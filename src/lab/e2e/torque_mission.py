#!/usr/bin/env python3
"""One mission-level bounded-torque execution: same risk scene, actuator torque_limited
tau=8 (mission expected to complete) and tau=0.5 (starved: honest slow/failed outcome)."""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
out = Path('/home/peakpeng/Desktop/URP/setup/2026-10-18/ground-risk-planning/torque-mission')
assert not out.exists()
out.mkdir(parents=True)
os.environ['URP_LAB_RUNTIME'] = str(out / 'runtime')
os.environ['URP_ROS_DOMAIN_ID'] = '145'
from fastapi.testclient import TestClient
from urp_lab.scenarios.validate import validate_instance
from urp_lab.gateway import Config, create_app
INSTANCE = validate_instance('fleet_routing', {
    'boundary': [[0,0],[34,0],[34,26],[0,26]], 'depot': [3,3], 'robot_radius': 0.5,
    'tasks': [{'id': 1, 'xy': [30, 22], 'demand': 1, 'service_s': 1.0},
              {'id': 2, 'xy': [28, 24], 'demand': 1, 'service_s': 1.0}],
    'vehicles': {'count': 1, 'capacity': 2, 'travel': 'free', 'speed_mps': 1.0},
    'objective': 'total_distance'})
app = create_app(Config(runtime=out/'runtime', port=4143, field_sim_port=4196,
                        background=False, archive_autostart=False, extra_hosts={'testserver'}))
def wait_for(read, pred, seconds):
    end = time.monotonic()+seconds; s=None
    while time.monotonic() < end:
        s = read()
        if pred(s): return s
        time.sleep(0.5)
    raise TimeoutError(str(s)[:800])
results = {}
with TestClient(app) as c:
    api = '/lab/api'
    sc = c.post(api+'/compose', json={'text':'34×26米田块，1台车，2个采样点，容量2','seed':72}).json()
    sub = c.post(api+'/solve', json={'scenario_id': sc['id'], 'instance': INSTANCE,
                 'algorithms':[{'id':'pyvrp.fleet','params':{'time_limit_s':2,'seed':42}}]})
    rid = wait_for(lambda: c.get(api+'/runs/'+sub.json()['runs'][0]).json(),
                   lambda r: r['state'] not in ('queued','running'), 30)
    assert rid['state']=='done' and rid['check']['valid']
    for case, tau in (('rich', 8.0), ('starved', 0.5)):
        started = c.post(api+'/fieldsim', json={'run_id': rid['run_id'], 'real_time_factor': 6,
                                                'web': False,
                                                'physics': {'actuator_mode':'torque_limited',
                                                            'wheel_torque_limit_nm': tau}})
        assert started.status_code == 202, started.text
        sid = started.json()['session_id']
        st = lambda: c.get(api+'/fieldsim').json()
        wait_for(st, lambda s: s['phase'] in ('finished','failed') or not s['running'], 900)
        c.post(api+'/fieldsim/stop', json={})
        wait_for(st, lambda s: not s['running'], 120)
        r = c.get(api+f'/fieldsim/results/{sid}').json()
        rep = json.loads((out/'runtime'/'fieldsim'/sid/'session-report.json').read_text())
        m = r['metrics']
        tt = r.get('torque_traces') or {}
        results[case] = {'session_id': sid, 'state': r['state'], 'tau': tau,
                         'tasks': f"{m['tasks_reached']}/{m['tasks_total']}",
                         'makespan_s': m['makespan_s'], 'distance_m': m['total_distance_m'],
                         'cross_track_max': m['cross_track_max_m'],
                         'cleanup': rep.get('cleanup_status'),
                         'trace_rows': {k: len(v) for k, v in tt.items()},
                         'check_valid': (r.get('check') or {}).get('valid')}
        (out/f'{case}-summary.json').write_text(json.dumps(results[case], ensure_ascii=False, indent=1))
        print(case, results[case], flush=True)
ok = (results['rich']['state']=='succeeded' and results['rich']['tasks']=='2/2'
      and results['starved']['state'] in ('succeeded','failed'))
summary = {'schema':'urp.torque-mission-check/1',
           'status': 'PASS' if ok else 'FAIL', 'cases': results,
           'predeclared': 'tau=8: mission completes with truth-verified tasks; tau=0.5: honest outcome either way (slow crawl or failure)',
           'scope': 'bounded-torque actuator, velocity-servo reference unchanged; saturation evidenced by probe brake response'}
(out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1))
print('SUMMARY', summary['status'])
sys.exit(0 if ok else 1)
