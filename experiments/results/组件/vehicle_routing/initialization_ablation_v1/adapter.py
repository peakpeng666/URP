"""Original adapter for official PyVRP 0.14.0; no vendor source copied."""
import math
import time
from local_search_v2.solvers import solve as trusted_solve

PYVRP_METHODS = {"pyvrp_ils_random": 1_000_000, "pyvrp_ils_savings_warm": 1_000_000}
_backend = None


def prepare(algorithm):
    """Dependency import is accounted in complete-process CPU, before solver CPU."""
    global _backend
    if algorithm in PYVRP_METHODS:
        import importlib.metadata
        if importlib.metadata.version("pyvrp") != "0.14.0":
            raise RuntimeError("requires exact pyvrp==0.14.0")
        import pyvrp
        from pyvrp.PenaltyManager import PenaltyParams
        _backend = (pyvrp, PenaltyParams)


def matrices(instance, scale):
    distances = [[math.hypot(a[0] - b[0], a[1] - b[1]) for b in instance.coordinates]
                 for a in instance.coordinates]
    integer = [[int(math.floor(x * scale + 0.5)) for x in row] for row in distances]
    # Avoid the library's missing-edge sentinel and conservatively stay in int64
    # for a whole legal solution, costs and scaled penalty accumulation.
    n = instance.n_customers
    if any(x >= 17_592_186_044_416 for row in integer for x in row):
        raise ValueError("scaled edge reaches PyVRP missing-edge sentinel")
    worst_objective = max((x for row in integer for x in row), default=0) * max(1, 2 * n)
    worst_load_penalty = 100_000 * scale * sum(instance.demands)
    if worst_objective + worst_load_penalty >= 2 ** 60:
        raise ValueError("scaled objective plus load penalties unsafe for experiment integer guard")
    return distances, integer


def build(instance, scale):
    if _backend is None:
        raise RuntimeError("call prepare before solver budget begins")
    pyvrp, _ = _backend
    distances, integer = matrices(instance, scale)
    model = pyvrp.Model()
    locations = [model.add_location(*xy, name=str(i)) for i, xy in enumerate(instance.coordinates)]
    depot = model.add_depot(locations[0])
    for node in range(1, instance.n_customers + 1):
        model.add_client(locations[node], delivery=instance.demands[node], required=True, name=str(node))
    model.add_vehicle_type(num_available=max(1, instance.n_customers), capacity=instance.capacity,
                           start_depot=depot, end_depot=depot, fixed_cost=0,
                           unit_distance_cost=1, unit_duration_cost=0, max_reloads=0)
    for i, a in enumerate(locations):
        for j, b in enumerate(locations):
            model.add_edge(a, b, distance=integer[i][j], duration=0)
    return model, distances, integer


class CPUIterationStop:
    def __init__(self, budget, config):
        self.budget, self.config = budget, config
        self.iterations = 0
        self.reason = None

    def __call__(self, best_cost):
        if time.process_time() - self.budget.start_cpu >= self.budget.cpu_seconds - self.config["pyvrp_cpu_return_margin_seconds"]:
            self.reason = "cpu_return_margin"
            return True
        if time.perf_counter() - self.budget.start_wall >= self.budget.wall_seconds - 0.05:
            self.reason = "wall_return_margin"
            return True
        if self.iterations >= self.config["pyvrp_iterations"]:
            self.reason = "iteration_limit"
            return True
        self.iterations += 1
        return False


def solve(instance, algorithm, seed, budget, config):
    if algorithm not in PYVRP_METHODS:
        return trusted_solve(instance, algorithm, seed, budget, config)
    scale = PYVRP_METHODS[algorithm]
    if instance.n_customers == 0:
        return {"routes": [], "reported_cost": 0.0, "search": {"termination": "empty_instance_no_backend_solve", "integer_scale": scale}}
    warm_output = None
    warm_construct_cpu = warm_validation_cpu = 0.0
    if algorithm == "pyvrp_ils_savings_warm":
        from urp_cvrp.baselines import savings
        from urp_cvrp.checker import check_solution
        start = time.process_time()
        warm_output = savings(instance, seed, budget)
        warm_construct_cpu = time.process_time() - start
        start = time.process_time()
        warm_check = check_solution(instance, warm_output)
        warm_validation_cpu = time.process_time() - start
        if not warm_check.accepted:
            raise ValueError("independent warm-start checker rejected savings output")
    model, distances, integer = build(instance, scale)
    pyvrp, PenaltyParams = _backend
    data = model.data()
    initial_solution = None
    initial_integer_cost = None
    if warm_output is not None:
        # Public v0.14 API: list-of-lists use zero-based CLIENT indices.
        warm_clients = [[node - 1 for node in r[1:-1]] for r in warm_output["routes"]]
        initial_solution = pyvrp.Solution(data, warm_clients)
        if not initial_solution.is_feasible():
            raise ValueError("PyVRP rejects independently feasible warm-start conversion")
        initial_integer_cost = sum(integer[a][b] for r in warm_output["routes"] for a,b in zip(r,r[1:]))
        if initial_solution.distance_cost() != initial_integer_cost:
            raise ValueError("warm-start integer objective mismatch")
    # Penalty limits have cost units: rescale BOTH limits along with distances,
    # otherwise integer precision would silently change normalized penalties.
    params = _backend[0].SolveParams(penalty=PenaltyParams(min_penalty=0.1 * scale, max_penalty=100_000 * scale))
    stop = CPUIterationStop(budget, config)
    result = pyvrp.solve(data, stop, seed=seed, collect_stats=False, display=False, params=params, initial_solution=initial_solution)
    routes = []
    for route in result.best.routes():
        nodes = []
        for activity in route:
            if activity.is_depot():
                if activity.idx != 0:
                    raise ValueError("unexpected depot in PyVRP output")
                nodes.append(0)
            elif activity.is_client():
                nodes.append(activity.idx + 1)  # v0.14 client indices exclude depot
            else:
                raise ValueError("unsupported pickup/delivery activity")
        routes.append(nodes)
    edges = [(a, b) for route in routes for a, b in zip(route, route[1:])]
    integer_cost = sum(integer[a][b] for a, b in edges)
    unrounded = math.fsum(distances[a][b] for a, b in edges)
    max_edge_error = max((abs(distances[i][j] - integer[i][j] / scale)
                          for i in range(len(distances)) for j in range(len(distances))), default=0)
    library_cost = int(result.best.distance_cost() + result.best.fixed_vehicle_cost() + result.best.duration_cost())
    metadata = {
        "family": "PyVRP_0.14_iterated_local_search", "version": "0.14.0",
        "initialization": "savings_warm_start" if warm_output is not None else "default_random",
        "warm_start_constructor_cpu_seconds": warm_construct_cpu,
        "warm_start_independent_validation_cpu_seconds": warm_validation_cpu,
        "warm_start_original_cost": warm_output["reported_cost"] if warm_output is not None else None,
        "warm_start_integer_cost": initial_integer_cost,
        "warm_start_routes": warm_output["routes"] if warm_output is not None else None,
        "warm_start_independently_validated": warm_output is not None,
        "warm_start_library_feasible": initial_solution.is_feasible() if initial_solution is not None else None,
        "incumbent_not_worse_than_initial_integer_cost": integer_cost <= initial_integer_cost if initial_integer_cost is not None else None,
        "termination": stop.reason, "iterations": result.num_iterations,
        "stop_admitted_iterations": stop.iterations, "integer_scale": scale,
        "optimized_objective": "sum_round_half_up_scaled_euclidean_distance",
        "scored_objective": "original_sum_unrounded_euclidean_distance",
        "integer_cost": integer_cost, "library_integer_cost": library_cost,
        "integer_cost_matches": integer_cost == library_cost,
        "quantized_cost_divided_by_scale": integer_cost / scale,
        "unrounded_minus_quantized_cost": unrounded - integer_cost / scale,
        "route_edge_count": len(edges), "max_edge_rounding_error": max_edge_error,
        "route_rounding_bound": len(edges) * max_edge_error,
        "theoretical_rounding_bound_plus_float_slack": len(edges) * (0.5 / scale + 1e-12),
        "fleet_num_available": instance.n_customers, "vehicle_fixed_cost": 0,
        "penalty_min": 0.1 * scale, "penalty_max": 100_000 * scale,
        "pyvrp_feasible_flag": result.is_feasible(),
        "pyvrp_runtime_seconds": result.runtime,
    }
    if initial_integer_cost is not None and integer_cost > initial_integer_cost:
        raise ValueError("PyVRP incumbent lost the feasible warm-start bound")
    if integer_cost != library_cost:
        raise ValueError("PyVRP integer objective differs from independently summed edges")
    if abs(unrounded - integer_cost / scale) > len(edges) * max_edge_error + 1e-9:
        raise ValueError("quantization error exceeds measured bound")
    return {"routes": routes, "reported_cost": unrounded, "search": metadata}
