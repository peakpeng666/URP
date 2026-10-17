"""Multi-vehicle task allocation and routing on 2-D maps with obstacles (problem class `fleet_routing`).

Distances are shortest paths on the constructed travel graph (`vehicles.travel`):
- `free`: anywhere clear of obstacles — a visibility graph over the robot-inflated obstacles (exact for
  the generated visibility graph);
- `rows`: along the lanes between crop rows, entering and leaving them at the headland or a farm road,
  never across rows (`urp_lab.lanes`); each task is served from the nearest point of that network.
All-pairs Dijkstra runs between the depot and the service positions. Solvers decide assignment and order;
routes are realised along those shortest paths and re-checked against the map independently.
"""
from __future__ import annotations

import math
import time
from collections import Counter, defaultdict

import numpy as np

from .. import lanes
from ..lanes import free_space
from ..path_geometry import arc_lengths, locate

COLORS = ['#007aff', '#ff6b00', '#34a853', '#a142f4', '#e8336d', '#00a6a6', '#c49000', '#5856d6', '#8e5a2b', '#2f7d32',
          '#d81b60', '#1e88e5']


# ------------------------------------------------------------------- fleet --
def fleet_classes(inst):
    """Ordered vehicle classes (`vehicles.fleet`); legacy homogeneous instances synthesise one."""
    veh = inst['vehicles']
    fleet = veh.get('fleet')
    if isinstance(fleet, list) and fleet:
        return fleet
    return [{'name': '同型车', 'count': veh['count'], 'capacity': veh['capacity'],
             'speed_mps': float(veh.get('speed_mps') or 1.0), 'robot_radius': inst['robot_radius'],
             'min_turn_radius_m': 0.0, 'payload': 'load'}]


def vehicle_table(inst):
    """[(vehicle_index, class_index, class, depot_index)] flattened in class order.

    Vehicle indexes match route `vehicle`. With multiple depots the vehicles are assigned
    round-robin over `depots` in table order — a deterministic, documented policy."""
    nd = len(depot_list(inst))
    out, idx = [], 0
    for ci, cls in enumerate(fleet_classes(inst)):
        for _ in range(cls['count']):
            out.append((idx, ci, cls, idx % nd))
            idx += 1
    return out


def depot_list(inst):
    """Ordered depot coordinates (`depots`), single `[depot]` for legacy instances."""
    depots = inst.get('depots')
    if isinstance(depots, list) and len(depots) >= 1:
        return depots
    return [inst['depot']]


def _circumradius(a, b, c):
    """Radius of the circle through three points (inf when collinear)."""
    A, B, C = math.dist(a, b), math.dist(b, c), math.dist(a, c)
    area = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
    return A * B * C / (4 * area) if area > 1e-12 else math.inf


def min_curvature_radius(pts):
    """Smallest sampled turning radius of a polyline (consecutive triplets; exact on circular arcs)."""
    return min((_circumradius(pts[i], pts[i + 1], pts[i + 2]) for i in range(len(pts) - 2)), default=math.inf)


def dubins_realize(waypoints, min_radius, step=0.05):
    """Curvature-bounded realisation of a waypoint sequence (Dubins, 1957; OMPL implementation).

    The heading is carried between legs: each leg starts at the previous leg's end heading and ends
    aligned with its own segment direction, so every heading change becomes a bounded-curvature
    turn instead of a corner. Returns (dense polyline at ≈ `step` spacing, per-waypoint index in it)."""
    from ompl import base as ob, geometric as og
    clean, origin = [], []
    for p in waypoints:
        if not clean or math.dist(p, clean[-1]) > 1e-9:
            clean.append(list(p))
        origin.append(len(clean) - 1)
    space = ob.DubinsStateSpace(float(min_radius))
    si = ob.SpaceInformation(space)
    theta = math.atan2(clean[1][1] - clean[0][1], clean[1][0] - clean[0][0])
    pts, marks = [list(clean[0])], [0]
    for a, b in zip(clean, clean[1:]):
        heading = math.atan2(b[1] - a[1], b[0] - a[0])
        s0, s1 = space.allocState(), space.allocState()
        s0.setXY(*a); s0.setYaw(theta)
        s1.setXY(*b); s1.setYaw(heading)
        leg = og.PathGeometric(si, s0, s1)
        leg.interpolate(max(2, int(leg.length() / step) + 1))
        pts += [[s.getX(), s.getY()] for s in leg.getStates()[1:]]
        marks.append(len(pts) - 1)
        theta = heading
    return pts, [marks[origin[i]] for i in range(len(waypoints))]


# ----------------------------------------------------------------- geometry --
class Graph:
    """Visibility graph between depot/tasks and obstacle/boundary corners, with all-pairs shortest paths."""

    travel = 'free'
    info: dict = {}

    def __init__(self, inst):
        import shapely
        from shapely.geometry import Point, Polygon
        from shapely.prepared import prep
        t0 = time.perf_counter()
        self.free, self.boundary, _ = free_space(inst)
        self.points = [tuple(d) for d in depot_list(inst)] + [tuple(t['xy']) for t in inst['tasks']]
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
        np.fill_diagonal(W, 0.0)
        ii, jj = np.triu_indices(n, 1)
        # Batch GEOS predicates instead of constructing/calling a Python geometry
        # for every pair. Bound each batch to avoid quadratic temporary geometries.
        for start in range(0, len(ii), 8192):
            i, j = ii[start:start + 8192], jj[start:start + 8192]
            if not simple:
                segments = shapely.linestrings(np.stack((P[i], P[j]), axis=1))
                visible = shapely.covers(pfree.context, segments)
                i, j = i[visible], j[visible]
            W[i, j] = W[j, i] = np.hypot(*(P[i] - P[j]).T)
        from scipy.sparse import csr_matrix
        from scipy.sparse.csgraph import dijkstra
        # Explicit sparse zero entries are real edges between co-located tasks/depot.
        # Dense-to-sparse conversion drops them and invents positive detours.
        ii, jj = np.where(np.isfinite(W) & ~np.eye(n, dtype=bool))
        mat = csr_matrix((W[ii, jj], (ii, jj)), shape=(n, n))
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


class LaneGraph(Graph):
    """Travel graph along crop-row lanes, headlands and farm roads (`vehicles.travel = 'rows'`).

    Nodes: the depot, one service position per task (on its nearest lane or in the open area), the lane
    entries and the corners of the open area. Lane edges join consecutive nodes along each lane; edges in
    the open area are straight segments that stay inside it (every pair involving the depot, open-area
    stops or corners; between entries closer than `NEAR_M`)."""

    travel = 'rows'
    NEAR_M = 12.0

    def __init__(self, inst):
        from scipy.sparse import coo_matrix
        from scipy.sparse.csgraph import dijkstra
        from scipy.spatial import cKDTree
        from shapely.geometry import Point
        t0 = time.perf_counter()
        net = self.net = lanes.Network(inst)
        self.free, self.boundary = net.free, net.boundary
        for di, d in enumerate(depot_list(inst)):
            if not net.in_open((float(d[0]), float(d[1]))):
                raise ValueError(f'车库 {di + 1} 在作物行里：按行间通行时车辆从地头或机耕路出发，请把车库移到地头，或改为自由通行')
        nodes, special, on_lane, self.offsets = [tuple(depot_list(inst)[0])], [0], defaultdict(list), []
        for d in depot_list(inst)[1:]:
            special.append(len(nodes))
            nodes.append(tuple(d))
        for t in inst['tasks']:
            stop, lane, d = net.attach(t['xy'])
            if d > net.max_reach:
                raise ValueError(f"任务点 {t.get('label', t['id'])} 离最近的行间通道或地头 {d:.1f} m，按行间通行够不着；"
                                 '请把它移近作物行间，或改为自由通行')
            (on_lane[lane] if lane is not None else special).append(len(nodes))
            nodes.append(stop)
            self.offsets.append(d)
        self.points = list(nodes)
        k = len(nodes)
        edges: dict[tuple[int, int], float] = {}

        def link(i, j, w):
            key = (i, j) if i < j else (j, i)
            if i != j and w < edges.get(key, math.inf):
                edges[key] = float(w)
        entries = []
        for li, lane in enumerate(net.lanes):
            chain = [(lane.line.project(Point(nodes[i])), i) for i in on_lane.get(li, [])]
            for flag, xy, at in ((lane.entry_start, lane.start, 0.0), (lane.entry_end, lane.end, lane.line.length)):
                if flag:
                    entries.append(len(nodes))
                    chain.append((at, len(nodes)))
                    nodes.append(xy)
            chain.sort()
            for (s0, i), (s1, j) in zip(chain, chain[1:]):
                link(i, j, s1 - s0)
        corners = net.hubs()
        hubs = list(range(len(nodes), len(nodes) + len(corners)))
        nodes += corners
        P = np.array(nodes, dtype=float)
        pairs = {(min(i, j), max(i, j)) for i in special for j in special + entries + hubs if i != j}
        pairs |= {(i, j) for a, i in enumerate(hubs) for j in hubs[a + 1:]}
        pairs |= {(min(i, j), max(i, j)) for i in entries for j in hubs}
        if len(entries) > 1:
            near = cKDTree(P[entries]).query_pairs(self.NEAR_M)
            pairs |= {(min(entries[a], entries[b]), max(entries[a], entries[b])) for a, b in near}
        if pairs:
            ij = np.array(sorted(pairs))
            seen = net.visible(P[ij[:, 0]], P[ij[:, 1]])
            for (i, j), w in zip(ij[seen], np.hypot(*(P[ij[seen, 0]] - P[ij[seen, 1]]).T)):
                link(int(i), int(j), w)
        self.nodes = nodes
        n = len(nodes)
        if edges:
            ij = np.array(list(edges.keys()))
            mat = coo_matrix((np.array(list(edges.values())), (ij[:, 0], ij[:, 1])), shape=(n, n)).tocsr()
        else:
            mat = coo_matrix((n, n)).tocsr()
        self.dist, self.pred = dijkstra(mat, directed=False, indices=list(range(k)), return_predecessors=True)
        self.D = self.dist[:, :k]
        self.build_s = time.perf_counter() - t0
        Pk = P[:k]
        self.euclid = np.hypot(*(Pk[:, None, :] - Pk[None, :, :]).transpose(2, 0, 1))
        self.info = {'lanes': len(net.lanes), 'closed_lanes': net.closed, 'entries': len(entries), 'corners': len(hubs),
                     'edges': len(edges), 'service_offset_mean_m': float(np.mean(self.offsets)) if self.offsets else 0.0,
                     'service_offset_max_m': float(np.max(self.offsets)) if self.offsets else 0.0,
                     'plots': net.summary()['plots']}


def travel_graph(inst):
    return LaneGraph(inst) if inst['vehicles'].get('travel') == 'rows' else Graph(inst)


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
    """PyVRP or OR-Tools minimising total distance with at most K routes.

    Heterogeneous fleets (`vehicles.fleet`) map each class to its own vehicle type / capacity list;
    multiple depots (`depots`) start and end every pseudo-route at a depot (vehicles are assigned
    round-robin in table order). `K` is the pseudo-route budget as before (all tasks' worth in
    multi-trip mode). Returns (trips, trip_class, trip_depot, trace): the class and home depot of
    each trip; single-depot instances get depot 0, matching the legacy behaviour."""
    classes = fleet_classes(inst)
    hetero = len(classes) > 1
    multi = inst['vehicles'].get('trips', 'multi') == 'multi'
    depots = depot_list(inst)
    nd = len(depots)
    n = len(inst['tasks'])
    M = np.rint(D * 100).astype(np.int64)
    limit = float(params.get('time_limit_s', 3))
    trace = []
    real = [(ci, di) for _vi, ci, _cls, di in vehicle_table(inst)]
    if multi:
        groups = list(dict.fromkeys(real))
        pseudo = [key for key in groups for _ in range(n)]      # n pseudo-routes per (class, depot)
    else:
        pseudo = real
    if engine == 'pyvrp':
        from pyvrp import Model
        from pyvrp.stop import MaxRuntime
        model = Model()
        locs = [model.add_location(i, 0) for i in range(nd + n)]
        handles = [model.add_depot(locs[i]) for i in range(nd)]
        for i in range(n):
            model.add_client(locs[nd + i], delivery=demand[nd + i])
        counts: dict = {}
        for key in pseudo:
            counts[key] = counts.get(key, 0) + 1
        keys = list(counts)                                       # insertion order == table order
        for ci, di in keys:
            model.add_vehicle_type(num_available=counts[(ci, di)], capacity=classes[ci]['capacity'],
                                   start_depot=handles[di], end_depot=handles[di])
        for i in range(nd + n):
            for j in range(nd + n):
                model.add_edge(locs[i], locs[j], distance=int(M[i, j]))
        result = model.solve(MaxRuntime(limit), seed=int(params.get('seed', 42)), display=False, collect_stats=True)
        elapsed, best = 0.0, math.inf
        for dt, datum in zip(result.stats.runtimes, result.stats.data):
            elapsed += dt
            if datum.best_feas and datum.best_cost < best:
                best = datum.best_cost
                trace.append([round(elapsed, 4), best / 100])
        if not result.best.is_feasible():
            return None, None, None, trace
        trips = [[a.idx + nd for a in r if a.is_client()] for r in result.best.routes()]   # a.idx is the 0-based client index
        typed = [keys[int(r.vehicle_type())] for r in result.best.routes()]
        return trips, [ci for ci, _ in typed], [di for _, di in typed], trace
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    starts = [di for _ci, di in pseudo]
    caps = [classes[ci]['capacity'] for ci, _di in pseudo]
    manager = pywrapcp.RoutingIndexManager(nd + n, len(pseudo), starts, starts)
    routing = pywrapcp.RoutingModel(manager)
    cb = routing.RegisterTransitCallback(lambda i, j: int(M[manager.IndexToNode(i), manager.IndexToNode(j)]))
    routing.SetArcCostEvaluatorOfAllVehicles(cb)
    dem = routing.RegisterUnaryTransitCallback(lambda i: demand[manager.IndexToNode(i)])
    routing.AddDimensionWithVehicleCapacity(dem, 0, caps, True, 'Capacity')
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
        return None, None, None, trace
    trips, trip_class, trip_depot = [], [], []
    for v, (ci, di) in enumerate(pseudo):
        idx, r = routing.Start(v), []
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            if node >= nd:
                r.append(node)          # graph node numbers already offset the depots
            idx = sol.Value(routing.NextVar(idx))
        if r:
            trips.append(r)
            trip_class.append(ci)
            trip_depot.append(di)
    return trips, trip_class, trip_depot, trace


def ortools_makespan(inst, D, demand, params, K, multi):
    """OR-Tools on the real fleet: each vehicle may return to the depot to unload (optional reload
    nodes, as in the OR-Tools reload sample), and a global span cost on the time dimension
    minimises the latest finish. Returns trips, the vehicle of each trip and the trace (seconds).

    Heterogeneous fleets get per-class travel-time matrices (speed) and per-vehicle capacities;
    reload nodes unload down to zero for every class."""
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    classes = fleet_classes(inst)
    hetero = len(classes) > 1
    table = vehicle_table(inst)
    caps = [cls['capacity'] for _vi, _ci, cls, _di in table]
    n = len(inst['tasks'])
    service = [0.0] + [float(t.get('service_s', 0) or 0) for t in inst['tasks']]
    cap_ref = min(caps) if hetero else inst['vehicles']['capacity']
    reloads = max(0, math.ceil(sum(demand) / cap_ref)) if multi else 0
    orig = list(range(n + 1)) + [0] * reloads          # node -> matrix index; reload copies sit on the depot
    serv = np.array([service[o] for o in orig])
    if hetero:
        T = {ci: np.rint(10 * (D[np.ix_(orig, orig)] / cls['speed_mps'] + serv[:, None])).astype(np.int64) for ci, cls in enumerate(classes)}
        for m in T.values():
            np.fill_diagonal(m, 0)
    else:
        speed = inst['vehicles'].get('speed_mps') or 1.0
        T = {0: np.rint(10 * (D[np.ix_(orig, orig)] / speed + serv[:, None])).astype(np.int64)}
        np.fill_diagonal(T[0], 0)
    load = demand + [-max(caps)] * reloads
    manager = pywrapcp.RoutingIndexManager(n + 1 + reloads, K, 0)
    routing = pywrapcp.RoutingModel(manager)
    cbs = [routing.RegisterTransitCallback(lambda i, j, m=T[table[v][1]]: int(m[manager.IndexToNode(i), manager.IndexToNode(j)]))
           for v in range(K)]
    for v, cb in enumerate(cbs):
        routing.SetArcCostEvaluatorOfVehicle(cb, v)
    horizon = int(max(m.max() for m in T.values()) * (n + reloads + 2))
    routing.AddDimensionWithVehicleTransits(cbs, 0, horizon, True, 'Time')
    time_dim = routing.GetDimensionOrDie('Time')
    time_dim.SetGlobalSpanCostCoefficient(100)
    dem = routing.RegisterUnaryTransitCallback(lambda i: int(load[manager.IndexToNode(i)]))
    routing.AddDimensionWithVehicleCapacity(dem, max(caps), caps, True, 'Capacity')
    cap_dim = routing.GetDimensionOrDie('Capacity')
    for node in range(1, n + 1):
        cap_dim.SlackVar(manager.NodeToIndex(node)).SetValue(0)
    for node in range(n + 1, n + 1 + reloads):
        idx = manager.NodeToIndex(node)
        cap_dim.SlackVar(idx).SetRange(0, max(caps))  # unloading resets the load to zero for any class
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
    """Recompute task order, actual depot reloads, capacity, metrics and swept-radius clearance.

    Sequence/trip/service metadata are cross-checked against one another and the ordered geometry;
    none of them alone is a witness that a task was served. Invalid candidates remain diagnostics.
    Per-vehicle capacity, speed and footprint come from the route's fleet class (`vehicles.fleet`,
    synthesised as one class for legacy homogeneous instances).
    """
    from shapely.geometry import LineString, Point, Polygon
    errors, details = [], []
    tasks = {t['id']: t for t in inst['tasks']}
    rows = inst['vehicles'].get('travel') == 'rows'
    net = lanes.Network(inst) if rows else None
    area = net.travel_area() if rows else None
    boundary = Polygon(inst['boundary'])
    obstacles = [Polygon(o['polygon']) for o in inst.get('obstacles', [])]
    crop_rows = net.rows() if rows else []
    classes = fleet_classes(inst)
    depots = depot_list(inst)
    nd = len(depots)
    table = {vi: (ci, cls, di) for vi, ci, cls, di in vehicle_table(inst)}
    class_use: Counter = Counter()
    seen, vehicles, total = Counter(), set(), 0.0
    if not routes:
        errors.append('方案没有路线')
    if len(routes) > inst['vehicles']['count']:
        errors.append(f"使用 {len(routes)} 台车，超过车队规模 {inst['vehicles']['count']}")
    for index, r in enumerate(routes):
        name = str(r.get('vehicle_name') or f'车{index + 1}')
        seq = r.get('sequence') or []
        seen.update(seq)
        if any(t not in tasks for t in seq):
            errors.append(f'车辆 {name} 引用了不存在的任务')
        vehicle = r.get('vehicle', index)
        if vehicle in vehicles:
            errors.append(f'车辆编号 {vehicle} 重复')
        vehicles.add(vehicle)
        entry = table.get(vehicle)
        if entry is None:
            errors.append(f'车辆编号 {vehicle} 超出车队台数 {inst["vehicles"]["count"]}')
            cls, home = classes[0], depots[0]
        else:
            cls, home = entry[1], depots[entry[2]]
            class_use[entry[0]] += 1
        if 'fleet_class' in r and str(r['fleet_class']) != str(cls['name']):
            errors.append(f"车辆 {name} 声明的车型类别 {r['fleet_class']} 与车队定义 {cls['name']} 不一致")
        for key, expected in (('capacity', cls['capacity']), ('speed_mps', cls['speed_mps']), ('robot_radius', cls['robot_radius'])):
            if key in r and not math.isclose(float(r[key]), float(expected), rel_tol=1e-9):
                errors.append(f'车辆 {name} 声明的 {key}（{r[key]}）与类别 {cls["name"]}（{expected}）不一致')
        trips = r.get('trips')
        if not isinstance(trips, list) or not trips or any(not isinstance(t, list) or not t for t in trips):
            errors.append(f'车辆 {name} 缺少有效的分趟清单')
            trips = [seq]
        if [t for trip in trips for t in trip] != seq:
            errors.append(f'车辆 {name} 的分趟清单与访问顺序不一致')
        if any(t not in tasks for trip in trips for t in trip):
            errors.append(f'车辆 {name} 的分趟清单含未知任务')
        load = max((sum(tasks[t]['demand'] for t in trip if t in tasks) for trip in trips), default=0)
        if load > cls['capacity']:
            errors.append(f"车辆 {name}（{cls['name']}）单趟载重 {load} 超过该类容量 {cls['capacity']}")
        if inst['vehicles'].get('trips', 'multi') != 'multi' and len(trips) > 1:
            errors.append(f'车辆 {name} 跑了 {len(trips)} 趟，但当前设置为单趟')
        services = r.get('services') or []
        if [sv.get('task') for sv in services] != seq:
            errors.append(f'车辆 {name} 的作业位置清单与访问顺序不一致')
        pts = r.get('polyline') or []
        try:
            valid_points = bool(pts) and all(len(p) == 2 and all(math.isfinite(float(x)) for x in p) for p in pts)
        except (TypeError, ValueError):
            valid_points = False
        if not valid_points:
            errors.append(f'车辆 {name} 缺少有限数值的路线几何')
            continue
        radius = float(cls['robot_radius'])
        lengths = arc_lengths(pts)
        length = lengths[-1]
        turn = float(cls.get('min_turn_radius_m') or 0)
        if 'min_turn_radius_m' in r and not math.isclose(float(r['min_turn_radius_m']), turn, rel_tol=1e-9):
            errors.append(f'车辆 {name} 声明的最小转弯半径（{r["min_turn_radius_m"]}）与类别 {cls["name"]}（{turn}）不一致')
        if turn > 0:
            spacing = max((math.dist(a, b) for a, b in zip(pts, pts[1:])), default=0.0)
            if spacing > 0.15:
                errors.append(f'车辆 {name} 的曲率路线采样间距 {spacing:.3f} m 过稀，不能据以复核转弯半径')
            sampled = min_curvature_radius(pts)
            if sampled < turn * 0.99:
                errors.append(f'车辆 {name}（{cls["name"]}）路线实测最小转弯半径 {sampled:.3f} m 小于类别约束 {turn} m')
        geom = LineString(pts) if len(pts) > 1 and length > 1e-12 else Point(pts[0])
        # Distance to original polygons avoids under-inflated round buffer approximations.
        clear = boundary.covers(geom) and geom.distance(boundary.boundary) >= radius - 1e-6
        clear = clear and all(geom.distance(o) >= radius - 1e-6 for o in obstacles)
        if not clear:
            errors.append(f'车辆 {name} 的机器人占用空间穿过障碍或越出边界')
        segs = [LineString([a, b]) for a, b in zip(pts, pts[1:]) if a != b]
        off = sum(not area.covers(seg) for seg in segs) if rows else 0
        if off:
            errors.append(f'车辆 {name} 有 {off} 段路线离开行间通道和地头，斜穿了作物')
        crop_clear = all(geom.distance(row) >= radius - 1e-6 for row in crop_rows)
        if not crop_clear:
            errors.append(f'车辆 {name} 的机器人占用空间侵入作物行')
        if math.dist(pts[0], home) > 1e-6 or math.dist(pts[-1], home) > 1e-6:
            errors.append(f'车辆 {name} 未从自己的车库出发并返回')
        if 'depot' in r and nd > 1:
            di = r.get('depot')
            if not isinstance(di, int) or isinstance(di, bool) or not 0 <= di < nd:
                errors.append(f'车辆 {name} 声明的车库编号 {di} 无效')
            elif 'depot_xy' in r and (math.dist(r['depot_xy'], depots[di]) > 1e-6 or math.dist(home, depots[di]) > 1e-6):
                errors.append(f'车辆 {name} 声明的车库坐标与车队分配不一致')
        # Locate each stop in sequence, including a real depot return between trips.
        cursor, served_count = 0.0, 0
        returns = set(np.cumsum([len(trip) for trip in trips]).tolist()[:-1])
        for sv in services:
            task = tasks.get(sv.get('task'))
            if task is None:
                continue
            stop = sv.get('stop') or task['xy']
            try:
                if len(stop) != 2 or not all(math.isfinite(float(x)) for x in stop):
                    raise ValueError
                nearest = net.attach(task['xy'])[2] if rows else 0.0
                if math.dist(stop, task['xy']) > nearest + 1e-5 or (rows and nearest > net.max_reach):
                    errors.append(f"车辆 {name} 任务 {task['id']} 的作业位置不可达或偏离最近可达处")
                at = locate(pts, stop, cursor)
                pos = sv.get('position')
                if pos is not None:
                    if not isinstance(pos, int) or isinstance(pos, bool) or not 0 <= pos < len(pts):
                        raise ValueError
                    at = lengths[pos] if math.dist(pts[pos], stop) <= 1e-5 and lengths[pos] >= cursor - 1e-5 else None
                if at is None:
                    errors.append(f"车辆 {name} 未按顺序经过任务 {task['id']} 的作业位置")
                else:
                    cursor = at
            except (ValueError, TypeError, IndexError):
                errors.append(f"车辆 {name} 任务 {task['id']} 的作业位置无效")
            served_count += 1
            if served_count in returns:
                at = locate(pts, home, cursor)
                if at is None:
                    errors.append(f'车辆 {name} 分趟之间未返回车库卸载')
                else:
                    cursor = at
        duration = length / cls['speed_mps'] + sum(tasks[t]['service_s'] for t in seq if t in tasks)
        for key, expected, label in [('cost', length, '里程'), ('load', load, '载重'), ('duration_s', duration, '用时')]:
            value = r.get(key)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or not math.isclose(value, expected, rel_tol=1e-6, abs_tol=1e-5):
                errors.append(f'车辆 {name} 的{label}与独立复算不一致')
        total += length
        details.append({'vehicle': name, 'fleet_class': cls['name'], 'load': load, 'length_m': length, 'duration_s': duration,
                        'collisions': int(not clear) + int(not crop_clear), 'off_network': off})
    for ci, cls in enumerate(classes):
        if class_use[ci] > cls['count']:
            errors.append(f"车型类别 {cls['name']} 使用 {class_use[ci]} 台，超过该类台数 {cls['count']}")
    missing = sorted(set(tasks) - seen.keys())
    dup = sorted(t for t, count in seen.items() if count > 1)
    if missing:
        errors.append(f'{len(missing)} 个任务未被分配：{missing[:8]}')
    if dup:
        errors.append(f'任务重复服务：{dup[:8]}')
    return {'valid': not errors, 'errors': errors, 'computed_cost': total, 'routes': details,
            'checker': 'urp_lab.solvers.fleet.check · 顺序/分趟/指标及连续圆足迹独立复算（Shapely）',
            'source': 'panel_baseline'}


# ------------------------------------------------------------------ solve --
def assign_trips(trip_times, K):
    """LPT assignment heuristic for the latest finish; not an exact makespan optimizer."""
    load, out = [0.0] * K, [[] for _ in range(K)]
    for i in sorted(range(len(trip_times)), key=lambda i: -trip_times[i]):
        v = min(range(K), key=lambda v: (load[v], v))
        out[v].append(i)
        load[v] += trip_times[i]
    return out


def solve(scenario, inst, algorithm_id, params):
    t0 = time.perf_counter()
    graph = travel_graph(inst)
    D = graph.D
    n = len(inst['tasks'])
    depots = depot_list(inst)
    nd = len(depots)
    unreachable = [inst['tasks'][i - 1]['label'] for i in range(1, n + 1)
                   if not any(np.isfinite(D[d0, i]) for d0 in range(nd))]
    if unreachable:
        raise ValueError(f'有任务点与所有车库不连通（被障碍{"或作物行" if graph.travel == "rows" else ""}隔断）：{unreachable[:6]}')
    demand = [0] * nd + [t['demand'] for t in inst['tasks']]
    K = inst['vehicles']['count']
    classes = fleet_classes(inst)
    hetero = len(classes) > 1
    multi_depot = nd > 1
    class_of = [ci for vi, ci, _cls, _di in vehicle_table(inst)]
    multi = inst['vehicles'].get('trips', 'multi') == 'multi'
    fleet_cap = sum(c['count'] * c['capacity'] for c in classes)
    if not multi and sum(demand) > fleet_cap:
        return [], None, {'fleet_capacity': fleet_cap, 'total_demand': sum(demand)}, \
            {'reason': f'总需求 {sum(demand)} 超过车队单趟总容量 {fleet_cap}'
                       + ('（按各类别台数 × 容量合计）' if hetero else f'（{K} × {classes[0]["capacity"]}）')
                       + '；可允许多趟往返或增加车辆/容量'}, 'infeasible', []
    if hetero and algorithm_id in ('panel.sweep', 'panel.cluster_first', 'panel.savings_fleet'):
        raise ValueError('构造基线（sweep / cluster_first / savings）只支持同构车队；异构车队请用 pyvrp.fleet 或 ortools.fleet')
    if multi_depot and (algorithm_id.startswith('panel.')
                        or (algorithm_id == 'ortools.fleet' and inst.get('objective') == 'makespan')):
        raise ValueError('多车库当前支持 pyvrp.fleet / ortools.fleet 的总里程目标；构造基线与 makespan 的多车库建模尚未实现')
    deadline = time.perf_counter() + float(params.get('time_limit_s', 3))
    route_cap = n if multi else K
    trace, owner, trip_class, trip_depot = [], None, None, None
    if algorithm_id == 'pyvrp.fleet':
        trips, trip_class, trip_depot, trace = metaheuristic('pyvrp', inst, D, demand, params, route_cap)
    elif algorithm_id == 'ortools.fleet' and inst.get('objective') == 'makespan':
        trips, owner, trace = ortools_makespan(inst, D, demand, params, K, multi)
        trip_class = [class_of[v] for v in owner] if owner is not None else None
    elif algorithm_id == 'ortools.fleet':
        trips, trip_class, trip_depot, trace = metaheuristic('ortools', inst, D, demand, params, route_cap)
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
    if trip_class is None:
        trip_class = [0] * len(trips)          # constructive baselines run on homogeneous fleets only
    if trip_depot is None:
        trip_depot = [0] * len(trips)          # makespan keeps the (single) home depot
    trip_len = [float(sum(D[a, b] for a, b in zip([trip_depot[i]] + r + [trip_depot[i]], r + [trip_depot[i]])))
                for i, r in enumerate(trips)]
    trip_time = [L / classes[ci]['speed_mps'] + sum(inst['tasks'][i - nd].get('service_s', 0) for i in r)
                 for L, r, ci in zip(trip_len, trips, trip_class)]
    if owner is not None:
        plan = [[i for i, o in enumerate(owner) if o == v] for v in range(K)]
    elif hetero or multi_depot:
        plan = [[] for _ in range(K)]
        depot_of = [di for _vi, _ci, _cls, di in vehicle_table(inst)]
        keys = list(dict.fromkeys(zip(class_of, depot_of)))
        vehicles_of = {key: [vi for vi in range(K) if (class_of[vi], depot_of[vi]) == key] for key in keys}
        if multi:
            for key in keys:
                mine = [i for i, k in enumerate(zip(trip_class, trip_depot)) if k == key]
                buckets = assign_trips([trip_time[i] for i in mine], max(1, len(vehicles_of[key])))
                for vi, bucket in zip(vehicles_of[key] + [None] * len(buckets), buckets):
                    if vi is not None:
                        plan[vi] = [mine[i] for i in bucket]
        else:
            free = {key: list(reversed(vehicles_of[key])) for key in keys}
            for i, key in enumerate(zip(trip_class, trip_depot)):
                if not free.get(key):
                    break                        # more trips of this class/depot than vehicles: the checker reports it
                plan[free[key].pop()].append(i)
    elif multi or len(trips) <= K:
        plan = assign_trips(trip_time, K) if multi else [[i] for i in range(len(trips))]
    else:
        plan = [[i] for i in range(len(trips))]  # more single trips than vehicles: the checker reports it
    names = inst['vehicles'].get('names') or []
    table = {vi: cls for vi, _ci, cls, _di in vehicle_table(inst)}
    routes = []
    for vi, mine in enumerate(plan):
        if not mine:
            continue
        cls = table.get(vi) or classes[0]
        home = [di for _vi, _ci, _cls, di in vehicle_table(inst)][vi] if multi_depot else 0
        stops = [home] + [s for i in mine for s in trips[i] + [home]]
        waypoints, service_waypoints = [], []
        for a, b in zip(stops, stops[1:]):
            seg = graph.path(a, b)
            waypoints += seg if not waypoints else seg[1:]
            if b != home:
                service_waypoints.append(len(waypoints) - 1)
        turn = float(cls.get('min_turn_radius_m') or 0)
        if turn > 0:
            pts, marks = dubins_realize(waypoints, turn)
            service_positions = [marks[wi] for wi in service_waypoints]
        else:
            pts, service_positions = waypoints, service_waypoints
        length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        service_total = sum(inst['tasks'][s - nd]['service_s'] for i in mine for s in trips[i])
        route = {'vehicle': vi, 'vehicle_name': names[vi] if vi < len(names) else f'车{vi + 1}', 'color': COLORS[vi % len(COLORS)],
                 'nodes': None, 'sequence': [inst['tasks'][s - nd]['id'] for i in mine for s in trips[i]],
                 'trips': [[inst['tasks'][s - nd]['id'] for s in trips[i]] for i in mine],
                 'services': [{'task': inst['tasks'][s - nd]['id'], 'position': pos, 'stop': list(graph.points[s])}
                              for s, pos in zip([s for i in mine for s in trips[i]], service_positions)],
                 'polyline': pts, 'cost': length,
                 'load': max(sum(demand[s] for s in trips[i]) for i in mine),
                 'duration_s': length / cls['speed_mps'] + service_total}
        if hetero:
            route.update(fleet_class=cls['name'], capacity=cls['capacity'],
                         speed_mps=cls['speed_mps'], robot_radius=cls['robot_radius'])
        if turn > 0:
            route.update(min_turn_radius_m=turn, curvature_radius_m=round(min_curvature_radius(pts), 4))
        if multi_depot:
            route.update(depot=home, depot_xy=[float(depots[home][0]), float(depots[home][1])])
        routes.append(route)
    chk = check(inst, routes)
    lengths = [r['cost'] for r in routes]
    euclid = sum(float(graph.euclid[a, b]) for i, r in enumerate(trips)
                 for a, b in zip([trip_depot[i]] + r, r + [trip_depot[i]]))
    trip_capacity = sum(classes[ci]['capacity'] for ci in trip_class)
    metrics = {'total_distance_m': sum(lengths), 'makespan_s': max(r['duration_s'] for r in routes),
               'longest_route_m': max(lengths), 'vehicles_used': len(routes), 'fleet_size': K, 'trips': len(trips),
               'balance_cv': float(np.std(lengths) / np.mean(lengths)) if len(lengths) > 1 and np.mean(lengths) else 0.0,
               'capacity_utilization': sum(demand) / trip_capacity if trip_capacity else 1.0,
               'detour_ratio': sum(lengths) / euclid if euclid else 1.0,
               'graph_nodes': len(graph.nodes), 'graph_build_s': graph.build_s, 'objective_mode': inst.get('objective', 'total_distance'),
               'travel': graph.travel,
               'curvature_constrained_vehicles': sum(1 for r in routes if r.get('min_turn_radius_m')),
               'per_vehicle': [{'vehicle': r['vehicle_name'],
                                **({'fleet_class': r['fleet_class']} if hetero else {}),
                                **({'min_turn_radius_m': r['min_turn_radius_m']} if r.get('min_turn_radius_m') else {}),
                                'color': r['color'], 'tasks': len(r['sequence']), 'trips': len(r['trips']),
                                'load': r['load'], 'length_m': r['cost'], 'duration_s': r['duration_s']} for r in routes]}
    if graph.travel == 'rows':
        metrics.update(lanes=graph.info['lanes'], service_offset_mean_m=graph.info['service_offset_mean_m'],
                       service_offset_max_m=graph.info['service_offset_max_m'])
    model = ('沿作物行间通道、地头与机耕路的通行图最短路：作物行不可穿越，任务使用邻近通道停车访问代理；未验证作业具可达或农业作业质量'
             if graph.travel == 'rows' else '机器人半径膨胀障碍上的可视图最短路（候选图上的最短路；不保证连续空间全局最短）')
    raw = {'trips': trips, 'vehicle_plan': plan, 'distance_model': model, 'travel_network': graph.info or None,
           'search_scale': 'PyVRP / OR-Tools 用厘米取整距离搜索，结果按米复算', 'planning_s': time.perf_counter() - t0,
           'trip_assignment': ('OR-Tools 直接为各车安排往返（车库卸载点），时间维度跨度代价最小化最晚完成'
                               if algorithm_id == 'ortools.fleet' and inst.get('objective') == 'makespan'
                               else '多趟：先求各趟路线，再按最长处理时间优先分配到各车' if multi else '单趟：每车一条路线')}
    raw['model_contract'] = {
        'schema': 'urp.fleet-model/1', 'frame': 'local planar metres',
        'geometry': {'footprint': 'circumscribed circle', 'radius_m': inst['robot_radius'],
                     'path': ('piecewise Dubins shortest paths between carried-heading waypoints, curvature bounded by each '
                              "class's min_turn_radius_m (Dubins 1957; OMPL DubinsStateSpace); forward motion only, no "
                              'Reeds–Shepp reversing; assignment optimised on straight-line graph distances, realised '
                              'curved lengths are reported as executed metrics'
                              if any(float(c.get('min_turn_radius_m') or 0) > 0 for c in classes)
                              else 'piecewise linear shortest paths on constructed graph; no curvature optimization'),
                     'curvature_bounded': any(float(c.get('min_turn_radius_m') or 0) > 0 for c in classes)},
        'fleet': {'type': 'heterogeneous' if hetero else 'homogeneous',
                  **({'depots': [{'index': i, 'xy': [float(d[0]), float(d[1])]} for i, d in enumerate(depots)],
                      'depot_assignment': 'vehicles round-robin over depots in table order; start, reload and return at the home depot',
                      'unsupported': 'makespan objective and constructive baselines reject multi-depot instances'}
                     if multi_depot else {}),
                  **({'classes': [{'name': c['name'], 'count': c['count'], 'capacity': c['capacity'],
                                   'speed_mps': c['speed_mps'], 'robot_radius': c['robot_radius'], 'payload': c['payload']}
                                  for c in classes],
                      'note': '通行图与障碍膨胀按车队最大足迹半径；独立检查器按各车自身足迹复算净空'}
                     if hetero else {}),
                  'capacity_unit': 'abstract demand units, not kg',
                  'reload': 'instantaneous at depot between trips; no handling duration or payload dynamics'},
        'task': {'success': 'visit assigned access location and dwell; no tool, crop interaction or work-quality model',
                 'access': 'nearest lane/headland proxy' if graph.travel == 'rows' else 'task coordinate',
                 'physical_reach_verified': False, 'max_geometric_offset_m': max(getattr(graph, 'offsets', [0]) or [0])},
        'time': {'model': 'distance/speed + requested service time', 'acceleration': False,
                 'turns': False, 'parking': False, 'traffic_conflicts': False,
                 'scope': 'constant-speed planning proxy, not physically predicted completion time'},
        'optimization': {'reported_objective': inst.get('objective', 'total_distance'),
                         'search': 'weighted distance and route-span surrogate' if algorithm_id == 'ortools.fleet' and inst.get('objective') == 'makespan'
                         else 'distance routing then trip allocation',
                         'trip_allocation': 'OR-Tools assignment' if owner is not None else 'LPT heuristic' if multi else 'one trip per vehicle',
                         'optimality_proved': False}}
    if not chk['valid']:
        raw['rejected_routes'] = routes
        raw['reason'] = '候选方案未通过独立检查，不能作为可行方案执行'
        return [], chk, metrics, raw, 'no_solution', trace
    return routes, chk, metrics, raw, 'feasible', trace


def objective_value(inst, metrics):
    return metrics['makespan_s'] if inst.get('objective') == 'makespan' else metrics['total_distance_m']
