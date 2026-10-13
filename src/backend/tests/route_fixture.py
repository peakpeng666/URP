"""Tiny synthetic route contract fixture, never research evidence."""
import copy
import hashlib
import json
from pathlib import Path


def write_fixture(root):
    root = Path(root); root.mkdir(parents=True, exist_ok=True)
    instance = {'id': 'fixture_possible', 'geometry': 'fixture', 'stratum': 'TEST_ONLY',
        'level': 'test', 'vehicles': 1, 'capacity': 2, 'depart_time': 0, 'return_deadline': 120,
        'nodes': [{'id': 0, 'x': 0, 'y': 0, 'demand': 0, 'service': 0, 'window': [0,120]},
                  {'id': 1, 'x': 1, 'y': 0, 'demand': 1, 'service': 1, 'window': [0,2]},
                  {'id': 2, 'x': 2, 'y': 0, 'demand': 1, 'service': 1, 'window': [0,10]}]}
    impossible = copy.deepcopy(instance); impossible['id'] = 'fixture_impossible'
    impossible['nodes'][1]['window'] = [0,0]
    inputs = [instance, impossible]
    def row(method, route):
        seen, time, prev, distance, stops = [], 0, 0, 0, []
        for node in route:
            item = instance['nodes'][node]; leg = abs(node-prev); arrival = time+leg
            start = max(arrival,item['window'][0]); late = max(0,start-item['window'][1])
            stops.append(dict(node=node,arrival=arrival,wait=start-arrival,start=start,depart=start+1,
                window_open=item['window'][0],window_close=item['window'][1],lateness=late,demand=1,leg_distance=leg))
            seen.append(node); time=start+1; prev=node; distance+=leg
        missing = [n for n in [1,2] if n not in seen]; late_count = sum(s['lateness']>0 for s in stops)
        audit = dict(route_feasible=not late_count,full_service_feasible=not late_count and not missing,
            served_unique=len(seen),missing=missing,duplicates=[],unknown=[],violations=['late_start']*late_count,
            late_starts=late_count,total_lateness=sum(s['lateness'] for s in stops),overloaded_vehicles=0,
            late_depot_returns=0,total_distance=distance+prev,schedules=[dict(vehicle=0,route=route,load=len(seen),
            overload=0,distance=distance+prev,stops=stops,return_leg_distance=prev,return_time=time+prev,depot_lateness=0)])
        return dict(instance=instance['id'],geometry='fixture',stratum='TEST_ONLY',level='test',method=method,
            status='complete' if method!='capacity_only_diagnostic' else 'replayed_capacity_only_optimum',routes=[route],audit=audit,
            cpu_seconds=0,full_oracle_objective=4,full_gap_percent=0 if audit['full_service_feasible'] else None,
            same_served_mask_optimum=None,same_served_mask_gap_percent=None,coverage_shortfall=len(missing))
    rows = [row('distance_first',[1,2]),row('time_window_first',[1]),row('capacity_only_diagnostic',[2,1])]
    rows.append(dict(instance=impossible['id'],geometry='fixture',stratum='TEST_ONLY',level='test',method='oracle_full',
        status='proven_infeasible',routes=None,audit=None,cpu_seconds=0,full_oracle_objective=None,full_gap_percent=None,
        same_served_mask_optimum=None,same_served_mask_gap_percent=None,coverage_shortfall=None))
    objects = {'inputs.json':inputs,'protocol.json':{'study_id':'SYNTHETIC_CONTRACT_FIXTURE', 'input':{
        'distance':'Euclidean in arbitrary distance units; speed=1; no rounding during optimization',
        'time_window_semantics':'Inclusive bounds on START OF SERVICE; wait allowed; travel/service nonnegative; all routes return to depot'}},
        'map_backend.json':dict(schema_version=1,coordinate_system='synthetic Cartesian, not longitude/latitude; not road travel',
            time_window_semantics='inclusive service-start',units='arbitrary distance/time, speed1',
            objective='total Euclidean route distance, full service required',instances=inputs,solutions=rows),
        'verification.json':dict(passed=True,record_count=4,checks=['TEST FIXTURE ONLY']),
        'self_check.json':{'unit_tests':['TEST FIXTURE ONLY']}}
    for name,obj in objects.items(): (root/name).write_text(json.dumps(obj),encoding='utf-8')
    (root/'routes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
    (root/'checker.py').write_text('# INERT TEST ARTIFACT; never imported or executed.\n')
    (root/'freeze.json').write_text(json.dumps({'sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest()
        for name in ['inputs.json','protocol.json','checker.py']}}))
    return root
