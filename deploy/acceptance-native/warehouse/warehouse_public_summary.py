"""Separate fixed projection for rechecked historical replay, not a solver run."""
import argparse
import json
import math
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from public_summary import project as runner_projection
from historical_input import SOURCE, HISTORICAL_SOURCE

HASHES = ('historical_routes_sha256', 'historical_planned_sha256', 'current_plan_sha256',
          'adapter_sha256', 'current_execution_sha256', 'current_map_fingerprint_sha256',
          'current_map_bytes_sha256', 'historical_resource_manifest_sha256',
          'current_resource_manifest_sha256', 'overlay_source_sha256', 'overlay_binary_sha256')
BOOLS = ('tasks_all_reached', 'execution_mode_verified', 'route_check_valid', 'map_collision_free', 'actual_map_collision_free',
         'trajectory_motion_verified', 'source_identity_verified', 'map_identity_verified',
         'runtime_compatibility_verified', 'assets_complete', 'resources_match_historical', 'cleanup_pass')
COUNTS = ('tasks_total','tasks_reached','trajectory_samples','remaining_owned_process_count',
          'historical_resource_count','current_resource_count','missing_resource_count',
          'additional_resource_count','changed_resource_count')
METRICS = ('duration_sim_s','duration_wall_s','real_time_factor','actual_length_m','final_error_m','cross_track_max_m')

def number(value, integer=False, low=0, high=1e9):
    if type(value) not in ((int,) if integer else (int,float)): return None
    if not low <= value <= high: return None
    return value if math.isfinite(value) else None

def digest(value, length=64):
    return value if isinstance(value,str) and re.fullmatch('[0-9a-f]{%d}'%length,value) else None

def project(raw, runner=None, *, require_runner=True):
    raw=raw if isinstance(raw,dict) else {}
    state=raw.get('state');state=state if state in ('PASS','FAIL','ERROR','NOT_RUN') else 'ERROR'
    result={'schema_version':1,'stage':'warehouse','state':state,'warehouse_state':state,
            'source_sha':digest(raw.get('source_sha'),40),'harness_sha':digest(raw.get('harness_sha'),40),
            'historical_source_sha':HISTORICAL_SOURCE,'route_origin':'historical_fixed_witness',
            'solver_executed':False,'physical_budget_origin':'source_reconstructed_not_observed',
            'physical_budget_s':number(raw.get('physical_budget_s')),
            'overall_wall_budget_s':number(raw.get('overall_wall_budget_s')),
            'historical_map_bytes_identity':'not_recorded','historical_execution_identity_status':'not_recorded',
            'historical_counts_semantics':'tasks_reached_single_route_not_trials',
            'api_spawn_yaw':1.570796,'expected_session_spawn_yaw':1.5708,
            'runner_failure_hint':'unknown','runner_stage':'unknown','runner_exit_code':None,'runner_cleanup_remaining':None,'runner_forced_kill_count':None}
    for key in HASHES: result[key]=digest(raw.get(key))
    for key in BOOLS: result[key]=raw.get(key) if type(raw.get(key)) is bool else None
    for key in COUNTS: result[key]=number(raw.get(key),True)
    for key in METRICS: result[key]=number(raw.get(key))
    result['gateway_exit_code']=number(raw.get('gateway_exit_code'),True,-255,255)
    result['measurement_availability']={key:'measured' if result[key] is not None else 'not_measured' for key in (*COUNTS,*METRICS)}
    if runner is not None:
        runner=runner if isinstance(runner,dict) else {}
        diagnostic=runner_projection({},runner)
        for key in ('installation_step','registry_diagnostic','host_apt_repair','apt_metadata_status','apt_metadata_phase','apt_metadata_error','apt_evidence','apt_fallback_error','apt_dependencies'):
            result[key]=diagnostic[key]
        hint=runner.get('failure_hint')
        result['runner_failure_hint']=hint if hint in ('none','source_identity','package_install','dependency_fetch','network','disk_full','native_build','registry_identity','apt_signature','apt_source_conflict','apt_release','apt_hook','apt_lock','apt_package_missing','apt_dependency_conflict','apt_libunwind_conflict','unknown') else 'unknown'
        result['runner_stage']=runner.get('stage') if runner.get('stage') in ('installation','simulation') else 'unknown'
        result['runner_exit_code']=number(runner.get('exit_code'),True,-255,255)
        result['runner_cleanup_remaining']=number(runner.get('cleanup_remaining'),True)
        result['runner_forced_kill_count']=number(runner.get('forced_kill_count'),True)
        if result['runner_forced_kill_count'] != 0 or result['runner_exit_code'] != 0 or result['runner_cleanup_remaining'] != 0: result['state']='FAIL'
    if require_runner and runner is None and result['state']=='PASS': result['state']='FAIL'
    if result['state']=='PASS' and not (
        result['source_sha']==SOURCE and result['harness_sha'] and all(result[k] is not None for k in HASHES)
        and all(result[k] is True for k in BOOLS) and result['tasks_total']==result['tasks_reached']==5
        and (result['trajectory_samples'] or 0)>=2 and (result['actual_length_m'] or 0)>0
        and result['remaining_owned_process_count']==0 and result['gateway_exit_code']==0
        and result['historical_resource_count']==result['current_resource_count']==45
        and all(result[k]==0 for k in ('missing_resource_count','additional_resource_count','changed_resource_count'))
        and result['physical_budget_s'] is not None and abs(result['physical_budget_s']-649.6)<1e-7):
        result['state']='FAIL'
    result['warehouse_state']=result['state']
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--runner-status',type=Path)
    a=p.parse_args()
    def read(path):
        try:return json.loads(path.read_text())
        except Exception:return {}
    try:result=project(read(a.input),read(a.runner_status) if a.runner_status else None)
    except Exception:result=project({}, {})
    print(json.dumps(result,sort_keys=True,allow_nan=False))
    return 0 if result['state']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
