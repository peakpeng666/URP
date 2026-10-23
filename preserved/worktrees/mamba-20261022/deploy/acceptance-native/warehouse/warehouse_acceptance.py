#!/usr/bin/env python3
"""Isolated warehouse replay over original APIs. No ROS starts in local tests."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from urllib.parse import urlsplit

from historical_input import SOURCE, ARCHIVE_SIZE, from_archive, from_directory, canonical_sha
from recheck import build_record, public_receipt
from resource_identity import compare
from warehouse_lifecycle import drive, physical_evidence
from warehouse_public_summary import project, digest

FUEL_MODELS=('Warehouse','shelf_big','shelf','Chair','foldable_chair','MaleVisitorOnPhone','Table','Jersey Barrier','Casual female')


def adapter_identity():
    return canonical_sha({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob('*.py'))})


def download_archive(private):
    # Existing verified public Release asset, not a newly guessed release/tag.
    req=urllib.request.Request('https://api.github.com/repos/peakpeng666/URP/releases/assets/653624946',
                               headers={'Accept':'application/vnd.github+json','User-Agent':'URP-isolated-acceptance'})
    with urllib.request.urlopen(req,timeout=60) as f:meta=json.load(f)
    if meta.get('id')!=653624946 or meta.get('name')!='deployment-acceptance.tar.zst' or meta.get('size')!=ARCHIVE_SIZE:raise ValueError('historical_asset_metadata_mismatch')
    url=meta.get('browser_download_url');parsed=urlsplit(url or '')
    if parsed.scheme!='https' or parsed.hostname!='github.com' or not parsed.path.startswith('/peakpeng666/URP/releases/download/'):raise ValueError('historical_asset_url_rejected')
    target=private/'historical.tar.zst';count=0
    with urllib.request.urlopen(url,timeout=120) as response,target.open('xb') as stream:
        while True:
            data=response.read(1024*1024)
            if not data:break
            count+=len(data)
            if count>ARCHIVE_SIZE:raise ValueError('historical_asset_too_large')
            stream.write(data)
    # from_archive subsequently verifies the full fixed SHA and exact size.
    return target


def map_snapshot(maps):
    # Clear both caches: execution_manifest excludes external map bytes.
    maps.load.cache_clear();maps._SIGNATURES.clear()
    grid=maps.load('warehouse')
    value={'yaml_sha256':hashlib.sha256(grid.yaml.read_bytes()).hexdigest(),
           'image_sha256':hashlib.sha256(grid.image_path.read_bytes()).hexdigest()}
    return {'current_map_bytes_sha256':canonical_sha(value),'current_map_fingerprint_sha256':maps.fingerprint('warehouse')}


def preload_fuel(source, private, env):
    # Uses only the fixed source's existing official version-pinned asset mechanism.
    # Its logs and downloaded models never leave the ephemeral runner checkout.
    script=source/'deploy/fetch-fuel.sh';cache=source/'setup/2026-10-15/cache/ignition-fuel'
    deadline=time.monotonic()+900
    for model in FUEL_MODELS:
        with (private/'fuel-fetch.log').open('ab') as stream:
            p=subprocess.Popen(['bash',str(script),str(cache)],cwd=source,env=dict(env,URP_FUEL_ONLY=model),
                               stdin=subprocess.DEVNULL,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            if p.wait(timeout=max(1,min(300,deadline-time.monotonic())))!=0:raise ValueError('fuel_fetch_failed')
            if time.monotonic()>=deadline:raise ValueError('fuel_prefetch_deadline')


def execute(a):
    private=a.private_dir.resolve();private.mkdir(parents=True,exist_ok=False,mode=0o700)
    runtime=private/'runtime';runtime.mkdir(mode=0o700)
    frozen=a.frozen_harness.resolve()
    sys.path.insert(0,str(frozen))
    from acceptance import api, owned, signal_owned, verify_source, read
    from startup_diagnostics import collect
    source=a.source.resolve();token=secrets.token_hex(24);gateway=None;base=None;forced=False;sid=None
    raw={'state':'ERROR','source_sha':SOURCE,'harness_sha':a.harness_sha,'overall_wall_budget_s':1800}
    def save(name,obj):(private/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False))
    try:
        if a.stage!='warehouse' or not digest(a.harness_sha,40):raise ValueError('warehouse_arguments_invalid')
        verify_source(source)
        if Path(sys.prefix).resolve()!=(source/'src/lab/.venv').resolve():raise ValueError('wrong_checker_interpreter')
        env=dict(os.environ,URP_LAB_RUNTIME=str(runtime),URP_ACCEPTANCE_OWNER=token,ROS_LOCALHOST_ONLY='1',
                 URP_ROS_DOMAIN_ID='147',ROS_DOMAIN_ID='147',URP_BIND_HOST='127.0.0.1',PYTHONPATH=str(source/'src/lab'))
        if any(key in env for key in ('URP_TF_FIX','URP_GUI_FIX','URP_BRIDGE_FIX','URP_ROS_MAPS')):raise ValueError('runtime_override_forbidden')
        os.environ['URP_LAB_RUNTIME']=str(runtime)
        sys.path.insert(0,str(source/'src/lab'));sys.path.insert(0,str(source/'src/research/src'))
        from urp_lab.jobs import execution_manifest
        from urp_lab.solvers import map_check
        from urp_lab.simplan import to_sim_plan
        from urp_lab.scenarios import maps
        from urp_lab.worlds import inspect_world
        from urp_lab.store import Store
        from urp_research.turn_modes.checker import check
        # No directory override in production CLI. Local JSON fixtures are test-only.
        inputs=from_archive(a.archive or download_archive(private))
        preload_fuel(source,private,env)
        resources=compare(inputs['evidence/native-tb4-session/world-assets.json'],inspect_world('warehouse'))
        raw.update(resources)
        if resources['resources_match_historical'] is not True:raise ValueError('historical_resources_mismatch')
        map_before=map_snapshot(maps);adapter_before=adapter_identity()
        record,plan=build_record(inputs,check,map_check,to_sim_plan,execution_manifest,lambda:maps.fingerprint('warehouse'),adapter_before)
        raw.update(public_receipt(record));raw.update(resources);raw.update(source_sha=SOURCE,harness_sha=a.harness_sha,overall_wall_budget_s=1800,state='ERROR',**map_before)
        save('new-record.json',record);save('current-plan.json',plan)
        db=Store(runtime/'lab.sqlite3')
        try:
            if db.list_runs() or db.active_sim_runs():raise ValueError('runtime_not_empty')
            db.put_run(record)
            if db.get_run(record['run_id'])!=record:raise ValueError('import_readback_mismatch')
        finally:db.close()
        def guard():
            try:
                verify_source(source)
                if adapter_identity()!=adapter_before or execution_manifest()['sha256']!=record['reproducibility']['execution_sha256']:raise ValueError('current_execution_identity_changed')
            except Exception:
                raw['source_identity_verified']=False
                raise
            if map_snapshot(maps)!=map_before:
                raw['map_identity_verified']=False
                raise ValueError('current_map_identity_changed')
            try:
                checked=compare(inputs['evidence/native-tb4-session/world-assets.json'],inspect_world('warehouse'))
                if checked!=resources:
                    raw.update(checked)
                    raise ValueError('current_resources_changed')
            except Exception:
                raw['resources_match_historical']=False
                raise
        guard()
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        with (private/'gateway.log').open('w') as log:
            gateway=subprocess.Popen([str(source/'src/lab/.venv/bin/python'),'-m','urp_lab','serve','--host','127.0.0.1','--port',str(port),'--no-archive'],
                         cwd=source/'src/lab',env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        end=time.monotonic()+120
        while True:
            if gateway.poll() is not None or time.monotonic()>end:raise ValueError('gateway_failed')
            try:
                if api(base,'GET','/health').get('status')=='ok':break
            except (OSError,ValueError):pass
            time.sleep(.5)
        persisted=api(base,'GET','/runs/'+record['run_id'])
        if persisted!=record:raise ValueError('gateway_import_readback_mismatch')
        lifecycle=drive(lambda method,path,data=None,timeout=5:api(base,method,path,data,timeout),record['run_id'],plan,guard,save)
        sid=lifecycle['session_id']
        import re
        if not isinstance(sid,str) or not re.fullmatch(r'sim_[A-Za-z0-9_]+',sid):raise ValueError('session_identity_missing')
        session=read(runtime/'sim'/sid/'session-report.json',{})
        if session.get('session_id')!=sid:raise ValueError('session_report_identity_mismatch')
        raw.update(physical_evidence(lifecycle['result'],session,lifecycle,plan))
        guard();raw.update(source_identity_verified=True,map_identity_verified=True)
        # Assert real session settings, not just requested API settings.
        if (session.get('spawn')!=record['replay']['expected_session_spawn'] or
                (session.get('navigation_profile') or {}).get('localization')!='ground_truth'):
            raw['state']='FAIL'
        compat=session.get('compatibility') or {}
        binary={k:hashlib.sha256(Path(compat[k]).read_bytes()).hexdigest() for k in ('tf','gui') if compat.get(k)}
        bridge_hash=(session.get('bridge_runtime') or {}).get('sha256')
        if len(binary)==2 and digest(bridge_hash):binary['bridge']=bridge_hash;raw['overlay_binary_sha256']=canonical_sha(binary)
        native=source/'src/lab/ros/native'
        sources={str(p.relative_to(native)):hashlib.sha256(p.read_bytes()).hexdigest() for p in native.rglob('*')
                 if p.is_file() and (p.suffix in ('.cpp','.cc','.h','.hh','.patch','.json','.sh') or p.name=='CMakeLists.txt')}
        deployment=source/'setup/2026-10-15/deployment'
        for rel in ('tf-repro/buffer_candidate.cpp','gui-plugin-lifetime.cpp','tf2-overlay-manifest.json','gui-overlay-manifest.json'):
            sources['deployment/'+rel]=hashlib.sha256((deployment/rel).read_bytes()).hexdigest()
        raw['overlay_source_sha256']=canonical_sha(sources)
    except BaseException as exc:
        raw['state']='ERROR';(private/'harness-error.txt').write_text(type(exc).__name__+': '+str(exc))
    finally:
        if base and gateway and gateway.poll() is None:
            try:api(base,'POST','/shutdown',{},timeout=10)
            except Exception:pass
            try:gateway.wait(timeout=240)
            except subprocess.TimeoutExpired:forced=True
        if owned(token):
            forced=True;signal_owned(token,signal.SIGTERM);end=time.monotonic()+15
            while owned(token) and time.monotonic()<end:time.sleep(.5)
        if owned(token):signal_owned(token,signal.SIGKILL);time.sleep(1)
        if gateway:
            try:gateway.wait(timeout=5)
            except subprocess.TimeoutExpired:pass
        raw['gateway_exit_code']=gateway.returncode if gateway else None
        raw['remaining_owned_process_count']=len(owned(token))
        raw['cleanup_pass']=bool(raw.get('cleanup_pass') and not forced and raw['remaining_owned_process_count']==0)
        try:raw['startup_diagnostics']=collect(runtime,sid)
        except Exception:pass
        summary=project(raw,require_runner=False);a.summary.parent.mkdir(parents=True,exist_ok=True);a.summary.write_text(json.dumps(summary,indent=2,allow_nan=False))
    return 0 if summary['state']=='PASS' else 1


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--private-dir',type=Path,required=True)
    p.add_argument('--summary',type=Path,required=True);p.add_argument('--harness-sha',required=True)
    p.add_argument('--stage',choices=['warehouse'],default='warehouse');p.add_argument('--archive',type=Path)
    p.add_argument('--frozen-harness',type=Path,default=Path(__file__).resolve().parent.parent)
    a=p.parse_args()
    def stop(signum,frame):raise RuntimeError('interrupted')
    signal.signal(signal.SIGTERM,stop)
    try:return execute(a)
    except BaseException:return 1

if __name__=='__main__':raise SystemExit(main())
