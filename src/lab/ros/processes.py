"""Owned ROS process groups: lifecycle, resource sampling and honest exit collection."""
import ctypes
from datetime import datetime, timezone
import os
from pathlib import Path
import signal
import subprocess
import time

from bridge_runtime import EXECUTABLE, SYSTEM_EXECUTABLE

BASE = Path(__file__).resolve().parents[1] / "runtime"

class OwnedProcesses:
    """One-shot Linux subreaper: signal/reap only child groups created here."""
    def __init__(self, env, label):
        if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0):
            raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')
        self.env, self.label, self.children = env, label, []
        self.peak_rss_kib = 0
        self.last_sample = 0
        self.resources = []

    def start(self, name, command, extra_env=None):
        log = BASE / 'logs' / f'{self.label}-{name}.log'
        with log.open('x') as stream:
            p = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                 env={**self.env, **(extra_env or {})}, start_new_session=True)
        self.children.append((name, p, log, command))
        return log

    def sample(self):
        ids = {p.pid for _, p, _, _ in self.children}
        rss, cpu_ticks, rows = 0, 0, []
        for path in Path('/proc').glob('[0-9]*/stat'):
            try:
                raw = path.read_text(); f = raw[raw.rfind(')') + 2:].split()
                if int(f[2]) in ids:
                    rows.append({'pid': int(path.parent.name), 'group': int(f[2]),
                                 'state': f[0], 'start_ticks': int(f[19])})
                    rss += int(f[21]) * os.sysconf('SC_PAGE_SIZE') // 1024
                    cpu_ticks += int(f[11])+int(f[12])
            except (OSError, ValueError):
                continue
        self.peak_rss_kib = max(self.peak_rss_kib, rss)
        self.resources.append({'utc':datetime.now(timezone.utc).isoformat(), 'rss_kib':rss,
                               'cpu_seconds_live_processes':cpu_ticks/os.sysconf('SC_CLK_TCK'),
                               'process_count':len(rows)})
        return rows

    def cleanup(self):
        results = []
        for name, p, log, command in reversed(self.children):
            start = time.monotonic(); records = []; signals = []
            complete = False
            for sig, grace in [(signal.SIGINT, 12), (signal.SIGTERM, 5), (signal.SIGKILL, 3)]:
                try:
                    # WNOWAIT keeps a child identity reserved until after signaling.
                    os.waitid(os.P_PGID, p.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                except ChildProcessError:
                    complete = True; break
                try:
                    # A ROS launch leader forwards SIGINT to its child. Sending
                    # the same first signal to both races RViz shutdown handlers.
                    if sig==signal.SIGINT and name in ('rviz','gui','nav','localization','sim'):
                        os.kill(p.pid,sig);signals.append(sig.name+'_LEADER')
                    else:
                        os.killpg(p.pid, sig); signals.append(sig.name)
                except ProcessLookupError:
                    pass
                deadline = time.monotonic() + grace
                while time.monotonic() < deadline:
                    try:
                        pid, status, usage = os.wait4(-p.pid, os.WNOHANG)
                    except ChildProcessError:
                        complete = True; break
                    if pid:
                        rc = os.waitstatus_to_exitcode(status)
                        if pid == p.pid: p.returncode = rc
                        records.append({'pid': pid, 'returncode': rc,
                                        'cpu_seconds': usage.ru_utime + usage.ru_stime,
                                        'peak_rss_kib': usage.ru_maxrss})
                    else:
                        time.sleep(.05)
                if complete: break
            results.append({'name': name, 'group': p.pid, 'command': command,
                            'signals': signals, 'reaped': records, 'complete': complete,
                            'seconds': time.monotonic() - start})
        return results

    def stop_bridges(self):
        """Stop owned bridge leaves once, before their launch leader forwards signals."""
        return self.stop_executables((EXECUTABLE, SYSTEM_EXECUTABLE), grace=4)

    def stop_executables(self, executables, grace=8):
        """Signal selected owned leaves while their dependencies are still alive.

        Their launch parent retains waitpid ownership and logs the actual status.
        """
        executables = {Path(p) for p in executables}
        sent=[]
        for row in self.sample():
            pid=row['pid']
            try:
                executable = os.readlink(f'/proc/{pid}/exe').removesuffix(' (deleted)')
                if Path(executable) not in executables or row['state']=='Z': continue
                fd=os.pidfd_open(pid)
                try:
                    if os.getpgid(pid)!=row['group']: continue
                    signal.pidfd_send_signal(fd,signal.SIGINT)
                    sent.append({'pid':pid,'group':row['group'],'start_ticks':row['start_ticks']})
                finally:os.close(fd)
            except (OSError,ProcessLookupError):pass
        live=set();end=time.monotonic()+grace
        while time.monotonic()<end:
            live={r['pid'] for r in self.sample() if r['state']!='Z'}
            if not any(r['pid'] in live for r in sent):break
            time.sleep(.1)
        return {'signaled':sent,'still_running':[r for r in sent if r['pid'] in live]}
