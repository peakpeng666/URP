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
    result['runner_failure_hint'] = 'unknown'
    result['runner_stage'] = 'unknown'
    result['runner_exit_code'] = None
    result['runner_cleanup_remaining'] = None
    if runner is not None:
        runner = runner if isinstance(runner, dict) else {}
        hint = runner.get('failure_hint')
        result['runner_failure_hint'] = hint if hint in ('none', 'source_identity', 'package_install', 'dependency_fetch', 'network', 'disk_full', 'native_build', 'registry_identity', 'unknown') else 'unknown'
        result['runner_stage'] = runner.get('stage') if runner.get('stage') in ('installation', 'simulation') else 'unknown'
        result['runner_exit_code'] = number(runner.get('exit_code'), True, -255, 255)
        result['runner_cleanup_remaining'] = number(runner.get('cleanup_remaining'), True)
        if result['runner_exit_code'] != 0 or result['runner_cleanup_remaining'] != 0:
            result['state'] = 'FAIL'
    # A public PASS cannot be forged by an incomplete/ready-only input.
    if result['state'] == 'PASS':
        if not (result['source_sha'] == SOURCE and result['harness_sha'] and
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
