"""Benchmark analysis for sets of solver runs: gaps, ranks, Friedman/Nemenyi, Wilcoxon–Holm, performance profiles,
ECDF of gaps, anytime curves, instance-space projection and LaTeX export (Demšar 2006; Dolan & Moré 2002; Smith-Miles 2023)."""
from __future__ import annotations

import math
import statistics as st
from collections import defaultdict

import numpy as np
from scipy import stats

SUCCESS_STATUS = ('optimal', 'feasible')


def _value(run) -> float | None:
    if run.get('state') != 'done' or run.get('status') not in SUCCESS_STATUS:
        return None
    if not (run.get('check') or {}).get('valid'):
        return None
    v = (run.get('objective') or {}).get('value')
    return float(v) if isinstance(v, (int, float)) and math.isfinite(v) else None


def _label(run, budgets: set) -> str:
    alg = run['algorithm']['id']
    if len(budgets) > 1:
        return f"{alg} @{run['params'].get('time_limit_s')}s"
    return alg


def _reference(runs_for_instance: list[dict]) -> tuple[float | None, str]:
    for r in runs_for_instance:
        bks = ((r.get('scenario_snapshot') or {}).get('reference') or {}).get('bks')
        if bks:
            return float(bks), 'BKS'
    vals = [v for v in (_value(r) for r in runs_for_instance) if v is not None]
    return (min(vals), '本组最好解') if vals else (None, '无可行解')


def analyze(runs: list[dict], alpha: float = 0.05) -> dict:
    runs = [r for r in runs if r.get('state') in ('done', 'error', 'timeout', 'canceled')]
    if not runs:
        return {'empty': True, 'n_runs': 0}
    budgets = {r['params'].get('time_limit_s') for r in runs}
    names = {}
    by_inst: dict[str, list] = defaultdict(list)
    for r in runs:
        key = f"{r['scenario_id']}#{r['instance_sha256'][:10]}"
        by_inst[key].append(r)
        names[_label(r, budgets)] = r['algorithm']
    algorithms = sorted(names)
    instances = sorted(by_inst)
    reference, ref_kind = {}, {}
    for i in instances:
        reference[i], ref_kind[i] = _reference(by_inst[i])
    # per (instance, algorithm): run values, gaps, times
    cell = defaultdict(lambda: {'values': [], 'gaps': [], 'times': [], 'runs': 0, 'failures': 0})
    for i in instances:
        for r in by_inst[i]:
            c = cell[(i, _label(r, budgets))]
            c['runs'] += 1
            v = _value(r)
            t = (r.get('metrics') or {}).get('wall_s')
            if t is not None:
                c['times'].append(float(t))
            if v is None:
                c['failures'] += 1
                continue
            c['values'].append(v)
            if reference[i]:
                c['gaps'].append(100.0 * (v - reference[i]) / reference[i])
    # mean objective per cell → ranks per instance (failures rank last, ties averaged)
    mean_obj = {(i, a): (st.mean(cell[(i, a)]['values']) if cell[(i, a)]['values'] else math.inf) for i in instances for a in algorithms}
    complete = [i for i in instances if all(cell[(i, a)]['runs'] for a in algorithms)]
    ranks = {}
    for i in complete:
        row = [mean_obj[(i, a)] for a in algorithms]
        for a, rk in zip(algorithms, stats.rankdata(row)):
            ranks[(i, a)] = float(rk)
    summary = []
    for a in algorithms:
        cs = [cell[(i, a)] for i in instances if cell[(i, a)]['runs']]
        gaps = [g for c in cs for g in c['gaps']]
        times = [t for c in cs for t in c['times']]
        n = sum(c['runs'] for c in cs)
        ok = sum(len(c['values']) for c in cs)
        summary.append({
            'algorithm': a, 'id': names[a]['id'], 'name': names[a].get('name'), 'source': names[a].get('source'),
            'instances': len(cs), 'runs': n, 'successes': ok, 'success_rate': ok / n if n else None,
            'gap_mean': st.mean(gaps) if gaps else None, 'gap_sd': st.stdev(gaps) if len(gaps) > 1 else None,
            'gap_median': st.median(gaps) if gaps else None, 'gap_best': min(gaps) if gaps else None,
            'time_mean': st.mean(times) if times else None, 'time_median': st.median(times) if times else None,
            'mean_rank': st.mean(ranks[(i, a)] for i in complete) if complete else None,
            'wins': sum(1 for i in complete if ranks[(i, a)] == min(ranks[(i, b)] for b in algorithms)),
        })
    per_instance = []
    for i in instances:
        sc = by_inst[i][0]
        row = {'instance': i, 'scenario_id': sc['scenario_id'], 'title': (sc.get('scenario_snapshot') or {}).get('title', sc['scenario_id']),
               'reference': reference[i], 'reference_kind': ref_kind[i], 'cells': {}}
        for a in algorithms:
            c = cell[(i, a)]
            if not c['runs']:
                continue
            row['cells'][a] = {'mean': st.mean(c['values']) if c['values'] else None, 'best': min(c['values']) if c['values'] else None,
                               'sd': st.stdev(c['values']) if len(c['values']) > 1 else None,
                               'gap_mean': st.mean(c['gaps']) if c['gaps'] else None, 'runs': c['runs'], 'failures': c['failures'],
                               'time_mean': st.mean(c['times']) if c['times'] else None, 'rank': ranks.get((i, a))}
        per_instance.append(row)
    tests = _tests(algorithms, complete, ranks, mean_obj, reference, alpha)
    return {
        'empty': False, 'n_runs': len(runs), 'n_instances': len(instances), 'n_complete_instances': len(complete),
        'algorithms': algorithms, 'summary': summary, 'per_instance': per_instance, 'tests': tests,
        'performance_profile': _profiles(algorithms, complete, mean_obj),
        'ecdf': {a: sorted(g for i in instances for g in cell[(i, a)]['gaps']) for a in algorithms},
        'anytime': _anytime(by_inst, reference, budgets),
        'scatter': [{'algorithm': _label(r, budgets), 'time': (r.get('metrics') or {}).get('wall_s'),
                     'gap': (100.0 * (_value(r) - reference[k]) / reference[k]) if _value(r) is not None and reference[k] else None,
                     'instance': k, 'run_id': r['run_id']} for k, rs in by_inst.items() for r in rs],
        'reference_note': 'CVRPLIB 算例以最优已知解（BKS）为参照，其余以本组所有算法的最好可行解为参照；失败或未通过检查的运行不计差距，按最差排序。',
    }


def _tests(algorithms, complete, ranks, mean_obj, reference, alpha):
    k, n = len(algorithms), len(complete)
    out = {'alpha': alpha, 'k': k, 'n': n}
    if k >= 3 and n >= 2:
        cols = [[mean_obj[(i, a)] if math.isfinite(mean_obj[(i, a)]) else 1e300 for i in complete] for a in algorithms]
        try:
            chi2, p = stats.friedmanchisquare(*cols)
            out['friedman'] = {'statistic': float(chi2), 'p_value': float(p), 'significant': bool(p < alpha)}
        except ValueError as exc:
            out['friedman'] = {'error': str(exc)}
        q = stats.studentized_range.ppf(1 - alpha, k, np.inf) / math.sqrt(2)
        out['nemenyi'] = {'q_alpha': float(q), 'critical_difference': float(q * math.sqrt(k * (k + 1) / (6.0 * n))),
                          'mean_ranks': {a: st.mean(ranks[(i, a)] for i in complete) for a in algorithms}}
    pairs = []
    for x in range(k):
        for y in range(x + 1, k):
            a, b = algorithms[x], algorithms[y]
            da = [mean_obj[(i, a)] for i in complete]
            db = [mean_obj[(i, b)] for i in complete]
            diffs = [p - q for p, q in zip(da, db) if math.isfinite(p) and math.isfinite(q)]
            row = {'a': a, 'b': b, 'n': len(diffs), 'a_better': sum(d < 0 for d in diffs), 'b_better': sum(d > 0 for d in diffs),
                   'ties': sum(d == 0 for d in diffs)}
            if len(diffs) >= 5 and any(diffs):
                res = stats.wilcoxon(diffs, zero_method='zsplit')
                row.update(statistic=float(res.statistic), p_value=float(res.pvalue))
            pairs.append(row)
    tested = sorted((r for r in pairs if 'p_value' in r), key=lambda r: r['p_value'])
    m = len(tested)
    running = 0.0
    for j, r in enumerate(tested):
        running = max(running, min(1.0, (m - j) * r['p_value']))
        r['p_holm'] = running
        r['significant'] = running < alpha
    out['wilcoxon_holm'] = pairs
    return out


def _profiles(algorithms, complete, mean_obj):
    if not complete:
        return {'taus': [], 'curves': {}}
    ratios = {a: [] for a in algorithms}
    for i in complete:
        best = min(mean_obj[(i, a)] for a in algorithms)
        for a in algorithms:
            v = mean_obj[(i, a)]
            ratios[a].append(v / best if math.isfinite(v) and best > 0 else (1.0 if v == best else math.inf))
    finite = [r for rs in ratios.values() for r in rs if math.isfinite(r)]
    top = max(finite + [1.0])
    taus = sorted({1.0, *np.round(np.linspace(1.0, top * 1.02, 60), 6).tolist(), *[r for r in finite]})
    return {'taus': taus, 'curves': {a: [sum(r <= t for r in rs) / len(rs) for t in taus] for a, rs in ratios.items()},
            'note': 'ρ(τ)：该算法成本不超过当期最好成本 τ 倍的实例比例（Dolan & Moré 2002）'}


def _anytime(by_inst, reference, budgets):
    curves = defaultdict(list)
    horizon = 0.0
    for k, rs in by_inst.items():
        ref = reference[k]
        if not ref:
            continue
        for r in rs:
            tr = r.get('trace') or []
            if not tr or _value(r) is None:
                continue
            horizon = max(horizon, tr[-1][0], float(r['params'].get('time_limit_s') or 0))
            curves[_label(r, budgets)].append([(t, 100.0 * (v - ref) / ref) for t, v in tr])
    if not curves:
        return {'grid': [], 'median': {}}
    grid = np.geomspace(1e-3, max(horizon, 1e-2), 48).tolist()
    med = {}
    for a, cs in curves.items():
        series = []
        for t in grid:
            vals = []
            for c in cs:
                prior = [g for (tt, g) in c if tt <= t]
                vals.append(prior[-1] if prior else math.inf)
            finite = [v for v in vals if math.isfinite(v)]
            series.append(st.median(vals) if len(finite) * 2 > len(vals) else None)
        med[a] = series
    return {'grid': grid, 'median': med, 'note': '各运行“当前最好解”相对参照的差距随时间变化的中位数；尚无可行解的运行按 +∞ 计。'}


def features(scenario: dict, instance: dict) -> tuple[list[str], list[float]] | None:
    pc = scenario['problem_class']
    if pc == 'euclidean_cvrp':
        from . import paths
        paths.ensure_research_path()
        from urp_research.cvrp_selection.experiment import features as f
        vals = f(instance)['values']
        return ['log 客户数', '平均需求/容量', '需求离散度', '半径离散度', '近邻距离/半径', '纵横比'], vals
    if pc == 'turn_routing':
        nodes = {u for u, _, _ in instance['arcs']} | {v for _, v, _ in instance['arcs']}
        triples = sum(1 for _ in instance['arcs']) or 1
        demand = sum(c['demand'] for c in instance['customers'])
        return (['任务数', '节点数', '平均出度', '禁止转弯比例', '转弯惩罚比例', '容量紧度'],
                [len(instance['customers']), len(nodes), len(instance['arcs']) / len(nodes),
                 len(instance['forbidden_turns']) / triples, len(instance['turn_penalties']) / triples, demand / instance['capacity']])
    return None


def instance_space(runs: list[dict]) -> dict:
    """PCA projection of instance features with best-algorithm labels and convex-hull footprints."""
    from shapely.geometry import MultiPoint
    by_inst = defaultdict(list)
    for r in runs:
        by_inst[r['instance_sha256']].append(r)
    names, rows, labels, ids = None, [], [], []
    for sha, rs in by_inst.items():
        r0 = rs[0]
        sc, inst = r0.get('scenario_snapshot'), r0.get('instance')
        if not sc or not inst:
            continue
        f = features(sc, inst)
        if not f:
            continue
        names = f[0]
        vals = defaultdict(list)
        for r in rs:
            v = _value(r)
            if v is not None:
                vals[r['algorithm']['id']].append(v)
        best = min(vals, key=lambda a: st.mean(vals[a])) if vals else None
        rows.append(f[1]); labels.append(best); ids.append({'scenario_id': r0['scenario_id'], 'title': sc.get('title')})
    if len(rows) < 3:
        return {'points': [], 'note': '至少需要 3 个带特征的实例（CVRP 或转弯路由）'}
    X = np.array(rows, dtype=float)
    mu, sd = X.mean(axis=0), X.std(axis=0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    P = Z @ Vt[:2].T
    var = (S ** 2) / max(1e-12, (S ** 2).sum())
    pts = [{'x': float(p[0]), 'y': float(p[1]), 'best': b, **meta} for p, b, meta in zip(P, labels, ids)]
    footprints = {}
    for a in {b for b in labels if b}:
        mine = [(p['x'], p['y']) for p in pts if p['best'] == a]
        if len(mine) >= 3:
            hull = MultiPoint(mine).convex_hull
            if hull.geom_type == 'Polygon':
                footprints[a] = [list(c) for c in hull.exterior.coords]
    return {'points': pts, 'features': names, 'loadings': Vt[:2].T.tolist(), 'explained_variance': var[:2].tolist(),
            'footprints': footprints, 'method': '标准化特征的主成分投影（Smith-Miles 实例空间分析的线性简化）'}


def latex_table(result: dict, caption: str = '算法比较') -> str:
    if result.get('empty'):
        return '% no runs\n'
    def f(v, d=2):
        return '--' if v is None else f'{v:.{d}f}'
    best_gap = min((s['gap_mean'] for s in result['summary'] if s['gap_mean'] is not None), default=None)
    lines = [r'\begin{table}[t]', r'\centering', rf'\caption{{{caption}}}', r'\begin{tabular}{lrrrrr}', r'\toprule',
             r'Algorithm & Success & Gap (\%) & Mean rank & Wins & Time (s) \\', r'\midrule']
    for s in sorted(result['summary'], key=lambda s: (s['mean_rank'] is None, s['mean_rank'] or 0)):
        gap = f(s['gap_mean'])
        if s['gap_sd'] is not None:
            gap += rf' $\pm$ {f(s["gap_sd"])}'
        if best_gap is not None and s['gap_mean'] == best_gap:
            gap = rf'\textbf{{{gap}}}'
        name = s['algorithm'].replace('_', r'\_').replace('#', r'\#')
        lines.append(rf"{name} & {s['successes']}/{s['runs']} & {gap} & {f(s['mean_rank'])} & {s['wins']} & {f(s['time_mean'], 3)} \\")
    lines += [r'\bottomrule', r'\end{tabular}']
    t = result['tests']
    if 'friedman' in t and 'statistic' in t['friedman']:
        lines.append(rf"\\[2pt]{{\footnotesize Friedman $\chi^2={t['friedman']['statistic']:.2f}$, $p={t['friedman']['p_value']:.3g}$; "
                     rf"Nemenyi CD$_{{\alpha={t['alpha']}}}={t['nemenyi']['critical_difference']:.2f}$ ($k={t['k']}, N={t['n']}$).}}")
    lines.append(r'\end{table}')
    return '\n'.join(lines) + '\n'
