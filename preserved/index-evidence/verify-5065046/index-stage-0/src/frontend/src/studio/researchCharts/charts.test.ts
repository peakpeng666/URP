import { describe, expect, it } from 'vitest';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import type { Analysis } from '../types';
import { ProfileChart } from './AnalysisCharts';
import { analysis } from './testFixtures';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const html = <P,>(el: (props: P) => unknown, props: P) => renderToStaticMarkup(createElement(el as any, props as any));

describe('analysis chart rendering', () => {
  it('profile: legend matches series, facts include n, unsolved share, reference and direction', () => {
    const out = html(ProfileChart, { analysis: analysis() });
    expect(out).toContain('role="img"');
    expect(out).toContain('Alg A');
    expect(out).toContain('Alg B');
    expect(out).toContain('n = 2');
    expect(out).toContain('Alg B 50%');
    expect(out).toContain('参照');
    expect(out).toContain('方向');
    expect((out.match(/data-series=/g) ?? []).length).toBe(2);
  });
  it('profile empty state says 数据未提供 with the reason', () => {
    const out = html(ProfileChart, { analysis: analysis({ performance_profile: { taus: [], curves: {} } } as Partial<Analysis>) });
    expect(out).toContain('数据未提供');
    expect(out).toContain('taus');
    expect(out).not.toContain('role="img"');
  });
});

describe('ECDF rendering', () => {
  it('shows not-reached counts and the reference; empty ECDF data says 数据未提供', async () => {
    const { EcdfCharts } = await import('./AnalysisCharts');
    const a = analysis({ summary: [{ algorithm: 'a', name: 'Alg A', runs: 3, successes: 2 }] as Analysis['summary'], algorithms: ['a'],
      ecdf: { a: [0, 1] }, scatter: [{ algorithm: 'a', time: 1, gap: 0, instance: 'i', run_id: 'r' }], reference_note: 'BKS 参照' });
    const out = html(EcdfCharts, { analysis: a });
    expect(out).toContain('未达到 1/3');
    expect(out).toContain('BKS 参照');
    const empty = html(EcdfCharts, { analysis: analysis({ ecdf: {}, scatter: [] }) });
    expect((empty.match(/数据未提供/g) ?? []).length).toBe(2);
  });
});

describe('convergence rendering', () => {
  it('anytime: median drawn, interval explicitly 数据未提供; empty grid has a reason', async () => {
    const { AnytimeChart } = await import('./AnalysisCharts');
    const out = html(AnytimeChart, { analysis: analysis({ anytime: { grid: [0.1, 1], median: { a: [5, 1] } } }) });
    expect(out).toContain('区间：数据未提供');
    expect(out).toContain('data-series="a"');
    expect(html(AnytimeChart, { analysis: analysis() })).toContain('数据未提供：Analysis.anytime.grid 为空');
  });
  it('seed band: band drawn for multi-seed groups; quarantined-only input renders an empty state', async () => {
    const { SeedBandChart } = await import('./RunCharts');
    const { solved } = await import('./testFixtures');
    const out = html(SeedBandChart, { runs: [solved({ run_id: 'a' }), solved({ run_id: 'b', params: { seed: 2, time_limit_s: 2 }, trace: [[0.01, 30], [0.5, 10]] })] });
    expect(out).toContain('data-band');
    expect(out).toContain('种子 1、2');
    const empty = html(SeedBandChart, { runs: [solved({ process: { source_identity_verified: false } })] });
    expect(empty).toContain('数据未提供');
  });
});

describe('gap-time and CD rendering', () => {
  it('gap-time notes host and budget; CD renders ranks, cliques and an empty state', async () => {
    const { GapTimeChart, CdChart } = await import('./AnalysisCharts');
    const out = html(GapTimeChart, { analysis: analysis({ scatter: [{ algorithm: 'a', time: 1, gap: 0, instance: 'i', run_id: 'r' }] }) });
    expect(out).toContain('主机：数据未提供');
    expect(out).toContain('预算：数据未提供');
    const cd = html(CdChart, { analysis: analysis({ tests: { alpha: .05, k: 2, n: 4, wilcoxon_holm: [], nemenyi: { q_alpha: 1.96, critical_difference: 2, mean_ranks: { a: 1.25, b: 1.75 } } } }) });
    expect(cd).toContain('Alg A（1.25）');
    expect(cd).toContain('data-clique');
    expect(cd).toContain('Friedman：数据未提供');
    expect(html(CdChart, { analysis: analysis() })).toContain('数据未提供：tests.nemenyi 缺失');
  });
});

describe('verification rendering', () => {
  it('diagonal, hollow invalid markers, and an empty state without check values', async () => {
    const { VerificationChart } = await import('./RunCharts');
    const { solved } = await import('./testFixtures');
    const out = html(VerificationChart, { runs: [solved({ run_id: 'a' }), solved({ run_id: 'b', check: { valid: false, errors: [], computed_cost: 12 } })] });
    expect(out).toContain('data-diagonal');
    expect(out).toContain('data-point="invalid"');
    expect(out).toContain('验算未通过');
    expect(html(VerificationChart, { runs: [solved({ check: null })] })).toContain('数据未提供');
  });
});

describe('status flow rendering', () => {
  it('labels every category with its count and has an empty state', async () => {
    const { StatusFlowChart } = await import('./RunCharts');
    const { solved } = await import('./testFixtures');
    const out = html(StatusFlowChart, { runs: [solved(), solved({ process: undefined }), solved({ process: { source_identity_verified: false } })] });
    expect(out).toContain('data-status="success"');
    expect(out).toContain('有解 · 身份未核验 · 1');
    expect(out).toContain('已隔离（源码身份不符） · 1');
    expect(out).toContain('url(#st-quarantined)');
    expect(html(StatusFlowChart, { runs: [] })).toContain('数据未提供');
  });
});
