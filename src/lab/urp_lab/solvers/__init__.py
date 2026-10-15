"""Adapters around existing research code and installed solvers; witnesses checked independently."""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import math
import time
from collections import Counter

from .. import paths
from ..scenarios import maps
from . import f2c_coverage

paths.ensure_research_path()
from urp_research.turn_modes import solver, checker, oracle, evaluate_candidate

PARAMS = [{'name': 'time_limit_s', 'type': 'number', 'default': 3, 'min': 0.05, 'max': 120, 'label': '时间预算 (s)'},
          {'name': 'seed', 'type': 'integer', 'default': 42, 'min': 0, 'max': 2147483647, 'label': '随机种子'}]


def catalog():
    rows = [
        ('urp.turn_mode_dp', '转弯模式分层 DP', 'turn_routing', 'project', 'exact', 'optimal', 'solver.py', 12),
        ('urp.raw_oracle', '原图独立精确搜索', 'turn_routing', 'project', 'exact', 'optimal', 'oracle.py', 8),
        ('urp.reset_dp', '重置进入方向的松弛 DP', 'turn_routing', 'project', 'relaxation', 'optimal_for_relaxation', 'solver.py', 12),
        ('pyvrp.hgs+urp.layered', 'PyVRP ILS + 转弯分层实现', 'turn_routing', 'third_party', 'metaheuristic', 'none', 'pyvrp', None),
        ('ortools.gls+urp.layered', 'OR-Tools + 转弯分层实现', 'turn_routing', 'third_party', 'metaheuristic', 'none', 'ortools', None),
        ('pyvrp.hgs', 'PyVRP ILS', 'euclidean_cvrp', 'third_party', 'metaheuristic', 'none', 'pyvrp', None),
        ('ortools.gls', 'OR-Tools GLS', 'euclidean_cvrp', 'third_party', 'metaheuristic', 'none', 'ortools', None),
        ('panel.boustrophedon', '平行往复覆盖基线', 'coverage', 'panel_baseline', 'baseline', 'none', 'shapely', None),
    ]
    out = []
    for aid, name, pc, source, family, guarantee, origin, limit in rows:
        if source == 'project':
            origin = 'src/research/src/urp_research/turn_modes/' + origin
            version = hashlib.sha256((paths.REPO / origin).read_bytes()).hexdigest()
        else:
            version = md.version(origin)
            origin = f'{origin} {version}' + (' / IteratedLocalSearch' if aid.startswith('pyvrp.') else '') + (' + src/research/src/urp_research/turn_modes/evaluate_candidate.py' if pc == 'turn_routing' else '')
        out.append(dict(id=aid, name=name, problem_classes=[pc], family=family, source=source, origin=origin,
                        version=version, turn_aware=pc == 'turn_routing' and aid != 'urp.reset_dp', guarantee=guarantee,
                        limits={'max_tasks': limit} if limit else {}, available=True, unavailable_reason=None,
                        params=PARAMS, description=('松弛最优解可能违反转弯约束；独立检查不通过则禁止仿真。' if aid == 'urp.reset_dp' else
                            '覆盖基线允许原地转向，不满足 Dubins 最小转弯半径；仅评估内缩作业区，覆盖率另报。' if pc == 'coverage' else
                            '项目精确算法；最优性限于所声明的离散路网与约束，结果经原图独立检查。' if source == 'project' else
                            '输出任务顺序与路线证据，经独立检查器重新计算。第三方仅优化取整成本，无最优保证。')))
    f2c_status=f2c_coverage.available()
    for pattern in ('boustrophedon', 'snake'):
        out.append(dict(id='f2c.' + pattern, name='Fields2Cover ' + pattern, problem_classes=['coverage'], family='coverage',
                        source='third_party', origin='Fields2Cover SG/RP + Dubins（本地原生扩展 SHA256 '+str(f2c_status.get('binary_sha256','missing'))+'）', version=f2c_status['version'], turn_aware=True, guarantee='none', limits={},
                        available=f2c_status['available'], unavailable_reason=f2c_status['reason'], params=PARAMS, description='凸田块内缩作业区覆盖；F2C 排序和 Dubins 连接，经整段足迹、采样曲率独立检查。不处理凹区域分解，不承诺全田块覆盖。'))
    return out


def assignments(matrix, demands, capacity, engine, params):
    """Return client indices (depot=0). Integer matrix is explicitly a search surrogate."""
    if any(d > capacity for d in demands):
        return None
    n = len(demands)
    if engine == 'pyvrp':
        from pyvrp import Model
        from pyvrp.stop import MaxRuntime
        model = Model()
        locations = [model.add_location(i, 0) for i in range(n)]
        depot = model.add_depot(locations[0])
        for i in range(1, n):
            model.add_client(locations[i], delivery=demands[i])
        model.add_vehicle_type(num_available=n-1, capacity=capacity, start_depot=depot, end_depot=depot)
        for i in range(n):
            for j in range(n):
                model.add_edge(locations[i], locations[j], distance=int(matrix[i][j]))
        result = model.solve(MaxRuntime(params.get('time_limit_s', 3)), seed=params.get('seed', 42), display=False)
        # PyVRP 0.14 uses typed, zero-based client activities (depots have a
        # separate index space), unlike the older Route.visits() API.
        return [[a.idx+1 for a in r if a.is_client()] for r in result.best.routes()] if result.best.is_feasible() else None
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    manager = pywrapcp.RoutingIndexManager(n, n-1, 0)
    routing = pywrapcp.RoutingModel(manager)
    distance = routing.RegisterTransitCallback(lambda i, j: int(matrix[manager.IndexToNode(i)][manager.IndexToNode(j)]))
    routing.SetArcCostEvaluatorOfAllVehicles(distance)
    demand = routing.RegisterUnaryTransitCallback(lambda i: demands[manager.IndexToNode(i)])
    routing.AddDimensionWithVehicleCapacity(demand, 0, [capacity]*(n-1), True, 'Capacity')
    p = pywrapcp.DefaultRoutingSearchParameters()
    p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    p.time_limit.FromMilliseconds(max(1, round(params.get('time_limit_s', 3)*1000)))
    solution = routing.SolveWithParameters(p)
    if solution is None:
        return None
    routes = []
    for v in range(n-1):
        idx, route = routing.Start(v), []
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            if node: route.append(node)
            idx = solution.Value(routing.NextVar(idx))
        if route: routes.append(route)
    return routes


def map_check(world, routes):
    g = maps.load(world)
    violations, best = [], math.inf
    threshold = maps.ROBOT_RADIUS_M + maps.MAP_CHECK_MARGIN_M
    for ri, r in enumerate(routes):
        for si, (a, b) in enumerate(zip(r['polyline'], r['polyline'][1:])):
            clearance, point = maps.segment_clearance(g, a, b)
            best = min(best, clearance)
            if clearance < threshold:
                violations.append(dict(route=ri, segment=si, point=list(point), clearance_m=clearance))
    return dict(checked=bool(routes), collision_free=bool(routes) and not violations,
                min_clearance_m=best if math.isfinite(best) else None, robot_radius_m=maps.ROBOT_RADIUS_M,
                margin_m=maps.MAP_CHECK_MARGIN_M, violations=violations,
                method='整条线段半栅格采样 + EDT 保守单元/采样误差下界；未知及地图外按障碍')


def coverage(inst):
    from shapely.geometry import Polygon, LineString
    from shapely.ops import unary_union
    area = Polygon(inst['field'], inst.get('obstacles', []))
    interior = area.buffer(-inst['headland_width'])
    if interior.is_empty:
        return [], {'valid': False, 'errors': ['内缩作业区为空']}, {}
    x0, y0, x1, y1 = interior.bounds
    step = inst['swath_width']
    points, strips = [], []
    y, row = y0 + min(step/2, (y1-y0)/2), 0
    while y < y1:
        cut = interior.intersection(LineString([(x0-1, y), (x1+1, y)]))
        lines = [cut] if cut.geom_type == 'LineString' else list(getattr(cut, 'geoms', []))
        for line in lines:
            if line.geom_type != 'LineString' or line.is_empty: continue
            pair = list(line.coords)
            if row % 2: pair.reverse()
            points.extend(pair); strips.append(line.buffer(step/2, cap_style=2))
            row += 1
        y += step
    if len(points) < 2: return [], {'valid': False, 'errors': ['没有作业行']}, {}
    path = LineString(points)
    # Independently recompute swept footprint, including connectors (not merely swath endpoints).
    valid = area.covers(path.buffer(inst['robot_width']/2))
    covered = unary_union(strips).intersection(area).area
    return [dict(vehicle=0, nodes=None, sequence=[], services=[], polyline=points, cost=path.length, load=0)], \
        dict(valid=valid, errors=[] if valid else ['连接段/机器人占用超出田块或穿越障碍'], computed_cost=path.length,
             checker='urp_lab.solvers.coverage / Shapely swept-footprint', source='panel_baseline'), \
        dict(coverage_area_m2=covered, field_area_m2=area.area, coverage_fraction=covered/area.area,
             working_area_fraction=unary_union(strips).intersection(interior).area/interior.area,
             turn_radius_enforced=False, coverage_scope='内缩作业区；地头未作业；转弯半径未约束')


def run_algorithm(scenario, instance, algorithm_id, params):
    start, cpu = time.perf_counter(), time.process_time()
    alg = next(a for a in catalog() if a['id'] == algorithm_id)
    pc = scenario['problem_class']; extra = {}; raw = None
    if not alg['available']: raise ValueError(alg['unavailable_reason'])
    if pc == 'turn_routing':
        n = len(instance['customers'])
        if n > alg['limits'].get('max_tasks', 200): raise ValueError('超过该算法可用任务数上限')
        if instance.get('fleet_limit') is not None: raise ValueError('此适配器尚不支持 fleet_limit')
        if algorithm_id.startswith('urp.'):
            raw = oracle.solve(instance) if algorithm_id == 'urp.raw_oracle' else solver.solve(instance, 'reset' if algorithm_id == 'urp.reset_dp' else 'mode')[0]
            status = raw['status']
        else:
            tab = solver.preprocess(instance, 'reset')
            matrix = [[0] + tab['start']] + [[tab['end'][i]] + [0 if i==j else tab['conn'][i][j] for j in range(n)] for i in range(n)]
            matrix = [[int(c) if math.isfinite(c) else 10**9 for c in row] for row in matrix]
            seqs = assignments(matrix, [0]+[c['demand'] for c in instance['customers']], instance['capacity'], algorithm_id.split('.')[0], params)
            ev = evaluate_candidate.evaluate(instance, {'service_sequences': [[instance['customers'][i-1]['id'] for i in r] for r in seqs]}) if seqs else {}
            raw = ev.get('solution', {'status': 'no_solution', 'cost': None, 'routes': []})
            status = 'feasible' if ev.get('accepted') else 'no_solution'
        check = checker.check(instance, raw) if raw['routes'] else None
        if check: check.update(checker='src/research/src/urp_research/turn_modes/checker.py', source='project')
        tasks = {c['id']: c for c in instance['customers']}
        routes = [dict(vehicle=i, nodes=r['nodes'], sequence=[s['customer'] for s in r['services']],
                       services=[dict(task=s['customer'], position=s['position']) for s in r['services']],
                       polyline=[instance.get('coordinates', {}).get(str(v)) for v in r['nodes']], cost=r['cost'],
                       load=sum(tasks[s['customer']]['demand'] for s in r['services']), mode_chain=r.get('mode_chain')) for i,r in enumerate(raw['routes'])]
        for r in routes:
            if any(p is None for p in r['polyline']): r['polyline'] = []
        objective = raw['cost']
        extra['forbidden_turn_violations'] = sum('forbidden_turn' in e for e in (check or {}).get('errors', []))
        extra['turn_penalty_total'] = sum(dict((tuple(t[:3]),t[3]) for t in instance['turn_penalties']).get(t,0) for r in routes for t in zip(r['nodes'],r['nodes'][1:],r['nodes'][2:]))
    elif pc == 'euclidean_cvrp':
        pts = instance['coordinates']; dem = instance['demands']; cap = instance['capacity']
        matrix = [[round(math.dist(a,b)*1000) for b in pts] for a in pts]
        seqs = assignments(matrix, dem, cap, algorithm_id.split('.')[0], params)
        routes = []
        for i,seq in enumerate(seqs or []):
            nodes = [0]+seq+[0]
            routes.append(dict(vehicle=i, nodes=nodes, sequence=seq, services=[dict(task=t,position=j+1) for j,t in enumerate(seq)],
                               polyline=[pts[j] for j in nodes], cost=sum(math.dist(pts[a],pts[b]) for a,b in zip(nodes,nodes[1:])), load=sum(dem[j] for j in seq)))
        objective = sum(r['cost'] for r in routes) if routes else None
        errors = []
        if Counter(t for r in routes for t in r['sequence']) != Counter(range(1,len(pts))): errors.append('exact_once_service')
        if any(sum(dem[j] for j in r['nodes']) > cap for r in routes): errors.append('capacity')
        check = dict(valid=not errors, errors=errors, computed_cost=objective, checker='urp_lab.solvers / 原始欧氏距离与需求复算', source='panel_baseline') if routes else None
        status = 'feasible' if routes else ('infeasible' if max(dem)>cap else 'no_solution')
        raw = {'assignment': seqs, 'search_cost_scale': 1000, 'reported_cost': 'unrounded Euclidean'}
    else:
        if algorithm_id.startswith('f2c.'):
            routes,check,extra,raw=f2c_coverage.solve(instance,algorithm_id.split('.')[1])
        else: routes, check, extra = coverage(instance)
        objective = sum(r['cost'] for r in routes) if routes else None
        status = 'feasible' if routes and check['valid'] else 'no_solution'
        if status == 'no_solution': routes, objective = [], None
    mc = map_check(scenario['frame']['world'], routes) if scenario['frame']['kind']=='map' else None
    length = sum(math.dist(a,b) for r in routes for a,b in zip(r['polyline'], r['polyline'][1:]))
    return dict(status=status, objective=dict(value=objective, unit=scenario['cost_unit'], lower_bound=None), routes=routes,
                check=check, map_check=mc, algorithm={k:alg[k] for k in ('id','name','source','origin','version')}, raw_result=raw,
                metrics=dict(cost=objective, length=length if routes else None, length_unit='m' if scenario['frame']['kind']=='map' else 'unitless',
                             n_routes=len(routes), n_tasks=len(instance.get('customers', instance.get('demands', [0])))-(0 if pc=='turn_routing' else 1),
                             wall_s=time.perf_counter()-start, cpu_s=time.process_time()-cpu, **extra))
