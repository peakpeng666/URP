"""Study-level figures (several instances × algorithms × seeds): performance profiles (Dolan & Moré 2002),
gap distributions, Friedman + Nemenyi critical-difference diagram (Demšar 2006), pairwise Wilcoxon–Holm,
median anytime curves, time–quality trade-off, instance space (Smith-Miles et al.), and the evaluation of the
algorithm recommendation against the single best (SBS) and virtual best (VBS) solvers (as in ASlib)."""
from __future__ import annotations

import math
import statistics as stt
from collections import defaultdict

import numpy as np
from matplotlib.patches import Polygon as MPoly
from matplotlib.ticker import LogLocator, NullFormatter

from ..analysis import cd_unavailable_reason
from . import data as D
from .names import FEATURE_EN, alg_index, alg_label
from .style import Style, color, dash, figure, log_axis, marker, qlabel


def _names(an: dict, st: Style) -> dict[str, str]:
    zh = {s['algorithm']: s.get('name') for s in an.get('summary') or []}
    return {a: alg_label(a, st, zh.get(a)) for a in an.get('algorithms') or []}


def _n_text(an: dict, st: Style) -> str:
    return st.t(f"{an.get('n_instances')} 个实例（{an.get('n_complete_instances')} 个所有算法齐全）、{an.get('n_runs')} 次运行",
                f"{an.get('n_instances')} instances ({an.get('n_complete_instances')} complete for all algorithms), {an.get('n_runs')} runs")


def perf_profile(ctx: D.Context, st: Style, opts: dict):
    an = ctx.analysis
    pp = an['performance_profile']
    names = _names(an, st)
    taus = np.asarray(pp['taus'], float)
    fig, axs = figure(st, 0.7)
    ax = axs[0][0]
    rows = []
    for a in an['algorithms']:
        rho = np.asarray(pp['curves'].get(a) or [], float)
        if not len(rho):
            continue
        i = alg_index(a)
        ax.step(taus, rho, where='post', color=color(i), ls=dash(i), lw=1.1, label=names[a])
        rows += [{'algorithm': a, 'tau': float(t), 'rho': float(r)} for t, r in zip(taus, rho)]
    if taus.max(initial=1) > 2:
        from matplotlib.ticker import FuncFormatter
        ax.set_xscale('log', base=2)
        ax.xaxis.set_major_locator(LogLocator(base=2))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:g}'))
        ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlim(1, taus.max(initial=1.0) * 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel(st.t('性能比 τ', 'Performance ratio τ'))
    ax.set_ylabel(st.t('实例比例 ρ(τ)', 'Fraction of instances ρ(τ)'))
    ax.grid(which='major')
    ax.legend(loc='lower right')
    cap = {
        'zh': f"性能曲线（Dolan & Moré 2002）：ρ(τ) 为该算法成本不超过每个实例最好成本 τ 倍的实例比例；曲线越靠左上越好，τ = 1 处为取得最好解的比例。"
              f"基于 {_n_text(an, st)}，只纳入所有算法齐全的实例，每个实例取各算法可行运行的平均成本；全失败的算法–实例单元保留在分母，在有限 τ 处不计成功。部分种子失败另见运行成功率。",
        'en': f"Performance profiles (Dolan & Moré 2002): ρ(τ) is the fraction of instances on which an algorithm's cost is within a factor τ of the best; "
              f"higher and further left is better. Based on complete paired instances from {_n_text(an, st)}; per-instance cost is the mean over feasible runs. An algorithm-instance cell with no feasible run remains in the instance denominator but never counts at finite τ. Partial seed failures are reflected separately in run success rates.",
    }
    return fig, cap, {'profile': rows}


def gap_distribution(ctx: D.Context, st: Style, opts: dict):
    an = ctx.analysis
    names = _names(an, st)
    algs = [a for a in an['algorithms'] if an['ecdf'].get(a)]
    algs.sort(key=lambda a: stt.median(an['ecdf'][a]))
    k = len(algs)
    fig, axs = figure(st, max(0.32, min(1.0, 0.16 + 0.085 * k)))
    ax = axs[0][0]
    data = [np.asarray(an['ecdf'][a], float) for a in algs]
    pos = np.arange(k)[::-1] + 1
    bp = ax.boxplot(data, positions=pos, orientation='horizontal', whis=(5, 95), showfliers=False, widths=0.55, patch_artist=True,
                    medianprops={'color': '#111111', 'lw': 0.8}, boxprops={'lw': 0.5}, whiskerprops={'lw': 0.5}, capprops={'lw': 0.5})
    rng = np.random.default_rng(7)                          # jitter only: fixed seed so the figure is reproducible
    rows = []
    for j, (a, d) in enumerate(zip(algs, data)):
        i = alg_index(a)
        bp['boxes'][j].set_facecolor(color(i))
        bp['boxes'][j].set_alpha(0.35)
        ax.plot(d, pos[j] + rng.uniform(-0.16, 0.16, len(d)), ls='none', marker=marker(i), ms=1.8, mfc=color(i), mec='none', alpha=0.8, zorder=3)
        rows += [{'algorithm': a, 'gap_pct': float(g)} for g in d]
    ax.set_yticks(pos, [names[a] for a in algs])
    allg = np.concatenate(data) if data else np.zeros(1)
    if allg.max() > 100 and np.median(allg) < 20:
        ax.set_xscale('symlog', linthresh=1)
    ax.set_xlabel(qlabel(st, '相对参照解的差距', 'Gap to reference', '%'))
    ax.grid(axis='x')
    ax.axvline(0, color='#888888', lw=0.5)
    cap = {
        'zh': f"各算法相对参照解差距的分布（每点一次有有限差距的有效运行；失败和无正参照运行不画点；箱体为四分位，须为 5–95 百分位）。参照：{an.get('reference_note')} {_n_text(an, st)}。",
        'en': f"Distribution of the gap to the reference solution per algorithm (one point per finite valid-run gap; failures and runs without a positive reference are not plotted; boxes are quartiles, whiskers the 5th–95th percentiles). "
              f"Reference: best-known solution for CVRPLIB instances, otherwise the best valid solution found by any algorithm. {_n_text(an, st)}.",
    }
    return fig, cap, {'gaps': rows}


def cd_diagram(ctx: D.Context, st: Style, opts: dict):
    """Critical-difference diagram (Demšar 2006): mean ranks on an axis, groups not significantly different joined by bars."""
    an = ctx.analysis
    tests = an['tests']
    reason = cd_unavailable_reason(tests)
    if reason:
        raise ValueError(reason)
    nem = tests['nemenyi']
    names = _names(an, st)
    ranks = sorted(nem['mean_ranks'].items(), key=lambda kv: kv[1])
    k = len(ranks)
    cd = nem['critical_difference']
    left = ranks[: (k + 1) // 2]
    right = ranks[(k + 1) // 2:]
    rows_per_side = max(len(left), len(right))
    fig, axs = figure(st, 0.18 + 0.055 * rows_per_side)
    ax = axs[0][0]
    ax.set_xlim(0.5 - 0.95 * k / 3, k + 0.5 + 0.95 * k / 3)
    top = 0.0
    ax.set_ylim(-(rows_per_side * 0.9 + 0.45), 1.6)
    ax.axis('off')
    ax.hlines(top, 1, k, color='#111111', lw=0.8)
    for r in range(1, k + 1):
        ax.vlines(r, top, top + 0.22, color='#111111', lw=0.8)
        ax.text(r, top + 0.32, str(r), ha='center', va='bottom', fontsize=st.fs - 0.5)
    for i, (a, rk) in enumerate(left):
        y = -(i + 1) * 0.9
        ax.plot([rk, rk, 0.85], [top, y, y], color='#111111', lw=0.7)
        ax.text(0.8, y, f'{names[a]}  {rk:.2f}', ha='right', va='center', fontsize=st.fs - 0.5)
    for i, (a, rk) in enumerate(right[::-1]):
        y = -(i + 1) * 0.9
        ax.plot([rk, rk, k + 0.15], [top, y, y], color='#111111', lw=0.7)
        ax.text(k + 0.2, y, f'{rk:.2f}  {names[a]}', ha='left', va='center', fontsize=st.fs - 0.5)
    # CD bar
    ax.plot([1, 1 + cd], [1.15, 1.15], color='#111111', lw=1.0)
    for x in (1, 1 + cd):
        ax.vlines(x, 1.05, 1.25, color='#111111', lw=0.8)
    ax.text(1 + cd / 2, 1.3, f'CD = {cd:.2f}', ha='center', va='bottom', fontsize=st.fs - 0.5)
    # cliques: maximal runs of consecutive algorithms whose rank spread is below CD
    vals = [rk for _, rk in ranks]
    cliques = []
    for i in range(k):
        j = i
        while j + 1 < k and vals[j + 1] - vals[i] <= cd:
            j += 1
        if j > i and not any(a <= i and j <= b for a, b in cliques):
            cliques.append((i, j))
    for c, (i, j) in enumerate(cliques):
        y = -0.25 - 0.18 * c
        ax.plot([vals[i] - 0.03, vals[j] + 0.03], [y, y], color='#111111', lw=2.2, solid_capstyle='butt')
    fr = tests.get('friedman') or {}
    ptxt = f"p = {fr['p_value']:.2g}" if fr.get('p_value') is not None else st.t('无法计算', 'not computable')
    cap = {
        'zh': f"临界差图（Demšar 2006）：轴上为各算法在 {tests['n']} 个实例上的平均秩（1 为最好），粗横线连接的算法之间差异不显著"
              f"（Nemenyi 检验，α = {tests['alpha']}，CD = {cd:.2f}）。Friedman 检验 χ² = {fr.get('statistic'):.2f}，{ptxt}。",
        'en': f"Critical-difference diagram (Demšar 2006): mean ranks over {tests['n']} instances (1 = best); algorithms joined by a thick bar are not "
              f"significantly different (Nemenyi, α = {tests['alpha']}, CD = {cd:.2f}). Friedman test χ² = {fr.get('statistic'):.2f}, {ptxt}.",
    }
    rows = [{'algorithm': a, 'mean_rank': rk} for a, rk in ranks] + [{'algorithm': 'CD', 'mean_rank': cd}]
    return fig, cap, {'ranks': rows}


def pairwise(ctx: D.Context, st: Style, opts: dict):
    an = ctx.analysis
    names = _names(an, st)
    algs = an['algorithms']
    k = len(algs)
    idx = {a: i for i, a in enumerate(algs)}
    M = np.full((k, k), np.nan)
    star = [['' for _ in range(k)] for _ in range(k)]
    for r in an['tests']['wilcoxon_holm']:
        if not r['n']:
            continue
        i, j = idx[r['a']], idx[r['b']]
        M[i, j] = r['a_better'] / r['n']
        M[j, i] = r['b_better'] / r['n']
        p = r.get('p_holm')
        if p is not None:
            s = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
            if r['a_better'] > r['b_better']:
                star[i][j] = s
            elif r['b_better'] > r['a_better']:
                star[j][i] = s
    fig, axs = figure(st, 0.82)
    ax = axs[0][0]
    im = ax.imshow(M, cmap='RdBu', vmin=0, vmax=1)
    for i in range(k):
        for j in range(k):
            if i != j and np.isfinite(M[i, j]):
                ax.text(j, i, f'{M[i, j]:.2f}{star[i][j]}', ha='center', va='center', fontsize=st.fs - 1.5,
                        color='white' if abs(M[i, j] - 0.5) > 0.32 else '#111111')
    ax.set_xticks(range(k), [names[a] for a in algs], rotation=40, ha='right')
    ax.set_yticks(range(k), [names[a] for a in algs])
    ax.set_xlabel(st.t('列：对手算法', 'Column: opponent'))
    for sp in ax.spines.values():
        sp.set_visible(False)
    cb = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    cb.set_label(st.t('优于对手的实例比例', 'Share of instances better than opponent'))
    cb.outline.set_linewidth(0.4)
    cap = {
        'zh': f"两两比较：格中数字为行算法优于列算法的实例比例，星号为 Wilcoxon 符号秩检验经 Holm 校正后的显著性（* p<0.05，** p<0.01，*** p<0.001；"
              f"仅纳入双方成本及差值有限的配对；有效配对不足 5 个或全部平局时不检验）。{_n_text(an, st)}。",
        'en': f"Pairwise comparison: each cell is the share of instances on which the row algorithm beats the column algorithm; stars mark Wilcoxon signed-rank "
              f"tests with Holm correction (* p<0.05, ** p<0.01, *** p<0.001; only finite-cost, finite-difference pairs are included; fewer than 5 such pairs or all ties are not tested). {_n_text(an, st)}.",
    }
    return fig, cap, {'pairs': an['tests']['wilcoxon_holm']}


def anytime_median(ctx: D.Context, st: Style, opts: dict):
    an = ctx.analysis
    names = _names(an, st)
    grid = np.asarray(an['anytime']['grid'], float)
    fig, axs = figure(st, 0.62)
    ax = axs[0][0]
    rows = []
    for a in an['algorithms']:
        med = an['anytime']['median'].get(a)
        if not med:
            continue
        i = alg_index(a)
        y = np.array([np.nan if v is None or not math.isfinite(v) else v for v in med], float)
        ax.plot(grid, y, color=color(i), ls=dash(i), lw=1.1, label=names[a], drawstyle='steps-post')
        rows += [{'algorithm': a, 't_s': float(t), 'median_gap_pct': None if np.isnan(v) else float(v)} for t, v in zip(grid, y)]
    log_axis(ax, 'x')
    ax.set_xlabel(qlabel(st, '计算时间', 'Wall-clock time', 's'))
    ax.set_ylabel(qlabel(st, '差距中位数', 'Median gap', '%'))
    ax.set_ylim(bottom=0)
    ax.grid(which='major')
    ax.legend(loc='upper right')
    ex = int(an['anytime'].get('excluded') or 0)
    cap = {
        'zh': f"各算法“当前最好解”相对参照差距的中位数随时间的变化（尚无可行解的运行按 +∞ 计，超过半数无解时不画）。{_n_text(an, st)}。"
              + (f"另有 {ex} 次运行的过程轨迹记录的是求解器内部目标（终值与目标值不一致，如“尽快完成”任务中的 PyVRP），未计入。" if ex else ''),
        'en': f"Median gap of the best-so-far solution over time (runs without a feasible solution count as +∞; not drawn while more than half have none). {_n_text(an, st)}."
              + (f" {ex} runs whose trace records the solver's internal objective (final value ≠ objective, e.g. PyVRP on makespan task maps) are excluded." if ex else ''),
    }
    return fig, cap, {'anytime': rows}


def time_quality(ctx: D.Context, st: Style, opts: dict):
    an = ctx.analysis
    names = _names(an, st)
    pts = [p for p in an['scatter'] if p.get('time') is not None and p.get('gap') is not None]
    fig, axs = figure(st, 0.68)
    ax = axs[0][0]
    med = []
    for a in an['algorithms']:
        mine = [p for p in pts if p['algorithm'] == a]
        if not mine:
            continue
        i = alg_index(a)
        t = np.maximum([p['time'] for p in mine], 1e-3)
        g = np.asarray([p['gap'] for p in mine], float)
        ax.plot(t, g, ls='none', marker=marker(i), ms=2.4, mfc=color(i), mec='none', alpha=0.55)
        med.append((a, float(np.median(t)), float(np.median(g)), i))
        ax.plot(np.median(t), np.median(g), ls='none', marker=marker(i), ms=5.5, mfc=color(i), mec='#111111', mew=0.6, zorder=5, label=names[a])
    front = sorted(med, key=lambda m: m[1])
    best, line = math.inf, []
    for m in front:
        if m[2] < best:
            best = m[2]
            line.append(m)
    if len(line) > 1:
        ax.step([m[1] for m in line], [m[2] for m in line], where='post', color='#444444', lw=0.6, ls=':', zorder=4)
    log_axis(ax, 'x')
    ax.set_xlabel(qlabel(st, '计算时间', 'Wall-clock time', 's'))
    ax.set_ylabel(qlabel(st, '相对参照解的差距', 'Gap to reference', '%'))
    ax.grid(which='major')
    ax.legend(loc='upper right')
    cap = {
        'zh': f"计算时间与解质量的权衡：小点为单次运行，大点为各算法的中位数，点线为中位数的帕累托前沿。{_n_text(an, st)}。",
        'en': f"Time–quality trade-off: small markers are single runs, large markers the per-algorithm medians, the dotted line the Pareto front of the medians. {_n_text(an, st)}.",
    }
    return fig, cap, {'runs': pts, 'medians': [{'algorithm': a, 'time_median_s': t, 'gap_median_pct': g} for a, t, g, _ in med]}


TIE = 1e-5   # relative: objective values closer than this are the same solution quality (floating-point noise between solvers)


def _best(vals: dict[str, float]) -> tuple[str | None, list[str]]:
    """Best algorithm, or None with the list of tied algorithms."""
    if not vals:
        return None, []
    lo = min(vals.values())
    ties = sorted((a for a, v in vals.items() if v <= lo + TIE * max(1.0, abs(lo))), key=alg_index)
    return (ties[0] if len(ties) == 1 else None), ties


def _advice_space(runs: list[dict]) -> dict:
    """Instance space of the recommender's own input features (the state it saw at submission)."""
    by = defaultdict(list)
    for r in runs:
        by[r['instance_sha256']].append(r)
    rows, labels, ids, keys, names = [], [], [], None, None
    for sha, rs in by.items():
        adv = next((((r.get('recommendation_at_submission') or {}).get('advice')) for r in rs if (r.get('recommendation_at_submission') or {}).get('advice')), None)
        if not adv:
            continue
        feats = [f for f in adv.get('features') or [] if isinstance(f.get('value'), (int, float))]
        if not feats:
            continue
        ks = [f['key'] for f in feats]
        if keys is None:
            keys, names = ks, [f.get('name') or f['key'] for f in feats]
        if ks != keys:
            continue
        vals = defaultdict(list)
        for r in rs:
            v = (r.get('objective') or {}).get('value')
            if r.get('state') == 'done' and (r.get('check') or {}).get('valid') and v is not None:
                vals[r['algorithm']['id']].append(v)
        best, ties = _best({a: stt.mean(v) for a, v in vals.items()})
        rows.append([float(f['value']) for f in feats])
        labels.append(best if best else ('tie' if ties else None))
        ids.append({'scenario_id': rs[0]['scenario_id'], 'recommended': adv.get('recommended'), 'ties': ties})
    if len(rows) < 3:
        return {'points': []}
    X = np.asarray(rows, float)
    sd = X.std(axis=0)
    keep = sd > 0
    Z = (X[:, keep] - X[:, keep].mean(axis=0)) / sd[keep]
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    P = Z @ Vt[:2].T if Vt.shape[0] >= 2 else np.c_[Z @ Vt[:1].T, np.zeros(len(Z))]
    var = (S ** 2) / max(1e-12, float((S ** 2).sum()))
    return {'points': [{'x': float(p[0]), 'y': float(p[1]), 'best': b, **m} for p, b, m in zip(P, labels, ids)],
            'features': [n for n, k in zip(names, keep) if k], 'feature_keys': [k for k, kk in zip(keys, keep) if kk],
            'explained_variance': var[:2].tolist(), 'method': 'recommender features'}


def instance_space(ctx: D.Context, st: Style, opts: dict):
    space = ctx.space if (ctx.space or {}).get('points') else _advice_space(ctx.study_runs)
    an = ctx.analysis or {}
    names = _names(an, st) if an.get('algorithms') else {}
    pts = space['points']
    algs = sorted({p['best'] for p in pts if p['best'] and p['best'] != 'tie'}, key=alg_index)
    fig, axs = figure(st, 0.85)
    ax = axs[0][0]
    for a in algs:
        i = alg_index(a)
        fp = (space.get('footprints') or {}).get(a)
        if fp:
            ax.add_patch(MPoly(fp, closed=True, fc=color(i), ec=color(i), alpha=0.12, lw=0.6))
        mine = [p for p in pts if p['best'] == a]
        ax.plot([p['x'] for p in mine], [p['y'] for p in mine], ls='none', marker=marker(i), ms=3.8, mfc=color(i), mec='white', mew=0.3,
                label=names.get(a) or alg_label(a, st))
    tie = [p for p in pts if p['best'] == 'tie']
    if tie:
        ax.plot([p['x'] for p in tie], [p['y'] for p in tie], ls='none', marker='o', ms=3.8, mfc='#BBBBBB', mec='#555555', mew=0.4,
                label=st.t('多个算法并列最好', 'Several algorithms tie'))
    none = [p for p in pts if not p['best']]
    if none:
        ax.plot([p['x'] for p in none], [p['y'] for p in none], ls='none', marker='x', ms=3.6, mec='#888888', label=st.t('无可行解', 'No feasible run'))
    def missed(p):
        rec = p.get('recommended')
        return bool(rec) and p['best'] is not None and rec != p['best'] and rec not in (p.get('ties') or [])
    wrong = [p for p in pts if missed(p)]
    if wrong:
        ax.plot([p['x'] for p in wrong], [p['y'] for p in wrong], ls='none', marker='o', ms=7.5, mfc='none', mec='#C0392B', mew=0.8,
                label=st.t('推荐不是最好', 'Recommendation not best'))
    ev = space.get('explained_variance') or [0, 0]
    ax.set_xlabel(f'PC1 ({100 * ev[0]:.0f}%)')
    ax.set_ylabel(f'PC2 ({100 * ev[1]:.0f}%)' if len(ev) > 1 else 'PC2')
    ax.axhline(0, color='#DDDDDD', lw=0.4, zorder=0)
    ax.axvline(0, color='#DDDDDD', lw=0.4, zorder=0)
    ax.legend(loc='best', fontsize=st.fs - 1)
    fz = space.get('features') or []
    fe = [FEATURE_EN.get(k, k) for k in space.get('feature_keys') or []] or fz
    cap = {
        'zh': f"实例空间：{len(pts)} 个实例按标准化特征（{'、'.join(fz)}）做主成分投影，颜色 / 标记为该实例上平均成本最好的算法"
              f"（相对差 < {TIE:.0e} 视为并列），阴影为其凸包{'；红圈为推荐算法不在最好之列的实例' if wrong else '；所有实例上推荐算法都在最好之列'}。"
              f"（Smith-Miles 实例空间分析的线性简化）",
        'en': f"Instance space: principal-component projection of {len(pts)} instances on standardised features ({', '.join(fe)}); colour / marker = algorithm with the "
              f"best mean cost on that instance (relative differences < {TIE:.0e} count as ties), shaded = its convex hull"
              f"{'; red circles: the recommended algorithm was not among the best' if wrong else '; the recommended algorithm was among the best on every instance'} "
              f"(a linear simplification of Smith-Miles' instance space analysis).",
    }
    return fig, cap, {'points': pts}


def selection_eval(ctx: D.Context, st: Style, opts: dict):
    """Recommended algorithm (AS) vs single best solver (SBS) vs per-instance oracle (VBS)."""
    ev = selection_table(ctx.study_runs)
    an = ctx.analysis or {}
    names = _names(an, st) if an.get('algorithms') else {}
    fig, axs = figure(st, 0.62)
    ax = axs[0][0]
    rows = ev['rows']
    for label, key, c, ls in ((st.t('推荐（AS）', 'Recommended (AS)'), 'gap_as', color(0), '-'),
                              (st.t(f"单一最佳（SBS：{names.get(ev['sbs'], ev['sbs'])}）", f"Single best (SBS: {names.get(ev['sbs'], ev['sbs'])})"), 'gap_sbs', color(1), '--')):
        g = np.sort([r[key] for r in rows if r[key] is not None])
        if len(g):
            ax.step(np.r_[0, g], np.r_[0, np.arange(1, len(g) + 1) / len(g)], where='post', color=c, ls=ls, lw=1.1, label=label)
    ax.axvline(0, color='#444444', lw=0.6, ls=':', label=st.t('理想（VBS）', 'Oracle (VBS)'))
    ax.set_xlabel(qlabel(st, '相对每个实例最好算法的差距', 'Gap to the per-instance best', '%'))
    ax.set_ylabel(st.t('实例累计比例', 'Cumulative share of instances'))
    ax.set_ylim(0, 1.02)
    ax.set_xlim(left=min(-0.5, -0.02 * max([r['gap_sbs'] or 0 for r in rows] + [1])))
    ax.grid(which='major')
    ax.legend(loc='lower right')
    cg = ev['closed_gap']
    cap = {
        'zh': f"算法推荐的效果（{ev['n']} 个推荐算法已运行的实例）：曲线为相对每个实例最好算法（VBS）的差距的累计分布（相对差 < {TIE:.0e} 视为并列）。"
              f"推荐命中最好算法 {ev['hits']}/{ev['n']}，平均差距 推荐 {ev['mean_as']:.3g}% / 单一最佳 {ev['mean_sbs']:.3g}%"
              + (f"，闭合差距 {cg:.2f}（1 = 达到 VBS，0 = 等同 SBS）" if cg is not None else '') + f"。推荐取自每次运行提交时保存的建议快照（策略 {ev['policy']}）。",
        'en': f"Effect of the algorithm recommendation ({ev['n']} instances on which the recommended algorithm was run): cumulative distribution of the gap to the "
              f"per-instance best algorithm (VBS; relative differences < {TIE:.0e} count as ties). The recommendation hit the best algorithm on {ev['hits']}/{ev['n']} "
              f"instances; mean gap {ev['mean_as']:.3g}% (recommended) vs {ev['mean_sbs']:.3g}% (single best)" + (f", closed gap {cg:.2f} (1 = VBS, 0 = SBS)" if cg is not None else '') +
              f". Recommendations are the snapshots stored with each run at submission (policy {ev['policy']}).",
    }
    return fig, cap, {'instances': rows}


def selection_table(runs: list[dict]) -> dict:
    by = defaultdict(list)
    for r in runs:
        by[f"{r['scenario_id']}#{r['instance_sha256'][:10]}"].append(r)
    per, recs, policies = {}, {}, set()
    for k, rs in by.items():
        vals = defaultdict(list)
        for r in rs:
            v = (r.get('objective') or {}).get('value')
            if r.get('state') == 'done' and (r.get('check') or {}).get('valid') and v is not None and math.isfinite(v):
                vals[r['algorithm']['id']].append(float(v))
            adv = (r.get('recommendation_at_submission') or {}).get('advice') or {}
            if adv.get('recommended'):
                recs[k] = adv['recommended']
                policies.add(adv.get('policy') or '?')
        per[k] = {a: stt.mean(v) for a, v in vals.items()}
    algs = sorted({a for p in per.values() for a in p})
    complete = [k for k, p in per.items() if p and all(a in p for a in algs)]
    gap = lambda v, best: 100.0 * (v - best) / best if best > 0 else 0.0  # noqa: E731
    sbs = min(algs, key=lambda a: stt.mean(gap(per[k][a], min(per[k].values())) for k in complete)) if complete else None
    rows = []
    for k in complete:
        p, rec = per[k], recs.get(k)
        if rec not in p:
            continue
        best = min(p.values())
        g_as, g_sbs = gap(p[rec], best), gap(p[sbs], best)
        g_as, g_sbs = (0.0 if g < 100 * TIE else g for g in (g_as, g_sbs))      # floating-point ties between solvers
        rows.append({'instance': k, 'recommended': rec, 'vbs': _best(p)[1] or [min(p, key=p.get)], 'gap_as': g_as, 'gap_sbs': g_sbs, 'hit': g_as == 0.0})
    n = len(rows)
    mean_as = stt.mean(r['gap_as'] for r in rows) if rows else float('nan')
    mean_sbs = stt.mean(r['gap_sbs'] for r in rows) if rows else float('nan')
    return {'rows': rows, 'n': n, 'hits': sum(r['hit'] for r in rows), 'sbs': sbs, 'mean_as': mean_as, 'mean_sbs': mean_sbs,
            'closed_gap': (mean_sbs - mean_as) / mean_sbs if rows and mean_sbs > 1e-12 else None, 'policy': '、'.join(sorted(policies)) or '—'}



