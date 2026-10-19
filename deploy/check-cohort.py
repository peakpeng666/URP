#!/usr/bin/env python3
"""Bounded synthetic AILS/SISR deployment smoke; not a formal cohort experiment."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def check_incumbent(problem: dict, incumbent: dict | None) -> bool:
    """Recompute coverage, capacity and EUC_2D cost outside either native solver."""
    if not isinstance(incumbent, dict):
        return False
    routes = incumbent.get('routes')
    if not isinstance(routes, list) or not routes or len(routes) > problem['K']:
        return False
    seen, cost = [], 0
    for route in routes:
        if not isinstance(route, list) or len(route) < 3 or route[0] != 0 or route[-1] != 0:
            return False
        if any(type(node) is not int or not 1 <= node < len(problem['demands']) for node in route[1:-1]):
            return False
        seen.extend(route[1:-1])
        if sum(problem['demands'][node] for node in route[1:-1]) > problem['capacity']:
            return False
        cost += sum(math.floor(math.dist(problem['coordinates'][a], problem['coordinates'][b]) + .5)
                    for a, b in zip(route, route[1:]))
    return sorted(seen) == list(range(1, len(problem['demands']))) and cost == incumbent.get('cost')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='New absolute directory, never overwritten')
    args = parser.parse_args()
    if not args.output.is_absolute() or args.output.exists():
        parser.error('--output must be a new absolute directory')
    args.output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(ROOT / 'cohort_b'))
    from run_vendor import run
    # Synthetic points only. No CVRPLIB inputs, BKS, frozen schedules or records.
    problem = dict(coordinates=[[0, 0]] + [[i * 37 % 101, i * 53 % 97] for i in range(1, 21)],
                   demands=[0] + [1] * 20, capacity=5, K=20, seed=0)
    summary = dict(schema='urp.deployment-cohort-smoke/1',
                   scope='synthetic load/metric/feasibility check, not research reproduction',
                   created_utc=datetime.now(timezone.utc).isoformat(),
                   problem=problem, budget_seconds=1, results={})
    for algorithm in ('ails', 'sisr'):
        try:
            result = run(algorithm, problem, budget=1)
            valid = check_incumbent(problem, result.get('incumbent'))
            metric = any(e.get('event') == 'metric_verified' and e.get('edges') == 441
                         for e in result.get('events', []))
            passed = (valid and metric and result.get('status') == 'VALID'
                      and result.get('termination_status') in ('normal_exit', 'deadline_kill')
                      and not result.get('invalid_outputs'))
            result.update(independent_incumbent_valid=valid, smoke_passed=passed)
        except Exception as exc:
            result = dict(smoke_passed=False, error=f'{type(exc).__name__}: {exc}')
        (args.output / f'{algorithm}.json').write_text(json.dumps(result, indent=2) + '\n')
        summary['results'][algorithm] = dict(passed=result['smoke_passed'],
                                            status=result.get('status'),
                                            termination_status=result.get('termination_status'),
                                            returncode=result.get('returncode'),
                                            error=result.get('error'))
    summary['passed'] = all(r['passed'] for r in summary['results'].values())
    (args.output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
