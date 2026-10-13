"""Exhaustive oracle for at most seven customers, for tests only.

Enumerates every customer permutation and every separator pattern. This
includes every ordered collection of depot-to-depot tours, with duplicates.
Only capacity-feasible partitions are scored. No pruning heuristic or solver
library is involved. Exponential complexity is intentional and size-bounded.
"""

import itertools
import math


def exhaustive_optimum(instance):
    n = instance.n_customers
    if n > 7:
        raise ValueError("exhaustive oracle is limited to seven customers")
    if n == 0:
        return {"routes": [], "reported_cost": 0.0, "partitions_examined": 1}
    best_cost, best_routes, examined = math.inf, None, 0
    for ordering in itertools.permutations(range(1, n + 1)):
        for mask in range(1 << (n - 1)):
            examined += 1
            routes, start = [], 0
            for cut in range(n - 1):
                if mask & (1 << cut):
                    routes.append(ordering[start:cut + 1])
                    start = cut + 1
            routes.append(ordering[start:])
            if any(sum(instance.demands[j] for j in route) > instance.capacity for route in routes):
                continue
            edges = []
            for route in routes:
                full = (0,) + route + (0,)
                for a, b in zip(full, full[1:]):
                    p, q = instance.coordinates[a], instance.coordinates[b]
                    edges.append(math.dist(p, q))
            value = math.fsum(edges)
            if value < best_cost:
                best_cost = value
                best_routes = [[0] + list(route) + [0] for route in routes]
    return {"routes": best_routes, "reported_cost": best_cost, "partitions_examined": examined}
