"""Multi-vehicle task allocation and routing on 2-D maps with obstacles (problem class `fleet_routing`).

Distances are true obstacle-avoiding shortest paths: a visibility graph over the robot-inflated obstacles
(exact for polygonal obstacles), all-pairs Dijkstra between depot and tasks. Solvers decide assignment and
order; routes are realised along those shortest paths and re-checked against the map independently.
"""
from __future__ import annotations

import math
import time

import numpy as np

COLORS = ['#007aff', '#ff6b00', '#34a853', '#a142f4', '#e8336d', '#00a6a6', '#c49000', '#5856d6', '#8e5a2b', '#2f7d32',
          '#d81b60', '#1e88e5']


# ----------------------------------------------------------------- geometry --
def free_space(inst):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    r = inst['robot_radius']
    boundary = Polygon(inst['boundary'])
    blocked = unary_union([Polygon(o['polygon']).buffer(r, quad_segs=4) for o in inst.get('obstacles') or []]) \
        if inst.get('obstacles') else None
    free = boundary.buffer(-r, join_style=2)
    if blocked is not None and not blocked.is_empty:
        free = free.difference(blocked)
    return free, boundary, blocked


class Graph:
    """Visibility graph between depot/tasks and obstacle/boundary corners, with all-pairs shortest paths."""

    def __init__(self, inst):
        from shapely.geometry import LineString, Point, Polygon
        from shapely.prepared import prep
        t0 = time.perf_counter()
        self.free, self.boundary, _ = free_space(inst)
        self.points = [tuple(inst['depot'])] + [tuple(t['xy']) for t in inst['tasks']]
        r = inst['robot_radius']
        corners = []
        for o in inst.get('obstacles') or []:
            ring = Polygon(o['polygon']).buffer(r + 0.05, quad_segs=2, join_style=2).simplify(0.05)
            corners += list(ring.exterior.coords)[:-1]
        inner = Polygon(inst['boundary']).buffer(-(r + 0.05), join_style=2)
        if not inner.is_empty and inner.geom_type == 'Polygon' and inner.area < inner.convex_hull.area - 1e-6:
            corners += [p for p in list(inner.exterior.coords)[:-1]]
        pfree = prep(self.free.buffer(1e-6))
        corners = [c for c in corners if pfree.contains(Point(c))]
        self.nodes = self.points + corners
        n = len(self.nodes)
        P = np.array(self.nodes, dtype=float)
        W = np.full((n, n), np.inf)
        simple = not inst.get('obstacles') and self.boundary.equals(self.boundary.convex_hull)
        for i in range(n):
            W[i, i] = 0.0
            for j in range(i + 1, n):
                if simple or pfree.covers(LineString([self.nodes[i], self.nodes[j]])):
                    W[i, j] = W[j, i] = float(np.hypot(*(P[i] - P[j])))
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import dijkstra
        mat = csr_matrix(np.where(np.isfinite(W), W, 0.0))
        k = len(self.points)
        self.dist, self.pred = dijkstra(mat, directed=False, indices=list(range(k)), return_predecessors=True)
        self.D = self.dist[:, :k]
        self.build_s = time.perf_counter() - t0
        self.euclid = np.hypot(*(P[:k, None, :] - P[None, :k, :]).transpose(2, 0, 1))

    def path(self, a: int, b: int) -> list[list[float]]:
        if a == b:
            return [list(self.points[a])]
        seq, cur = [b], b
        while cur != a:
            cur = int(self.pred[a, cur])
            if cur < 0:
                raise ValueError('两点之间不连通（被障碍隔断）')
            seq.append(cur)
        return [list(self.nodes[i]) for i in reversed(seq)]

    def route_polyline(self, stops: list[int]) -> list[list[float]]:
        pts = []
        for a, b in zip(stops, stops[1:]):
            seg = self.path(a, b)
            pts += seg if not pts else seg[1:]
        return pts


# ----------------------------------------------------------------- solvers --
def _tour_cost(D, tour):
    return sum(D[a, b] for a, b in zip(tour, tour[1:]))


def two_opt(D, tour, deadline):
    """2-opt improvement of a closed tour [0, ..., 0]."""
    best = tour[:]
    improved = True
    while improved and time.perf_counter() < deadline:
        improved = False
        for i in range(1, len(best) - 2):
            for j in range(i + 1, len(best) - 1):
                a, b, c, d = best[i - 1], best[i], best[j], best[j + 1]
                if D[a, c] + D[b, d] < D[a, b] + D[c, d] - 1e-9:
                    best[i:j + 1] = best[i:j + 1][::-1]
                    improved = True
    return best


def tsp(D, nodes, deadline):
    """Nearest-neighbour + 2-opt tour from the depot through `nodes`."""
    left, tour = set(nodes), [0]
    while left:
        nxt = min(left, key=lambda j: (D[tour[-1], j], j))
        tour.append(nxt)
        left.remove(nxt)
    return two_opt(D, tour + [0], deadline)


def split_capacity(order, demand, cap):
    routes, cur, load = [], [], 0
    for t in order:
        if load + demand[t] > cap and cur:
            routes.append(cur)
            cur, load = [], 0
        cur.append(t)
        load += demand[t]
    if cur:
        routes.append(cur)
    return routes


def sweep(inst, D, demand, deadline):
    """Gillett–Miller sweep: polar order around the depot, split by capacity, 2-opt each route."""
    dx, dy = inst['depot']
    n = len(inst['tasks'])
    angles = {i: math.atan2(inst['tasks'][i - 1]['xy'][1] - dy, inst['tasks'][i - 1]['xy'][0] - dx) for i in range(1, n + 1)}
    best = None
    for start in sorted(angles, key=angles.get)[:: max(1, n // 12)]:
        order = sorted(angles, key=lambda i: (angles[i] - angles[start]) % (2 * math.pi))
        routes = [tsp(D, r, deadline)[1:-1] for r in split_capacity(order, demand, inst['vehicles']['capacity'])]
        cost = sum(_tour_cost(D, [0] + r + [0]) for r in routes)
        if best is None or cost < best[0]:
            best = (cost, routes)
    return best[1]


def cluster_first(inst, D, demand, deadline, seed):
    """Capacity-aware k-means on task positions (k = fleet size), then a 2-opt tour per cluster."""
    rng = np.random.default_rng(seed)
    K, cap = inst['vehicles']['count'], inst['vehicles']['capacity']
    X = np.array([t['xy'] for t in inst['tasks']], dtype=float)
    n = len(X)
    k = max(1, min(K, n))
    centers = X[rng.choice(n, k, replace=False)]
    for _ in range(30):
        order = np.argsort(-np.array([demand[i + 1] for i in range(n)]))
        loads, assign = np.zeros(k), np.zeros(n, dtype=int)
        for i in order:
            pref = np.argsort(np.hypot(*(centers - X[i]).T))
            limit = cap if inst['vehicles'].get('trips', 'multi') != 'multi' else math.inf
            choice = next((c for c in pref if loads[c] + demand[i + 1] <= limit), pref[0])
            assign[i] = choice
            loads[choice] += demand[i + 1]
        new = np.array([X[assign == c].mean(axis=0) if (assign == c).any() else centers[c] for c in range(k)])
        if np.allclose(new, centers):
            break
        centers = new
    routes, owner = [], []
    for c in range(k):
        members = [i + 1 for i in range(n) if assign[i] == c]
        for part in split_capacity(members, demand, cap):
            routes.append(tsp(D, part, deadline)[1:-1])
            owner.append(c)
    return routes, owner


def savings(inst, D, demand):
    """Clarke–Wright parallel savings on the obstacle-aware distance matrix."""
    cap = inst['vehicles']['capacity']
    n = len(inst['tasks'])
    route = {i: [i] for i in range(1, n + 1)}
    owner = {i: i for i in route}
    load = {i: demand[i] for i in route}
    pairs = sorted(((D[0, a] + D[0, b] - D[a, b], a, b) for a in range(1, n + 1) for b in range(a + 1, n + 1)), reverse=True)
    for s, a, b in pairs:
        if s <= 0:
            break
        ra, rb = owner[a], owner[b]
        if ra == rb or load[ra] + load[rb] > cap:
            continue
        A, B = route[ra], route[rb]
        if a not in (A[0], A[-1]) or b not in (B[0], B[-1]):
            continue
        if A[-1] != a:
            A = A[::-1]
        if B[0] != b:
            B = B[::-1]
        route[ra] = A + B
        load[ra] += load[rb]
        for t in B:
            owner[t] = ra
        del route[rb], load[rb]
    return list(route.values())


def metaheuristic(engine, inst, D, demand, params, K):
    """PyVRP or OR-Tools minimising total distance with at most K routes."""
    cap = inst['vehicles']['capacity']
    n = len(inst['tasks'])
    M = np.rint(D * 100).astype(np.int64)
    limit = float(params.get('time_limit_s', 3))
    trace = []
    if engine == 'pyvrp':
        from pyvrp import Model
        from pyvrp.stop import MaxRuntime
        model = Model()
        locs = [model.add_location(i, 0) for i in range(n + 1)]
        depot = model.add_depot(locs[0])
        for i in range(1, n + 1):
            model.add_client(locs[i], delivery=demand[i])
        model.add_vehicle_type(num_available=K, capacity=cap, start_depot=depot, end_depot=depot)
        for i in range(n + 1):
            for j in range(n + 1):
                model.add_edge(locs[i], locs[j], distance=int(M[i, j]))
        result = model.solve(MaxRuntime(limit), seed=int(params.get('seed', 42)), display=False, collect_stats=True)
        elapsed, best = 0.0, math.inf
        for dt, datum in zip(result.stats.runtimes, result.stats.data):
            elapsed += dt
            if datum.best_feas and datum.best_cost < best:
                best = datum.best_cost
                trace.append([round(elapsed, 4), best / 100])
        if not result.best.is_feasible():
            return None, trace
        return [[a.idx + 1 for a in r if a.is_client()] for r in result.best.routes()], trace
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    manager = pywrapcp.RoutingIndexManager(n + 1, K, 0)
    routing = pywrapcp.RoutingModel(manager)
    cb = routing.RegisterTransitCallback(lambda i, j: int(M[manager.IndexToNode(i), manager.IndexToNode(j)]))
    routing.SetArcCostEvaluatorOfAllVehicles(cb)
    dem = routing.RegisterUnaryTransitCallback(lambda i: demand[manager.IndexToNode(i)])
    routing.AddDimensionWithVehicleCapacity(dem, 0, [cap] * K, True, 'Capacity')
    t0 = time.perf_counter()

    def on_solution():
        v = routing.CostVar().Value() / 100
        if not trace or v < trace[-1][1]:
            trace.append([round(time.perf_counter() - t0, 4), v])
    routing.AddAtSolutionCallback(on_solution)
    p = pywrapcp.DefaultRoutingSearchParameters()
    p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    p.time_limit.FromMilliseconds(max(1, round(limit * 1000)))
    sol = routing.SolveWithParameters(p)
    if sol is None:
        return None, trace
    routes = []
    for v in range(K):
        idx, r = routing.Start(v), []
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            if node:
                r.append(node)
            idx = sol.Value(routing.NextVar(idx))
        if r:
            routes.append(r)
    return routes, trace


def ortools_makespan(inst, D, demand, params, K, multi):
    """OR-Tools on the real fleet: each vehicle may return to the depot to unload (optional reload
    nodes, as in the OR-Tools reload sample), and a global span cost on the time dimension
    minimises the latest finish. Returns trips, the vehicle of each trip and the trace (seconds)."""
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    cap = inst['vehicles']['capacity']
    speed = inst['vehicles'].get('speed_mps') or 1.0
    n = len(inst['tasks'])
    service = [0.0] + [float(t.get('service_s', 0) or 0) for t in inst['tasks']]
    reloads = max(0, math.ceil(sum(demand) / cap)) if multi else 0
    orig = list(range(n + 1)) + [0] * reloads          # node -> matrix index; reload copies sit on the depot
    T = np.rint(10 * (D[np.ix_(orig, orig)] / speed + np.array([service[o] for o in orig])[:, None])).astype(np.int64)
    np.fill_diagonal(T, 0)
    load = demand + [-cap] * reloads
    manager = pywrapcp.RoutingIndexManager(n + 1 + reloads, K, 0)
    routing = pywrapcp.RoutingModel(manager)
    cb = routing.RegisterTransitCallback(lambda i, j: int(T[manager.IndexToNode(i), manager.IndexToNode(j)]))
    routing.SetArcCostEvaluatorOfAllVehicles(cb)
    routing.AddDimension(cb, 0, int(T.max() * (n + reloads + 2)), True, 'Time')
    time_dim = routing.GetDimensionOrDie('Time')
    time_dim.SetGlobalSpanCostCoefficient(100)
    dem = routing.RegisterUnaryTransitCallback(lambda i: int(load[manager.IndexToNode(i)]))
    routing.AddDimension(dem, cap, cap, True, 'Capacity')
    cap_dim = routing.GetDimensionOrDie('Capacity')
    for node in range(1, n + 1):
        cap_dim.SlackVar(manager.NodeToIndex(node)).SetValue(0)
    for node in range(n + 1, n + 1 + reloads):
        idx = manager.NodeToIndex(node)
        cap_dim.SlackVar(idx).SetRange(0, cap)        # unloading resets the load to zero
        routing.AddDisjunction([idx], 0)               # reloads are optional and free
    t0, trace = time.perf_counter(), []

    def on_solution():
        try:
            span = max(time_dim.CumulVar(routing.End(v)).Value() for v in range(K)) / 10
        except Exception:  # noqa: BLE001 - fall back to the raw cost if cumuls are not readable here
            span = routing.CostVar().Value() / 1000
        if not trace or span < trace[-1][1]:
            trace.append([round(time.perf_counter() - t0, 4), span])
    routing.AddAtSolutionCallback(on_solution)
    p = pywrapcp.DefaultRoutingSearchParameters()
    p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    p.time_limit.FromMilliseconds(max(1, round(float(params.get('time_limit_s', 3)) * 1000)))
    sol = routing.SolveWithParameters(p)
    if sol is None:
        return None, None, trace
    trips, owner = [], []
    for v in range(K):
        idx, cur = routing.Start(v), []
        while True:
            idx = sol.Value(routing.NextVar(idx))
            node = manager.IndexToNode(idx)
            if routing.IsEnd(idx) or node > n:
                if cur:
                    trips.append(cur)
                    owner.append(v)
                cur = []
                if routing.IsEnd(idx):
                    break
            else:
                cur.append(node)
    return trips, owner, trace


# ------------------------------------------------------------------ check --
def check(inst, routes):
    """Independent verification from the raw map: coverage of tasks, loads, fleet size, collision-free geometry."""
    from shapely.geometry import LineString
    from shapely.prepared import prep
    free, boundary, _ = free_space(inst)
    pfree = prep(free.buffer(1e-4))
    errors, details = [], []
    ids = [t['id'] for t in inst['tasks']]
    served = [s for r in routes for s in r['sequence']]
    missing = sorted(set(ids) - set(served))
    dup = sorted({s for s in served if served.count(s) > 1})
    if missing:
        errors.append(f'{len(missing)} 个任务未被分配：{missing[:8]}')
    if dup:
        errors.append(f'任务重复服务：{dup[:8]}')
    if len(routes) > inst['vehicles']['count']:
        errors.append(f"使用 {len(routes)} 台车，超过车队规模 {inst['vehicles']['count']}")
    demand = {t['id']: t['demand'] for t in inst['tasks']}
    total = 0.0
    for r in routes:
        trips = r.get('trips') or [r['sequence']]
        load = max((sum(demand[s] for s in trip) for trip in trips), default=0)
        if load > inst['vehicles']['capacity']:
            errors.append(f"车辆 {r['vehicle_name']} 单趟载重 {load} 超过容量 {inst['vehicles']['capacity']}")
        if inst['vehicles'].get('trips', 'multi') != 'multi' and len(trips) > 1:
            errors.append(f"车辆 {r['vehicle_name']} 跑了 {len(trips)} 趟，但当前设置为单趟")
        pts = r['polyline']
        length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        bad = [i for i, (a, b) in enumerate(zip(pts, pts[1:])) if not pfree.covers(LineString([a, b]))]
        if bad:
            errors.append(f"车辆 {r['vehicle_name']} 有 {len(bad)} 段路线穿过障碍或越出边界")
        if pts and (math.dist(pts[0], inst['depot']) > 1e-6 or math.dist(pts[-1], inst['depot']) > 1e-6):
            errors.append(f"车辆 {r['vehicle_name']} 未从车库出发并返回")
        total += length
        details.append({'vehicle': r['vehicle_name'], 'load': load, 'length_m': length, 'collisions': len(bad)})
    return {'valid': not errors, 'errors': errors, 'computed_cost': total, 'routes': details,
            'checker': 'urp_lab.solvers.fleet.check · 原始地图几何复算（Shapely）', 'source': 'panel_baseline'}


# ------------------------------------------------------------------ solve --
def assign_trips(trip_times, K):
    """Longest-processing-time-first assignment of trips to K vehicles (minimises the latest finish)."""
    load, out = [0.0] * K, [[] for _ in range(K)]
    for i in sorted(range(len(trip_times)), key=lambda i: -trip_times[i]):
        v = min(range(K), key=lambda v: (load[v], v))
        out[v].append(i)
        load[v] += trip_times[i]
    return out


def solve(scenario, inst, algorithm_id, params):
    t0 = time.perf_counter()
    graph = Graph(inst)
    D = graph.D
    n = len(inst['tasks'])
    unreachable = [inst['tasks'][i - 1]['label'] for i in range(1, n + 1) if not np.isfinite(D[0, i])]
    if unreachable:
        raise ValueError(f'有任务点与车库不连通（被障碍隔断）：{unreachable[:6]}')
    demand = [0] + [t['demand'] for t in inst['tasks']]
    K, cap = inst['vehicles']['count'], inst['vehicles']['capacity']
    multi = inst['vehicles'].get('trips', 'multi') == 'multi'
    if not multi and sum(demand) > K * cap:
        return [], None, {'fleet_capacity': K * cap, 'total_demand': sum(demand)}, \
            {'reason': f'总需求 {sum(demand)} 超过车队单趟总容量 {K} × {cap}；可允许多趟往返或增加车辆/容量'}, 'infeasible', []
    deadline = time.perf_counter() + float(params.get('time_limit_s', 3))
    route_cap = n if multi else K
    trace, owner = [], None
    if algorithm_id == 'pyvrp.fleet':
        trips, trace = metaheuristic('pyvrp', inst, D, demand, params, route_cap)
    elif algorithm_id == 'ortools.fleet' and inst.get('objective') == 'makespan':
        trips, owner, trace = ortools_makespan(inst, D, demand, params, K, multi)
    elif algorithm_id == 'ortools.fleet':
        trips, trace = metaheuristic('ortools', inst, D, demand, params, route_cap)
    elif algorithm_id == 'panel.sweep':
        trips = sweep(inst, D, demand, deadline)
    elif algorithm_id == 'panel.cluster_first':
        trips, owner = cluster_first(inst, D, demand, deadline, int(params.get('seed', 42)))
    elif algorithm_id == 'panel.savings_fleet':
        trips = [two_opt(D, [0] + r + [0], deadline)[1:-1] for r in savings(inst, D, demand)]
    else:
        raise ValueError(f'未知算法 {algorithm_id}')
    if not trips:
        return [], None, {}, {'reason': '求解器没有返回可行方案'}, 'no_solution', trace
    speed = inst['vehicles'].get('speed_mps') or 1.0
    trip_len = [float(sum(D[a, b] for a, b in zip([0] + r + [0], r + [0]))) for r in trips]
    trip_time = [L / speed + sum(inst['tasks'][i - 1].get('service_s', 0) for i in r) for L, r in zip(trip_len, trips)]
    if owner is not None:
        plan = [[i for i, o in enumerate(owner) if o == v] for v in range(K)]
    elif multi or len(trips) <= K:
        plan = assign_trips(trip_time, K) if multi else [[i] for i in range(len(trips))]
    else:
        plan = [[i] for i in range(len(trips))]  # more single trips than vehicles: the checker reports it
    names = inst['vehicles'].get('names') or []
    routes = []
    for v, mine in enumerate(p for p in plan if p):
        stops = [0] + [s for i in mine for s in trips[i] + [0]]
        pts = graph.route_polyline(stops)
        routes.append({'vehicle': v, 'vehicle_name': names[v] if v < len(names) else f'车{v + 1}', 'color': COLORS[v % len(COLORS)],
                       'nodes': None, 'sequence': [inst['tasks'][s - 1]['id'] for i in mine for s in trips[i]],
                       'trips': [[inst['tasks'][s - 1]['id'] for s in trips[i]] for i in mine],
                       'services': [{'task': inst['tasks'][s - 1]['id'], 'position': None} for i in mine for s in trips[i]],
                       'polyline': pts, 'cost': sum(trip_len[i] for i in mine),
                       'load': max(sum(demand[s] for s in trips[i]) for i in mine),
                       'duration_s': sum(trip_time[i] for i in mine)})
    chk = check(inst, routes)
    lengths = [r['cost'] for r in routes]
    euclid = sum(float(graph.euclid[a, b]) for r in trips for a, b in zip([0] + r, r + [0]))
    metrics = {'total_distance_m': sum(lengths), 'makespan_s': max(r['duration_s'] for r in routes),
               'longest_route_m': max(lengths), 'vehicles_used': len(routes), 'fleet_size': K, 'trips': len(trips),
               'balance_cv': float(np.std(lengths) / np.mean(lengths)) if len(lengths) > 1 and np.mean(lengths) else 0.0,
               'capacity_utilization': sum(demand) / (len(trips) * cap), 'detour_ratio': sum(lengths) / euclid if euclid else 1.0,
               'graph_nodes': len(graph.nodes), 'graph_build_s': graph.build_s, 'objective_mode': inst.get('objective', 'total_distance'),
               'per_vehicle': [{'vehicle': r['vehicle_name'], 'color': r['color'], 'tasks': len(r['sequence']), 'trips': len(r['trips']),
                                'load': r['load'], 'length_m': r['cost'], 'duration_s': r['duration_s']} for r in routes]}
    raw = {'trips': trips, 'vehicle_plan': plan, 'distance_model': '机器人半径膨胀障碍上的可视图最短路（多边形障碍下精确）',
           'search_scale': 'PyVRP / OR-Tools 用厘米取整距离搜索，结果按米复算', 'planning_s': time.perf_counter() - t0,
           'trip_assignment': ('OR-Tools 直接为各车安排往返（车库卸载点），时间维度跨度代价最小化最晚完成'
                               if algorithm_id == 'ortools.fleet' and inst.get('objective') == 'makespan'
                               else '多趟：先求各趟路线，再按最长处理时间优先分配到各车' if multi else '单趟：每车一条路线')}
    # The plan is returned even when verification fails, so the violations can be shown on the map.
    return routes, chk, metrics, raw, 'feasible', trace


def objective_value(inst, metrics):
    return metrics['makespan_s'] if inst.get('objective') == 'makespan' else metrics['total_distance_m']
