"""Determinism analysis: feasibility flips, hash reproducibility and Wilson intervals on synthetic repeats."""
import json

from urp_lab.evolve import determinism as D


def _job(src, k, group='feasible', status='feasible', sha='s'):
    return {'job_id': f'{src}-{k}', 'family': 'coverage', 'config': 'full:none/n_swath', 'algorithm': 'f2c.full',
            'params': {'decomposition': 'none'}, 'instance': {'field': 'nl_field_1', 'profile': 'robot_s', 'repeat': k},
            'source_job': src, 'source_status': status, 'source_sha256': sha, 'sample_group': group}


def _rec(job, status='feasible', valid=True, sha=None, cost=None):
    return {'job_id': job['job_id'], 'status': status, 'valid': valid, 'routes_sha256': sha, 'objective': cost,
            'instance': job['instance'], 'config': job['config'], 'params': job['params']}


def _write(tmp_path, jobs, records):
    (tmp_path / 'plan.json').write_text(json.dumps({'jobs': jobs}), encoding='utf-8')
    (tmp_path / 'records').mkdir()
    for r in records:
        (tmp_path / 'records' / f"{r['job_id']}.json").write_text(json.dumps(r), encoding='utf-8')


def test_flip_and_wilson(tmp_path):
    jobs, recs = [], []
    for k in range(5):
        jobs.append(_job('A', k))
        recs.append(_rec(jobs[-1], sha='h1', cost=100.0))
        jobs.append(_job('B', k, sha='h1'))
        if k < 3:
            recs.append(_rec(jobs[-1], sha='h1' if k == 0 else 'h2', cost=[100.0, 110.0, 90.0][k]))
        else:
            recs.append(_rec(jobs[-1], status='no_solution', valid=False))
        jobs.append(_job('C', k, group='infeasible', status='no_solution', sha=None))
        recs.append(_rec(jobs[-1], status='no_solution', valid=False))
    _write(tmp_path, jobs, recs)
    res = D.analyse(tmp_path)
    assert res['tasks'] == 3 and res['repeats_per_task'] == 5
    a, b, c = {t['source_job']: t for t in res['per_task']}.values()
    assert a['reproducible'] and a['stable_feasibility'] and not a['flip'] and a['cost_cv'] == 0.0
    assert b['distinct_hashes'] == 2 and b['flip'] and not b['stable_feasibility']
    assert b['cost_cv'] is not None and abs(b['cost_cv'] - 0.1) < 1e-12
    assert b['matches_source'] == 1
    assert c['stable_feasibility'] and not c['reproducible'] and c['distinct_hashes'] == 0
    ov = res['overall']
    assert ov['reproducible_tasks'] == 1 and ov['stable_tasks'] == 2 and ov['flip_tasks'] == 1
    lo, hi = ov['flip_wilson95']
    assert 0.06 < lo < 0.07 and 0.79 < hi < 0.80      # Wilson(1/3, n=3)
    assert res['by_sample_group']['infeasible']['tasks'] == 1
    assert res['by_decomposition']['none']['tasks'] == 3


def test_missing_repeats_count_as_failures(tmp_path):
    jobs = [_job('A', k) for k in range(5)]
    recs = [_rec(jobs[k], sha='h1', cost=100.0) for k in range(3)]
    _write(tmp_path, jobs, recs)
    t = D.analyse(tmp_path)['per_task'][0]
    assert t['observed'] == 3 and t['expected'] == 5 and t['status_counts']['missing'] == 2
    assert not t['stable_feasibility'] and not t['reproducible'] and t['flip_any'] and not t['flip']


def test_wilson_bounds():
    lo, hi = D.wilson(0, 10)
    assert lo == 0.0 and abs(hi - 0.2775) < 1e-3
    lo, hi = D.wilson(10, 10)
    assert abs(lo - 0.7225) < 1e-3 and hi == 1.0
    assert D.wilson(0, 0) == [None, None]


def test_route_budget_probe_smoke():
    """The probe replays a recorded task and reports per-setting hash counts (F2C + field cache required)."""
    import pytest
    pytest.importorskip('fields2cover')
    from urp_lab.library import fields
    if not fields.status()['downloaded']:
        pytest.skip('Fields2Benchmark not cached')
    from urp_lab.evolve import route_determinism as R
    out = R.probe('evolve-audit-20261023', '8792aeb4e5a72873', repeats=1, workers=2, cores=(0, 1),
                  settings=('default', 'time_limit_10s'), write=False)
    assert set(out) == {'default', 'time_limit_10s'}
    assert all(isinstance(v[0], int) for v in out.values())
