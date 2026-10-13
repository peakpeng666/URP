"""Trusted continuous Euclidean replay; no solver or archive Python execution."""
from collections import Counter
from math import isclose, sqrt
from .store import StoreError


def replay(instance, routes):
    nodes = {n['id']: n for n in instance['nodes']}
    expected = set(nodes) - {0}
    seen = [n for route in routes for n in route]
    counts = Counter(seen)
    duplicates = sorted(n for n,c in counts.items() if c > 1)
    unknown = sorted(set(seen) - expected)
    missing = sorted(expected - set(seen))
    violations = []
    if len(routes) != instance['vehicles']: violations.append('vehicle_count')
    if duplicates: violations.append('duplicate')
    if unknown: violations.append('unknown')
    schedules = []
    total = total_late = 0.0
    late_count = overload_count = depot_late_count = 0
    for vehicle, route in enumerate(routes):
        load = sum(nodes[n]['demand'] for n in route if n in expected)
        overload = max(0, load-instance['capacity'])
        if overload: overload_count += 1; violations.append('overload')
        time, previous, distance, stops = instance['depart_time'], 0, 0.0, []
        for n in route:
            if n not in expected: continue
            node, prev = nodes[n], nodes[previous]
            leg = sqrt((node['x']-prev['x'])**2 + (node['y']-prev['y'])**2)
            arrival = time+leg
            start = max(arrival,node['window'][0])
            late = max(0.0,start-node['window'][1])
            if late > 1e-9:
                late_count += 1; total_late += late; violations.append('late_start')
            stops.append(dict(node=n,arrival=arrival,wait=start-arrival,start=start,
                depart=start+node['service'],window_open=node['window'][0],window_close=node['window'][1],
                lateness=late,demand=node['demand'],leg_distance=leg))
            previous, time, distance = n, start+node['service'], distance+leg
        last, depot = nodes[previous], nodes[0]
        return_leg = sqrt((last['x']-depot['x'])**2 + (last['y']-depot['y'])**2)
        distance += return_leg
        return_time = time+return_leg
        depot_lateness = max(0.0,return_time-instance['return_deadline'])
        if depot_lateness > 1e-9: depot_late_count += 1; violations.append('depot_late')
        schedules.append(dict(vehicle=vehicle,route=route,load=load,overload=overload,distance=distance,
            stops=stops,return_leg_distance=return_leg,return_time=return_time,depot_lateness=depot_lateness))
        total += distance
    return dict(route_feasible=not violations, full_service_feasible=not violations and not missing,
        served_unique=len(set(seen)&expected),missing=missing,duplicates=duplicates,unknown=unknown,
        violations=violations,late_starts=late_count,total_lateness=total_late,overloaded_vehicles=overload_count,
        late_depot_returns=depot_late_count,total_distance=total,schedules=schedules)


def verify_recorded(actual, recorded, path='audit'):
    """Compare the complete replay result, keeping numeric tolerance explicit."""
    if isinstance(actual,dict):
        if not isinstance(recorded,dict) or set(actual)!=set(recorded):
            raise StoreError('replay_mismatch',f'独立回放字段不同：{path}')
        for key,value in actual.items(): verify_recorded(value,recorded[key],path+'.'+key)
    elif isinstance(actual,list):
        if not isinstance(recorded,list) or len(actual)!=len(recorded):
            raise StoreError('replay_mismatch',f'独立回放数组不同：{path}')
        for i,(value,saved) in enumerate(zip(actual,recorded)): verify_recorded(value,saved,f'{path}[{i}]')
    elif isinstance(actual,bool):
        if type(recorded) is not bool or actual!=recorded:raise StoreError('replay_mismatch',f'独立回放状态不同：{path}')
    elif isinstance(actual,(int,float)):
        if isinstance(recorded,bool) or not isinstance(recorded,(int,float)) or not isclose(actual,recorded,rel_tol=1e-12,abs_tol=1e-9):
            raise StoreError('replay_mismatch',f'独立回放数值不同：{path}')
    elif actual!=recorded:raise StoreError('replay_mismatch',f'独立回放值不同：{path}')


def vehicles_from_audit(instance, audit):
    if audit is None:return []
    nodes = {n['id']:n for n in instance['nodes']}
    vehicles = []
    for schedule in audit['schedules']:
        load, stops = 0, []
        for sequence,stop in enumerate(schedule['stops'],1):
            before = load;load += stop['demand']
            stops.append({**stop,'sequence':sequence,'service_start':stop['start'],
                          'load_before':before,'load_after':load,'onboard_load':None})
        path = [0,*schedule['route'],0]
        vehicles.append({**schedule,'vehicle_id':schedule['vehicle'],'stops':stops,
            'path_node_ids':path,'path_coordinates':[[nodes[n]['x'],nodes[n]['y']] for n in path],
            'path_semantics':'straight Euclidean segments including depot return; not road geometry',
            'load_semantics':'cumulative_served_demand; physical onboard load is unknown'})
    return vehicles
