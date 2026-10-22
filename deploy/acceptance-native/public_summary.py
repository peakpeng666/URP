"""Fail-closed public projection. Never copy arbitrary input keys or strings."""
import argparse
import json
import math
import re
from pathlib import Path

SOURCE = '94420cf3b703c564134048e1b074406df901bba3'
STATES = {'PASS', 'FAIL', 'ERROR', 'NOT_RUN'}
HASHES = ('scenario_sha256', 'solution_sha256', 'resource_manifest_sha256',
          'runtime_fingerprint_sha256', 'overlay_source_sha256', 'overlay_binary_sha256')
NUMBERS = ('duration_sim_s', 'duration_wall_s', 'real_time_factor', 'clock_gap_max_s',
           'odom_age_max_s', 'truth_age_max_s', 'map_odom_stamp_lag_max_s',
           'odom_base_stamp_lag_max_s', 'future_tf_gap_max_s', 'actual_length_m',
           'final_error_m', 'cross_track_max_m')
COUNTS = ('tasks_total', 'tasks_reached', 'trajectory_samples', 'clock_backwards_count',
          'future_tf_error_count', 'remaining_owned_process_count')
BOOLS = ('cleanup_pass', 'map_collision_free', 'actual_map_collision_free',
         'source_identity_verified', 'assets_complete', 'trajectory_motion_verified', 'runtime_compatibility_verified')

def number(v, integer=False, low=0, high=1e9):
    if type(v) not in ((int,) if integer else (int, float)) or not math.isfinite(v) or not low <= v <= high:
        return None
    return v

def digest(v, length=64):
    return v if isinstance(v, str) and re.fullmatch('[0-9a-f]{%d}' % length, v) else None

def apt_projection(value):
    states={'not_run','verified','no_verified_edges','metadata_unavailable','tree_limit','invalid_projection','membership_only'}
    invalid=('invalid_projection',[])
    if not isinstance(value,dict) or set(value) not in ({'status','dependencies'},{'status','dependencies','metadata_phase','metadata_error'},{'status','dependencies','metadata_phase','metadata_error','evidence','fallback_error'}):return invalid
    state=value['status'];edges=value['dependencies']
    if not isinstance(state,str) or state not in states or not isinstance(edges,list) or len(edges)>20:return invalid
    if state=='membership_only':
        if value.get('evidence')!='apt_cache_membership' or value.get('fallback_error')!='none':return invalid
        clean=[]
        for e in edges:
            if not isinstance(e,dict) or set(e)!={'package','relation','dependency'} or not all(isinstance(x,str) for x in e.values()):return invalid
            if not all(re.fullmatch(r'[a-z0-9][a-z0-9+.-]{0,119}',e[k]) for k in ('package','dependency')) or e['relation'] not in ('depends','predepends','conflicts','breaks'):return invalid
            clean.append({k:e[k] for k in ('package','relation','dependency')})
        return ('membership_only',clean) if clean else ('no_verified_edges',[])
    if state!='verified':return (state,[]) if not edges else invalid
    out=[]
    keys={'package','package_version','relation','dependency','version_relation','dependency_version'}
    for e in edges:
        if not isinstance(e,dict) or set(e)!=keys or not all(isinstance(v,str) for v in e.values()):return invalid
        if not all(re.fullmatch(r'[a-z0-9][a-z0-9+.-]{0,119}',e[k]) for k in ('package','dependency')):return invalid
        if not re.fullmatch(r'[A-Za-z0-9.+:~\-]{1,120}',e['package_version']):return invalid
        if e['dependency_version'] and not re.fullmatch(r'[A-Za-z0-9.+:~\-]{1,120}',e['dependency_version']):return invalid
        if e['relation'] not in ('depends','predepends','conflicts','breaks') or e['version_relation'] not in ('any','eq','ge','le','gt','lt'):return invalid
        if (e['version_relation']=='any') != (e['dependency_version']==''):return invalid
        out.append({k:e[k] for k in sorted(keys)})
    return ('verified',out) if out else ('no_verified_edges',[])


def registry_projection(raw):
    raw=raw if isinstance(raw,dict) else {}
    phases=('lock_parse','source_policy','metadata_fetch','integrity_check','complete')
    errors=('none','http','timeout','tls','network','metadata_invalid','integrity_mismatch','source_not_allowlisted','lock_invalid','unknown')
    return {'phase':raw.get('phase') if raw.get('phase') in phases else 'unknown',
            'status':raw.get('status') if raw.get('status') in ('passed','failed') else 'not_measured',
            'error':raw.get('error') if raw.get('error') in errors else 'unknown',
            'http_status':number(raw.get('http_status'),True,100,599),
            'mirror_index':number(raw.get('mirror_index'),True,1,100000),
            'attempts':number(raw.get('attempts'),True,0,3),
            'mirror_identities_verified':number(raw.get('mirror_identities_verified'),True,0,100000)}


def project(raw, runner=None):
    raw = raw if isinstance(raw, dict) else {}
    result = {'schema_version': 1, 'source_sha': digest(raw.get('source_sha'), 40),
              'harness_sha': digest(raw.get('harness_sha'), 40),
              'stage': raw.get('stage') if raw.get('stage') in ('maze', 'warehouse') else 'unknown',
              'state': raw.get('state') if isinstance(raw.get('state'), str) and raw.get('state') in STATES else 'ERROR',
              'warehouse_state': 'NOT_RUN', 'physical_budget_origin': 'new_run',
              'physical_budget_s': number(raw.get('physical_budget_s')),
              'overall_wall_budget_s': number(raw.get('overall_wall_budget_s'))}
    for k in HASHES: result[k] = digest(raw.get(k))
    for k in NUMBERS: result[k] = number(raw.get(k))
    for k in COUNTS: result[k] = number(raw.get(k), True)
    for k in BOOLS: result[k] = raw.get(k) if type(raw.get(k)) is bool else None
    codes = raw.get('process_exit_codes', {})
    result['process_exit_codes'] = {k: number(codes.get(k), True, -255, 255) if isinstance(codes, dict) else None
                                    for k in ('full_loop', 'gateway')}
    result['measurement_availability'] = {k: 'measured' if result[k] is not None else 'not_measured'
                                          for k in (*NUMBERS, *COUNTS)}
    result['installation_step'] = 'unknown'
    result['runner_failure_hint'] = 'unknown'
    result['runner_stage'] = 'unknown'
    result['runner_exit_code'] = None
    result['runner_cleanup_remaining'] = None
    result['forced_kill_count'] = None
    result['apt_metadata_status'] = 'not_run'
    result['apt_metadata_phase'] = 'not_run'
    result['apt_metadata_error'] = 'not_measured'
    result['apt_evidence'] = 'not_measured'
    result['apt_fallback_error'] = 'not_measured'
    result['apt_dependencies'] = []
    result['registry_diagnostic'] = registry_projection(None)
    if runner is not None:
        runner = runner if isinstance(runner, dict) else {}
        result['registry_diagnostic'] = registry_projection(runner.get('registry_diagnostic'))
        step = runner.get('installation_step')
        result['installation_step'] = step if step in ('unknown', 'apt_update', 'apt_install', 'other', 'not_applicable', 'registry_check') else 'unknown'
        hint = runner.get('failure_hint')
        result['runner_failure_hint'] = hint if hint in ('none', 'source_identity', 'package_install', 'dependency_fetch', 'network', 'disk_full', 'native_build', 'registry_identity', 'apt_signature', 'apt_source_conflict', 'apt_release', 'apt_hook', 'apt_lock', 'apt_package_missing', 'apt_dependency_conflict', 'apt_libunwind_conflict', 'unknown') else 'unknown'
        result['runner_stage'] = runner.get('stage') if runner.get('stage') in ('installation', 'simulation') else 'unknown'
        result['runner_exit_code'] = number(runner.get('exit_code'), True, -255, 255)
        result['runner_cleanup_remaining'] = number(runner.get('cleanup_remaining'), True)
        result['forced_kill_count'] = number(runner.get('forced_kill_count'), True)
        result['apt_metadata_status'], result['apt_dependencies'] = apt_projection(runner.get('apt_projection', {'status':'not_run','dependencies':[]}))
        diagnostic=runner.get('apt_projection')
        if isinstance(diagnostic,dict):
            result['apt_evidence']='apt_cache_membership' if diagnostic.get('evidence')=='apt_cache_membership' else 'official_metadata' if diagnostic.get('status')=='verified' else 'not_measured'
            fallback=diagnostic.get('fallback_error')
            result['apt_fallback_error']=fallback if fallback in ('none','timeout','exit','unavailable','output_invalid') else 'not_measured'

            phase=diagnostic.get('metadata_phase');error=diagnostic.get('metadata_error')
            result['apt_metadata_phase']=phase if phase in ('module_import','source_identity','log_read','cache_open','metadata_project','complete','dependency_install','subprocess') else 'not_run'
            result['apt_metadata_error']=error if error in ('none','import_missing','import_error','api_attribute','api_type','api_key','command_failed','validation','filesystem','apt_system','apt_runtime','unknown','subprocess_exit','subprocess_timeout','subprocess_os','invalid_output','dependency_install_failed','dependency_install_timeout') else 'not_measured'

        if result['runner_exit_code'] != 0 or result['runner_cleanup_remaining'] != 0 or result['forced_kill_count'] != 0:
            result['state'] = 'FAIL'
    # A public PASS cannot be forged by an incomplete/ready-only input.
    if result['state'] == 'PASS':
        if not (result['runner_exit_code'] == 0 and result['runner_cleanup_remaining'] == 0 and result['forced_kill_count'] == 0 and result['source_sha'] == SOURCE and result['harness_sha'] and
                all(result[k] is True for k in BOOLS) and all(result[k] is not None for k in HASHES) and
                (result['tasks_total'] or 0) > 0 and result['tasks_total'] == result['tasks_reached'] and
                (result['trajectory_samples'] or 0) >= 2 and
                (result['actual_length_m'] or 0) > 0 and
                result['remaining_owned_process_count'] == 0 and
                all(v == 0 for v in result['process_exit_codes'].values())):
            result['state'] = 'FAIL'
    return result

def main():
    p = argparse.ArgumentParser(); p.add_argument('--input', type=Path, required=True)
    p.add_argument('--runner-status', type=Path); a = p.parse_args()
    try:
        raw = json.loads(a.input.read_text())
    except Exception:
        raw = {}
    runner = None
    if a.runner_status:
        try:
            runner = json.loads(a.runner_status.read_text())
        except Exception:
            runner = {}
    try:
        result = project(raw, runner)
    except Exception:
        # Keep independently valid supervisor diagnostics even if raw is malformed.
        try:
            result = project({}, runner)
        except Exception:
            result = project({}, {})
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0 if result['state'] == 'PASS' else 1

if __name__ == '__main__': raise SystemExit(main())
