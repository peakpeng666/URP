"""Small executable exercises for the LLM algorithm-design study guide.

This is teaching code, not an EoH/FunSearch implementation or an execution
sandbox. It never executes source returned by a language model.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import permutations
from math import isfinite
from typing import Callable, Sequence
import numpy as np

@dataclass(frozen=True)
class GAResult:
    best_genome: tuple[float, ...]
    best_loss: float
    history: tuple[float, ...]
    evaluations: int


def minimize_ga(loss: Callable[[np.ndarray], float], *, dim: int = 4,
                population: int = 24, generations: int = 30,
                mutation_rate: float = 0.2, sigma: float = 0.2,
                seed: int = 0) -> GAResult:
    """Minimizing real-valued GA with a single elite and finite-score checks.

    We intentionally re-evaluate the whole next generation (including its
    elite). Therefore the reported evaluation count is exact, not inferred
    from the number of offspring. `loss` must be deterministic and trusted.
    """
    if dim < 1 or population < 2 or generations < 0:
        raise ValueError('dim >= 1, population >= 2, generations >= 0 required')
    if not 0 <= mutation_rate <= 1 or not isfinite(sigma) or sigma < 0:
        raise ValueError('invalid mutation settings')
    rng = np.random.default_rng(seed)
    genomes = rng.normal(size=(population, dim))
    evaluations = 0

    def evaluate(xs: np.ndarray) -> np.ndarray:
        nonlocal evaluations
        scores = np.asarray([float(loss(x.copy())) for x in xs], dtype=float)
        evaluations += len(xs)
        if not np.isfinite(scores).all():
            raise ValueError('loss returned NaN or infinity')
        return scores

    scores = evaluate(genomes)
    history = [float(scores.min())]
    for _ in range(generations):
        children = [genomes[int(scores.argmin())].copy()]
        while len(children) < population:
            a = rng.choice(population, size=2, replace=False)
            b = rng.choice(population, size=2, replace=False)
            p = genomes[a[int(scores[a].argmin())]]
            q = genomes[b[int(scores[b].argmin())]]
            # Uniform crossover also works when dim == 1.
            child = np.where(rng.random(dim) < 0.5, p, q).copy()
            mask = rng.random(dim) < mutation_rate
            child[mask] += rng.normal(0, sigma, size=int(mask.sum()))
            children.append(child)
        genomes = np.asarray(children)
        scores = evaluate(genomes)       # Score BEFORE selection/logging.
        history.append(float(scores.min()))
    k = int(scores.argmin())
    return GAResult(tuple(map(float, genomes[k])), float(scores[k]),
                    tuple(history), evaluations)


def validate_distance(d: np.ndarray) -> np.ndarray:
    d = np.asarray(d, dtype=float)
    if d.ndim != 2 or d.shape[0] != d.shape[1] or len(d) < 2:
        raise ValueError('distance matrix must be square with n >= 2')
    if not np.isfinite(d).all() or (d < 0).any():
        raise ValueError('finite nonnegative distances required')
    if not np.allclose(np.diag(d), 0, rtol=0, atol=1e-12):
        raise ValueError('diagonal must be zero')
    return d


def tour_cost(tour: Sequence[int], d: np.ndarray) -> float:
    d = validate_distance(d)
    n = len(d)
    if len(tour) != n or any(type(i) is not int for i in tour):
        raise ValueError('tour must contain n Python integer node IDs')
    if set(tour) != set(range(n)):
        raise ValueError('each node must appear exactly once')
    return float(sum(d[tour[i], tour[(i + 1) % n]] for i in range(n)))


def exact_tsp(d: np.ndarray) -> tuple[list[int], float]:
    d = validate_distance(d)
    if len(d) > 9:
        raise ValueError('exhaustive teaching oracle is limited to n <= 9')
    best = min(([0, *p] for p in permutations(range(1, len(d)))),
               key=lambda t: tour_cost(t, d))
    return best, tour_cost(best, d)


def greedy_tsp(d: np.ndarray) -> tuple[list[int], float]:
    d = validate_distance(d)
    tour, remaining = [0], set(range(1, len(d)))
    while remaining:
        nxt = min(remaining, key=lambda j: (d[tour[-1], j], j))
        tour.append(nxt)
        remaining.remove(nxt)
    return tour, tour_cost(tour, d)


def pack(items: Sequence[float], capacity: float = 1.0,
         rule: str = 'best_fit') -> tuple[list[int], list[float]]:
    if not isfinite(capacity) or capacity <= 0:
        raise ValueError('positive finite capacity required')
    if rule not in {'first_fit', 'best_fit', 'next_fit'}:
        raise ValueError('unknown packing rule')
    loads: list[float] = []
    assignment: list[int] = []
    for x in items:
        if not isfinite(x) or x <= 0 or x > capacity:
            raise ValueError('each item must be finite and in (0, capacity]')
        feasible = [j for j, load in enumerate(loads) if load + x <= capacity + 1e-12]
        if rule == 'next_fit':
            feasible = [len(loads) - 1] if loads and len(loads)-1 in feasible else []
        if feasible:
            j = min(feasible, key=lambda j: (capacity-loads[j]-x, j)) if rule == 'best_fit' else feasible[0]
            loads[j] += x
        else:
            j = len(loads)
            loads.append(float(x))
        assignment.append(j)
    return assignment, loads


def validate_packing(items: Sequence[float], assignment: Sequence[int],
                     capacity: float = 1.0) -> int:
    if not isfinite(capacity) or capacity <= 0 or len(items) != len(assignment):
        raise ValueError('invalid capacity or assignment length')
    loads: dict[int, float] = {}
    for x, j in zip(items, assignment):
        if type(j) is not int or j < 0 or not isfinite(x) or not 0 < x <= capacity:
            raise ValueError('invalid item or bin ID')
        loads[j] = loads.get(j, 0.0) + x
    if any(load > capacity + 1e-12 for load in loads.values()):
        raise ValueError('overloaded bin')
    return len(loads)


def reproduce_unscored_population_bug() -> str:
    # Isolated reproduction of the guide's operation order; NOT the full file.
    class Individual:
        def __init__(self) -> None:
            self.fitness = None
    try:
        max([Individual(), Individual()], key=lambda x: x.fitness)
    except TypeError as exc:
        return type(exc).__name__
    raise AssertionError('expected TypeError was not observed')


if __name__ == '__main__':
    import json
    xy = np.array([[0,0], [1,0], [1,1], [0,1]], dtype=float)
    d = np.linalg.norm(xy[:, None] - xy[None, :], axis=-1)
    ga = minimize_ga(lambda x: float(x @ x), seed=19)
    print(json.dumps({
        'bug_reproduction': reproduce_unscored_population_bug(),
        'ga_best_loss': ga.best_loss, 'ga_evaluations': ga.evaluations,
        'ga_history_nonincreasing': all(a >= b for a,b in zip(ga.history,ga.history[1:])),
        'square_optimum': exact_tsp(d)[1],
        'square_crossing_cost': tour_cost([0,2,1,3], d),
        'packing_best_fit': len(pack([.6,.6,.4,.4], rule='best_fit')[1]),
        'packing_next_fit': len(pack([.6,.6,.4,.4], rule='next_fit')[1]),
    }, indent=2))
