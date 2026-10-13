import { describe, expect, it } from 'vitest';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { checkDecision, npSum, quantileLinear, remainingAfter } from './recompute';
import { canonicalIntList } from './sha256';
import type { Meta, RunRecord } from '../data/types';

const DATA = 'public/data';
const hasData = existsSync(`${DATA}/meta.json`) && existsSync(`${DATA}/runs`);

describe('numpy-compatible arithmetic', () => {
  it('sums small arrays exactly like a sequential loop from zero', () => {
    expect(npSum([1, 2, 3])).toBe(6);
    expect(npSum([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])).toBeCloseTo(4.5, 12);
  });
  it('implements linear quantiles', () => {
    const sorted = Float64Array.from({ length: 11 }, (_, i) => i * 10);
    expect(quantileLinear(sorted, 0.5)).toBe(50);
    expect(quantileLinear(sorted, 0.1)).toBeCloseTo(10, 12);
  });
});

describe.skipIf(!hasData)('recorded selector decisions (real data)', () => {
  const meta = hasData ? (JSON.parse(readFileSync(`${DATA}/meta.json`, 'utf8')) as Meta) : null;
  const files = hasData ? readdirSync(`${DATA}/runs`).filter((f) => f.endsWith('__SELECTOR.json')) : [];

  it('finds all 120 SELECTOR runs', () => {
    expect(files.length).toBe(120);
  });

  it('re-derives features, neighbours, predictions and choice for every decision', () => {
    let exactFeatures = 0;
    let worstFeature = 0;
    let worstDistance = 0;
    const mismatches: string[] = [];
    for (const f of files) {
      const run = JSON.parse(readFileSync(`${DATA}/runs/${f}`, 'utf8')) as RunRecord;
      const rem = remainingAfter(run.items, run.assignment, 500);
      const hash = createHash('sha256').update(canonicalIntList(rem)).digest('hex');
      if (hash !== run.prefix_remaining_sha256) mismatches.push(`${f}: prefix state hash`);
      const check = checkDecision(run.decision!, run.items.slice(0, 500), rem, meta!.model);
      exactFeatures += check.featuresExact;
      worstFeature = Math.max(worstFeature, check.featuresMaxAbs);
      worstDistance = Math.max(worstDistance, check.distancesMaxAbs);
      if (!check.neighborsMatch) mismatches.push(`${f}: neighbours`);
      if (!check.selectedMatch) mismatches.push(`${f}: selected index`);
      if (check.predictionsMaxAbs !== 0) mismatches.push(`${f}: predictions ${check.predictionsMaxAbs}`);
    }
    console.info(`features exact ${exactFeatures}/${files.length * 31}; worst |Δfeature| ${worstFeature}; worst |Δd²| ${worstDistance}`);
    expect(mismatches).toEqual([]);
    expect(worstFeature).toBeLessThanOrEqual(1e-12);
    expect(worstDistance).toBeLessThanOrEqual(1e-9);
  });
});
