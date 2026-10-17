"""PyVRP / OR-Tools fleet engines: distance-mode metaheuristic and the makespan model.

Split out of ``solvers/fleet.py`` (2026-10-17); behaviour unchanged.
"""
from __future__ import annotations

import math
import time

import numpy as np

from .fleet_common import depot_list, fleet_classes, vehicle_table


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
    home_of = [di for _vi, _ci, _cls, di in table]     # round-robin home depot per vehicle (MDVRP starts/ends)
    depots = depot_list(inst)
    nd = len(depots)
    n = len(inst['tasks'])
    service = [0.0] * nd + [float(t.get('service_s', 0) or 0) for t in inst['tasks']]
    nu = len(inst.get('unload_points') or [])
    cap_ref = min(caps) if hetero else inst['vehicles']['capacity']
    per_depot = min(n, max(0, math.ceil(sum(demand) / cap_ref))) if multi else 0
    reloads = (nd + nu) * per_depot
    # Only tasks are mandatory. Supply coordinates enter through optional reload copies,
    # never as mandatory zero-demand clients. orig maps model indices to graph indices.
    task_end = nd + n
    orig = list(range(task_end)) + [d for d in range(nd) for _ in range(per_depot)] \
        + [nd + n + u for u in range(nu) for _ in range(per_depot)]
    serv = np.array([service[o] if o < nd + n else 0.0 for o in orig])
    if hetero:
        T = {ci: np.rint(10 * (D[np.ix_(orig, orig)] / cls['speed_mps'] + serv[:, None])).astype(np.int64) for ci, cls in enumerate(classes)}
        for m in T.values():
            np.fill_diagonal(m, 0)
    else:
        speed = inst['vehicles'].get('speed_mps') or 1.0
        T = {0: np.rint(10 * (D[np.ix_(orig, orig)] / speed + serv[:, None])).astype(np.int64)}
        np.fill_diagonal(T[0], 0)
    load = [0] * nd + list(demand[nd:]) + [-max(caps)] * reloads
    manager = pywrapcp.RoutingIndexManager(task_end + reloads, K, home_of, home_of)
    routing = pywrapcp.RoutingModel(manager)
    cbs = [routing.RegisterTransitCallback(lambda i, j, m=T[table[v][1]]: int(m[manager.IndexToNode(i), manager.IndexToNode(j)]))
           for v in range(K)]
    for v, cb in enumerate(cbs):
        routing.SetArcCostEvaluatorOfVehicle(cb, v)
    horizon = int(max(m.max() for m in T.values()) * (task_end + reloads + 2))
    routing.AddDimensionWithVehicleTransits(cbs, 0, horizon, True, 'Time')
    time_dim = routing.GetDimensionOrDie('Time')
    time_dim.SetGlobalSpanCostCoefficient(100)
    dem = routing.RegisterUnaryTransitCallback(lambda i: int(load[manager.IndexToNode(i)]))
    routing.AddDimensionWithVehicleCapacity(dem, max(caps), caps, True, 'Capacity')
    cap_dim = routing.GetDimensionOrDie('Capacity')
    for node in range(nd, nd + n):
        cap_dim.SlackVar(manager.NodeToIndex(node)).SetValue(0)
    for node in range(task_end, task_end + reloads):
        idx = manager.NodeToIndex(node)
        cap_dim.SlackVar(idx).SetRange(0, max(caps))  # unloading resets the load to zero for any class
        routing.AddDisjunction([idx], 0)               # reloads are optional and free
        routing.solver().Add(cap_dim.CumulVar(idx) >= routing.ActiveVar(idx))
        # A reload separates nonempty trips. Inactive copies may self-loop; active
        # copies must lead to a task, excluding empty reload chains and terminal detours.
        routing.solver().Add(routing.NextVar(idx).Member(
            [idx] + [manager.NodeToIndex(t) for t in range(nd, nd + n)]))
        source = orig[node]
        if source < nd and nd > 1:                     # MDVRP: a depot's reloads serve only its home vehicles
            routing.solver().Add(routing.VehicleVar(idx).Member([-1] + [v for v in range(K) if home_of[v] == source]))
        # unload-point reload copies are open to every vehicle (mid-route supply, not home-bound)
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
    # PATH_CHEAPEST_ARC cannot complete a first solution when the per-depot reload membership
    # constraints bind (multi-depot with required reloads); insertion heuristics respect them.
    p.first_solution_strategy = (routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION if nd > 1
                                 else routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    p.time_limit.FromMilliseconds(max(1, round(float(params.get('time_limit_s', 3)) * 1000)))
    sol = routing.SolveWithParameters(p)
    if sol is None:
        return None, None, None, trace
    trips, owner, reload_at = [], [], []
    for v in range(K):
        idx, cur = routing.Start(v), []
        while True:
            idx = sol.Value(routing.NextVar(idx))
            node = manager.IndexToNode(idx)
            if routing.IsEnd(idx) or node >= nd + n:
                if cur:
                    trips.append(cur)
                    owner.append(v)
                    reload_at.append(orig[node])  # this trip ends at this reload or home
                cur = []
                if routing.IsEnd(idx):
                    break
            else:
                cur.append(node)
    return trips, owner, reload_at, trace


# ------------------------------------------------------------------ check --
