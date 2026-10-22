#!/usr/bin/env python3
"""Isolated runner lifecycle. All child output is private, never echoed on failure."""
import argparse, ctypes, json, os, pathlib, re, signal, subprocess, sys, time
HINTS = frozenset({'none','source_identity','package_install','dependency_fetch','network','disk_full','native_build','registry_identity','unknown','apt_signature','apt_source_conflict','apt_release','apt_hook','apt_lock','apt_package_missing','apt_dependency_conflict','apt_libunwind_conflict'})
LIMIT = 65536

def classify(path, exit_code):
    if exit_code == 0:
        return 'none'
    try:
        path = pathlib.Path(path)
        if path.is_symlink() or not path.is_file():
            return 'unknown'
        with path.open('rb') as stream:
            stream.seek(0,2)
            size=stream.tell()
            stream.seek(max(0,size-LIMIT))
            tail=stream.read(LIMIT).decode('utf-8',errors='replace').lower()
    except OSError:
        return 'unknown'
    # Require an explicit conflict edge, not mere mention of both packages.
    unwind=r'(?:libunwind-[0-9]{1,2}-dev[^\n]*conflicts(?::| on)[^\n]*libunwind-dev|libunwind-dev[^\n]*conflicts(?::| on)[^\n]*libunwind-[0-9]{1,2}-dev)'
    if re.search(unwind,tail):return 'apt_libunwind_conflict'
    markers = (
        ('disk_full', ('no space left on device','disk quota exceeded')),
        ('source_identity', ('source_revision_mismatch','index_revision_mismatch','tracked_blob_mismatch','tracked_file_missing','tracked_symlink_changed','unmerged_index','empty_source_checkout')),
        ('registry_identity', ('npm_mirror_identity_mismatch','non_allowlisted_npm_source')),
        ('apt_source_conflict', ('conflicting values set for option signed-by','conflicting values set for option trusted')),
        ('apt_signature', ('no_pubkey','expkeysig','badsig','the following signatures were invalid','the following signatures couldn','is not signed','at least one invalid signature was encountered')),
        ('apt_release', ('does not have a release file','no longer has a release file','release file is not valid yet','release file is expired')),
        ('apt_hook', ('problem executing scripts apt::update::post-invoke','problem executing scripts apt::update::pre-invoke','problem executing scripts dpkg::post-invoke','problem executing scripts dpkg::pre-invoke')),
        ('apt_lock', ('could not get lock','unable to acquire the dpkg frontend lock','unable to lock directory')),
        ('apt_package_missing', ('e: unable to locate package','has no installation candidate','unable to find a source package')),
        ('network', ('temporary failure in name resolution','could not resolve host','network is unreachable','connection timed out','connection reset by peer','certificate verify failed')),
        ('apt_dependency_conflict', ('following packages have unmet dependencies','unable to correct problems, you have held broken packages','e: unmet dependencies','pkgproblemresolver::resolve generated breaks')),
        ('package_install', ('e: unable to locate package','e: unmet dependencies','dpkg: error','sub-process /usr/bin/dpkg returned an error code')),
        ('dependency_fetch', ('failed to download','failed to fetch','no solution found when resolving dependencies','npm error code eintegrity','npm err! code eintegrity')),
        ('native_build', ('cmake error','ninja: build stopped','collect2: error: ld returned','fatal error:')),
    )
    for hint, needles in markers:
        if any(needle in tail for needle in needles):
            return hint
    return 'unknown'


def installation_step(path):
    try:
        with pathlib.Path(path).open('rb') as stream:
            stream.seek(0,2);stream.seek(max(0,stream.tell()-LIMIT))
            tail=stream.read(LIMIT).decode('utf-8',errors='replace')
    except OSError:return 'unknown'
    step='unknown'
    for line in tail.splitlines():
        if not re.match(r'^\++URP_SETUP ',line):continue
        if re.search(r'\bapt-get update(?:\s|$)',line):step='apt_update'
        elif re.search(r'\bapt-get install(?:\s|$)',line):step='apt_install'
        elif re.search(r'\b(?:uv|npm|cmake|g\+\+|python3|curl)\s',line):step='other'
    return step


def installation_progress(path):
    try:
        with pathlib.Path(path).open('rb') as f:
            f.seek(0,2);f.seek(max(0,f.tell()-LIMIT));tail=f.read(LIMIT).decode('utf-8',errors='replace')
    except OSError:return 'unknown'
    phase='unknown'
    for line in tail.splitlines():
        if not re.match(r'^\++URP_SETUP ',line):continue
        if re.search(r'\bapt-get\s',line):phase='apt'
        elif re.search(r'\buv\s|astral\.sh/uv/',line):phase='uv'
        elif re.search(r'\bnpm\s',line):phase='npm'
        elif 'src/lab/ros/native/install-ros-extras.sh' in line or 'deploy/build-cohort.sh' in line:phase='native'
    return phase


def snapshot():
    rows = {}
    for path in pathlib.Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            text = (path / 'stat').read_text()
            fields = text[text.rindex(')') + 2:].split()
            rows[int(path.name)] = (int(fields[1]), fields[19], fields[0])
        except (OSError, ValueError, IndexError):
            pass
    return rows

def descendants(rows, roots):
    result = set(roots)
    changed = True
    while changed:
        new = {pid for pid, row in rows.items() if row[0] in result}
        changed = not new.issubset(result)
        result |= new
    return result

def select_runtime_profile(root, env):
    # Match setup/ubuntu/run-lab.sh without changing runtime fingerprint checks.
    if (pathlib.Path(root)/'src/lab/runtime/native/bridge/profile.json').is_file():
        env['URP_SIM_PROFILE']='image'

def run(args):
    # Adopt only descendants that would otherwise be orphaned during shutdown.
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError('subreaper_failed')
    private = pathlib.Path(args.private_dir).resolve()
    private.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(private, 0o700)
    root = pathlib.Path(args.source).resolve()
    harness = pathlib.Path(args.harness).resolve()
    status = {'stage': 'installation', 'exit_code': 1, 'cleanup_remaining': 0, 'forced_kill_count': 0}
    owned = {}
    current = None
    env = os.environ.copy()
    # Do not pass action auth or service credentials to package hooks or simulations.
    for name in list(env):
        if any(token in name.upper() for token in ('TOKEN', 'SECRET', 'PASSWORD', 'CREDENTIAL')) or name.startswith('ACTIONS_'):
            env.pop(name, None)
    (private/'home/.local/bin').mkdir(parents=True)
    env.update(HOME=str(private/'home'), PYTHONDONTWRITEBYTECODE='1', LIBGL_ALWAYS_SOFTWARE='1',
               URP_BIND_HOST='127.0.0.1', URP_RMW='rmw_cyclonedds_cpp',
               UV_PYTHON_INSTALL_DIR=str(private/'python'),
               PATH=str(private/'home/.local/bin') + ':' + env.get('PATH', ''))
    # CLI opt-in is required even if the caller exports the environment variable.
    # Temporary child environment only; preserve the source lock and SRI checks.
    env['npm_config_registry']='https://registry.npmjs.org'
    env['npm_config_replace_registry_host']='registry.npmmirror.com'
    env.pop('URP_HOST_APT_REPAIR',None)
    if getattr(args,'allow_host_apt_repair',False):env['URP_HOST_APT_REPAIR']='1'
    stop = False
    def interrupted(signum, frame):
        nonlocal stop
        stop = True
        status['exit_code'] = 1
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    def track():
        rows = snapshot()
        roots = {os.getpid()} | {pid for pid, stamp in owned.items() if rows.get(pid, (None,None))[1] == stamp}
        for pid in descendants(rows, roots) - {os.getpid()}:
            if pid in rows:
                owned[pid] = rows[pid][1]
        return rows
    def child(command, filename, deadline):
        nonlocal current
        print(json.dumps({'stage':status['stage'],'state':'running'}),flush=True)
        next_progress=time.monotonic()+120
        last_install_phase='unknown'
        with (private / filename).open('wb') as stream:
            current = subprocess.Popen(command, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            while current.poll() is None:
                track()
                if time.monotonic() >= next_progress:
                    progress={'stage':status['stage'],'state':'running'}
                    if status['stage']=='installation':
                        found=installation_progress(private/filename)
                        if found!='unknown':last_install_phase=found
                        progress['installation_substage']=last_install_phase
                    print(json.dumps(progress),flush=True)
                    next_progress=time.monotonic()+120
                if stop or time.monotonic() > deadline:
                    raise TimeoutError('owned_stage_timeout')
                time.sleep(0.2)
            track()
            return current.returncode
    try:
        rc = child(['bash', str(pathlib.Path(__file__).with_name('install.sh')), str(root), str(private)], 'install.log', time.monotonic()+3600)
        if rc:
            status['exit_code'] = rc
            return status
        select_runtime_profile(root, env)
        status['stage'] = 'simulation'
        env['PATH'] = str(pathlib.Path(env['HOME'])/'.local/node-v24.22.0/bin') + ':' + env['PATH']
        # Xvfb is owned by this supervisor; Xvfb -displayfd avoids display collisions.
        display = private/'display'
        with display.open('wb') as fd, (private/'xvfb.log').open('wb') as log:
            xvfb = subprocess.Popen(['Xvfb','-displayfd',str(fd.fileno()),'-screen','0','1280x1024x24','-nolisten','tcp'],pass_fds=(fd.fileno(),),stdout=log,stderr=log,env=env,start_new_session=True)
        for _ in range(100):
            track()
            if display.read_text().strip(): break
            if xvfb.poll() is not None: raise RuntimeError('display_failed')
            time.sleep(.1)
        number = display.read_text().strip()
        if not number.isdigit(): raise RuntimeError('display_not_ready')
        env['DISPLAY'] = ':'+number
        entry = harness / ('warehouse/warehouse_acceptance.py' if args.stage == 'warehouse' else 'acceptance.py')
        rc = child([str(root/'src/lab/.venv/bin/python'), str(entry), '--source',str(root),'--private-dir',str(private/'harness-private'),'--harness-sha',args.harness_sha,'--summary',str(private/'summary.json'),'--stage',args.stage], 'acceptance.log', time.monotonic()+3600)
        status['exit_code'] = rc
    except Exception:
        status['exit_code'] = 1
    finally:
        forced_kills = set()
        for sig, seconds in ((signal.SIGTERM,20),(signal.SIGKILL,5)):
            end = time.monotonic()+seconds
            while True:
                rows = track()
                live = {pid for pid,stamp in owned.items() if rows.get(pid,(None,None))[1] == stamp}
                for pid in live:
                    # Zombies cannot receive a meaningful signal; reap them below.
                    if rows[pid][2] == 'Z': continue
                    try:
                        os.kill(pid,sig)
                        if sig == signal.SIGKILL:
                            forced_kills.add((pid,owned[pid]))
                    except (ProcessLookupError, PermissionError): pass
                if not live or time.monotonic() >= end: break
                # Reap direct children, preventing their zombies looking alive.
                try:
                    while os.waitpid(-1,os.WNOHANG)[0]: pass
                except ChildProcessError: pass
                time.sleep(.2)
        rows = snapshot()
        status['cleanup_remaining'] = sum(rows.get(pid,(None,None))[1] == stamp for pid,stamp in owned.items())
        status['forced_kill_count'] = len(forced_kills)
        if status['cleanup_remaining'] or status['forced_kill_count']: status['exit_code'] = 1
        if stop:
            status['exit_code'] = 1
        logfile = private / ('install.log' if status['stage'] == 'installation' else 'acceptance.log')
        status['failure_hint'] = classify(logfile, status['exit_code'])
        if status['stage']=='installation' and status['failure_hint'] in ('unknown','apt_dependency_conflict'):
            solver_hint=classify(private/'apt-solver.log',status['exit_code'])
            if solver_hint.startswith('apt_'):status['failure_hint']=solver_hint
        status['installation_step'] = installation_step(logfile) if status['stage']=='installation' else 'not_applicable'
        if stop:
            status['exit_code'] = 1
            status['failure_hint'] = 'unknown'
        status['registry_diagnostic'] = {}
        registry=private/'registry-identity.json'
        if registry.exists():
            try:
                if registry.is_symlink() or registry.stat().st_size>4096:raise ValueError('invalid_registry_diagnostic')
                status['registry_diagnostic']=json.loads(registry.read_text())
            except Exception:pass
        registry_status=status['registry_diagnostic']
        if not stop and isinstance(registry_status,dict) and registry_status.get('status')=='failed' and status['stage']=='installation':
            status['installation_step']='registry_check'
            category=registry_status.get('error')
            if category in ('integrity_mismatch','source_not_allowlisted','lock_invalid'):status['failure_hint']='registry_identity'
            elif category in ('http','timeout','tls','network'):status['failure_hint']='network'
        status['apt_projection'] = {'status':'not_run','dependencies':[]}
        projection=private/'apt-dependencies.json'
        if projection.exists():
            try:
                if projection.is_symlink() or projection.stat().st_size>32768:raise ValueError('invalid_projection')
                status['apt_projection']=json.loads(projection.read_text())
            except Exception:
                status['apt_projection']={'status':'invalid_projection','dependencies':[]}
        elif (private/'apt-solver.log').exists():
            status['apt_projection']={'status':'metadata_unavailable','dependencies':[]}
        repair_file=private/'host-apt-repair.json'
        status['host_apt_repair']={}
        if repair_file.exists():
            try:
                if repair_file.is_symlink() or repair_file.stat().st_size>4096:raise ValueError('invalid_repair_summary')
                status['host_apt_repair']=json.loads(repair_file.read_text())
            except Exception:pass
        (private/'runner-status.json').write_text(json.dumps(status))
    return status

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--harness',required=True);p.add_argument('--private-dir',required=True);p.add_argument('--stage',choices=['maze','warehouse'],default='maze');p.add_argument('--harness-sha',required=True)
    p.add_argument('--allow-host-apt-repair',action='store_true')
    try: result=run(p.parse_args());sys.exit(0 if result['exit_code']==0 else 1)
    except Exception: sys.exit(1)
