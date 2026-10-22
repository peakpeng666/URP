from warehouse_diagnostics import failure as describe_failure
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
from historical_fuel import download_archive as download_fuel_archive, materialize, verify_cache, canonicalize_assets, ALIAS_PROJECTION
from warehouse_lifecycle import drive, physical_evidence, OVERALL_WALL_S
from warehouse_public_summary import project, digest
from startup_observer import Observer, is_cancellation
from process_observer import ProcessObserver
import runtime_identity

FUEL_MODELS=('Warehouse','shelf_big','shelf','Chair','foldable_chair','MaleVisitorOnPhone','Table','Jersey Barrier','Casual female')


class IdentityCapture:
    """Optional evidence, with original errors authoritative and cleanup first."""
    def __init__(self):
        self.instance=None
        self.started=False
        self.finished=False
        self.cached=None
        self.pending=None
        self.containment_error=None
        self.original_error=None

    def defer_cancellation(self, error):
        if self.pending is None:
            self.pending=error

    def begin(self, private):
        if self.started or self.finished:return
        self.started=True
        try:
            self.instance=runtime_identity.RuntimeIdentity(private)
            self.instance.before_gateway()
        except BaseException as exc:
            if is_cancellation(exc):
                self.defer_cancellation(exc)
                raise
            if isinstance(exc,runtime_identity.QueryCleanupUncertain):
                self.containment_error=exc
                raise

    def finish(self):
        if self.finished:return self.cached
        self.finished=True
        self.cached=dict(runtime_identity.UNAVAILABLE)
        try:
            if self.instance is not None:
                try:self.instance.cleanup_query_child()
                except BaseException:
                    self.cached['query_cleanup_status']='uncertain'
                    raise
                self.instance.after_cleanup()
                self.cached=self.instance.result()
        except BaseException as exc:
            if isinstance(exc,runtime_identity.QueryCleanupUncertain):self.containment_error=exc
            if is_cancellation(exc):self.defer_cancellation(exc)
            self.remember_child_evidence()
        return self.cached

    def remember_child_evidence(self):
        # Own in-memory collector fields only, never process/environment reads.
        try:
            evidence=getattr(self.instance,'raw',None)
            if type(evidence) is dict:
                status=evidence.get('query_cleanup_status')
                if type(status) is str and status in ('not_started','not_observed','pending','reaped','uncertain'):
                    self.cached['query_cleanup_status']=status
                uncertain=evidence.get('query_cleanup_was_uncertain')
                if type(uncertain) is bool:self.cached['query_cleanup_was_uncertain']=uncertain
        except BaseException as exc:
            if is_cancellation(exc):self.defer_cancellation(exc)

    def apply_pending(self, result):
        if (self.pending is not None or self.containment_error is not None) and self.original_error is None:
            for key in ('state','warehouse_state'):
                if result.get(key)=='PASS':result[key]='ERROR'

    def raise_pending(self):
        error=self.pending if self.pending is not None else self.containment_error
        if error is not None and (self.original_error is None or self.original_error is error):
            raise error


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


def preload_fuel(source,private,env):
    # Separate historical cohort: never download current Fuel or overwrite a cache.
    cache=source/'setup/2026-10-15/cache/ignition-fuel'
    if cache.exists() or cache.is_symlink():raise ValueError('historical_cache_destination_exists')
    return materialize(download_fuel_archive(private),cache)


def execute(a):
    private=a.private_dir.resolve();private.mkdir(parents=True,exist_ok=False,mode=0o700)
    runtime=private/'runtime';runtime.mkdir(mode=0o700)
    frozen=a.frozen_harness.resolve()
    sys.path.insert(0,str(frozen))
    from acceptance import api, owned, signal_owned, verify_source, read
    from startup_diagnostics import collect
    from execution_diagnostics import collect as collect_execution
    source=a.source.resolve();token=secrets.token_hex(24);gateway=None;base=None;forced=False;sid=None;observer=None;process_observer=None
    identity_capture=IdentityCapture()
    raw={'state':'ERROR','source_sha':SOURCE,'harness_sha':a.harness_sha,'overall_wall_budget_s':OVERALL_WALL_S}
    diagnostic={'harness':{'phase':'preflight'},'session_report':'unavailable'}
    raw['warehouse_diagnostics']=diagnostic
    def mark(phase):diagnostic['harness']['phase']=phase
    def observed_session(value):
        nonlocal sid
        sid=value
        if observer is not None:observer.safe('bind',value)
        if process_observer is not None:process_observer.safe('bind',value)
    def save(name,obj):(private/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False))
    try:
        if a.stage!='warehouse' or not digest(a.harness_sha,40):raise ValueError('warehouse_arguments_invalid')
        mark('source_verification')
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
        mark('historical_inputs')
        inputs=from_archive(a.archive or download_archive(private))
        mark('fuel_restore')
        cache_receipt=preload_fuel(source,private,env)
        raw.update(cache_receipt)
        mark('resource_check')
        raw_assets=inspect_world('warehouse')
        raw_resources=compare(inputs['evidence/native-tb4-session/world-assets.json'],raw_assets)
        raw.update(raw_resource_manifest_sha256=raw_resources['current_resource_manifest_sha256'],
                   raw_resources_match_historical=raw_resources['resources_match_historical'],historical_alias_projection=ALIAS_PROJECTION)
        save('raw-world-assets.json',raw_assets)
        canonical_assets=canonicalize_assets(raw_assets,source/'setup/2026-10-15/cache/ignition-fuel')
        save('canonical-world-assets.json',canonical_assets)
        resources=compare(inputs['evidence/native-tb4-session/world-assets.json'],canonical_assets)
        raw.update(resources)
        if resources['resources_match_historical'] is not True:raise ValueError('historical_resources_mismatch')
        map_before=map_snapshot(maps);adapter_before=adapter_identity()
        mark('record_build')
        record,plan=build_record(inputs,check,map_check,to_sim_plan,execution_manifest,lambda:maps.fingerprint('warehouse'),adapter_before)
        raw.update(public_receipt(record));raw.update(resources);raw.update(source_sha=SOURCE,harness_sha=a.harness_sha,overall_wall_budget_s=OVERALL_WALL_S,state='ERROR',**map_before)
        save('new-record.json',record);save('current-plan.json',plan)
        mark('record_store')
        db=Store(runtime/'lab.sqlite3')
        try:
            if db.list_runs() or db.active_sim_runs():raise ValueError('runtime_not_empty')
            db.put_run(record)
            if db.get_run(record['run_id'])!=record:raise ValueError('import_readback_mismatch')
        finally:db.close()
        def guard():
            try:
                if verify_cache(source/'setup/2026-10-15/cache/ignition-fuel')!=cache_receipt:
                    raise ValueError('historical_cache_provenance_changed')
            except Exception:
                raw['historical_cache_verified']=False
                raise
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
                current_assets=inspect_world('warehouse')
                if compare(inputs['evidence/native-tb4-session/world-assets.json'],current_assets)!=raw_resources:
                    raise ValueError('raw_resource_identity_changed')
                checked=compare(inputs['evidence/native-tb4-session/world-assets.json'],canonicalize_assets(current_assets,source/'setup/2026-10-15/cache/ignition-fuel'))
                if checked!=resources:
                    raw.update(checked)
                    raise ValueError('current_resources_changed')
            except Exception:
                raw['resources_match_historical']=False
                raise
        mark('guard')
        guard()
        identity_capture.begin(private)
        mark('gateway_start')
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base=f'http://127.0.0.1:{port}'
        with (private/'gateway.log').open('w') as log:
            gateway=subprocess.Popen([str(source/'src/lab/.venv/bin/python'),'-m','urp_lab','serve','--host','127.0.0.1','--port',str(port),'--no-archive'],
                         cwd=source/'src/lab',env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        if env.get('URP_WAREHOUSE_STARTUP_OBSERVER')=='1' and env.get('URP_WAREHOUSE_STARTUP_OBSERVER_DELAY_S')=='30':
            try:process_observer=ProcessObserver(gateway)
            except BaseException as exc:
                if is_cancellation(exc):raise
                raw['warehouse_process_observation']={'status':'unavailable','end_reason':'read_error'}
        mark('gateway_health')
        end=time.monotonic()+120
        while True:
            if gateway.poll() is not None or time.monotonic()>end:raise ValueError('gateway_failed')
            try:
                if api(base,'GET','/health').get('status')=='ok':break
            except (OSError,ValueError):pass
            time.sleep(.5)
        diagnostic['harness']['gateway_health_verified']=True
        mark('gateway_readback')
        persisted=api(base,'GET','/runs/'+record['run_id'])
        if persisted!=record:raise ValueError('gateway_import_readback_mismatch')
        diagnostic['harness']['gateway_record_verified']=True
        mark('lifecycle')
        api_call=lambda method,path,data=None,timeout=5:api(base,method,path,data,timeout)
        if env.get('URP_WAREHOUSE_STARTUP_OBSERVER')=='1':
            try:
                observer=Observer(env,private,source)
                api_call=observer.wrap(api_call)
            except BaseException as exc:
                if is_cancellation(exc):raise
                observer=None;raw['warehouse_startup_observation']={'status':'unavailable'}
        if process_observer is not None:api_call=process_observer.wrap(api_call)
        lifecycle=drive(api_call,record['run_id'],plan,guard,save,on_session=observed_session)
        diagnostic['lifecycle']=lifecycle['diagnostics']
        raw['execution_protocol']=lifecycle['execution_protocol']
        raw['execution_diagnostics']=collect_execution(lifecycle['result'],[record],source)
        sid=lifecycle['session_id']
        import re
        if not isinstance(sid,str) or not re.fullmatch(r'sim_[A-Za-z0-9_]+',sid):raise ValueError('session_identity_missing')
        mark('session_report')
        report_path=runtime/'sim'/sid/'session-report.json'
        diagnostic['session_report']='missing' if not report_path.is_file() else 'invalid'
        session=read(report_path,{})
        if not isinstance(session,dict):raise ValueError('session_report_identity_mismatch')
        if session.get('session_id')!=sid:
            if report_path.is_file():diagnostic['session_report']='identity_mismatch'
            raise ValueError('session_report_identity_mismatch')
        diagnostic['session_report']='available'
        mark('physical_check')
        raw.update(physical_evidence(lifecycle['result'],session,lifecycle,plan))
        guard();raw.update(source_identity_verified=True,map_identity_verified=True)
        # Assert real session settings, not just requested API settings.
        if (session.get('spawn')!=record['replay']['expected_session_spawn'] or
                (session.get('navigation_profile') or {}).get('localization')!='ground_truth'):
            raw['state']='FAIL'
        mark('overlay_identity')
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
        identity_capture.original_error=exc
        diagnostic['harness'].update(failure_phase=diagnostic['harness']['phase'],**describe_failure(exc))
        raw['state']='ERROR';(private/'harness-error.txt').write_text(type(exc).__name__+': '+str(exc))
    finally:
        observer_cancellation=None
        if process_observer is not None:
            try:
                process_observer.stop('cleanup_started')
                raw['warehouse_process_observation']=process_observer.result()
            except BaseException as exc:
                raw['warehouse_process_observation']={'status':'unavailable','end_reason':'read_error'}
                if is_cancellation(exc):
                    observer_cancellation=exc
                    if raw.get('state')=='PASS':raw['state']='ERROR'
        if observer is not None:
            try:observer.safe('close')
            except BaseException as exc:
                observer_cancellation=exc
                if raw.get('state')=='PASS':raw['state']='ERROR'
            raw['warehouse_startup_observation']=observer.raw
        if base and gateway and gateway.poll() is None:
            try:api(base,'POST','/shutdown',{},timeout=10)
            except Exception as exc:diagnostic['harness']['gateway_shutdown_exception_kind']=describe_failure(exc)['exception_kind']
            diagnostic['harness']['gateway_wait_timed_out']=False
            try:gateway.wait(timeout=240)
            except subprocess.TimeoutExpired:
                forced=True;diagnostic['harness']['gateway_wait_timed_out']=True
        if owned(token):
            forced=True;signal_owned(token,signal.SIGTERM);end=time.monotonic()+15
            while owned(token) and time.monotonic()<end:time.sleep(.5)
        if owned(token):signal_owned(token,signal.SIGKILL);time.sleep(1)
        if gateway:
            try:gateway.wait(timeout=5)
            except subprocess.TimeoutExpired:pass
        diagnostic['harness']['forced_cleanup']=forced
        raw['gateway_exit_code']=gateway.returncode if gateway else None
        raw['remaining_owned_process_count']=len(owned(token))
        raw['cleanup_pass']=bool(raw.get('cleanup_pass') and not forced and raw['remaining_owned_process_count']==0)
        diagnostic['harness']['startup_collection_failed']=False
        try:raw['startup_diagnostics']=collect(runtime,sid)
        except Exception:diagnostic['harness']['startup_collection_failed']=True
        raw['warehouse_runtime_identity']=identity_capture.finish()
        identity_capture.apply_pending(raw)
        summary=project(raw,require_runner=False,runtime_identity_cancellation=identity_capture.defer_cancellation)
        identity_capture.apply_pending(summary)
        a.summary.parent.mkdir(parents=True,exist_ok=True);a.summary.write_text(json.dumps(summary,indent=2,allow_nan=False))
        if observer_cancellation is not None:raise observer_cancellation
        identity_capture.raise_pending()
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
