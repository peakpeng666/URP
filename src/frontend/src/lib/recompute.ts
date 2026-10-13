/**
 * Read-only re-derivation of the frozen selector decision (src/selector.py in
 * the research package) from the recorded prefix and recorded assignments.
 * Used only to CHECK the recorded decision; the UI always displays recorded
 * values. Summation mirrors NumPy (identity 0 + pairwise blocks of 8) so most
 * values match bit-for-bit; any difference is reported, never hidden.
 */
import type { Model } from '../data/types';

export function pairwiseSum(a: ArrayLike<number>, start = 0, n = a.length - start): number {
  if (n < 8) {
    let res = -0.0;
    for (let i = 0; i < n; i += 1) res += a[start + i];
    return res;
  }
  if (n <= 128) {
    let r0 = a[start];
    let r1 = a[start + 1];
    let r2 = a[start + 2];
    let r3 = a[start + 3];
    let r4 = a[start + 4];
    let r5 = a[start + 5];
    let r6 = a[start + 6];
    let r7 = a[start + 7];
    let i = 8;
    const stop = n - (n % 8);
    for (; i < stop; i += 8) {
      r0 += a[start + i];
      r1 += a[start + i + 1];
      r2 += a[start + i + 2];
      r3 += a[start + i + 3];
      r4 += a[start + i + 4];
      r5 += a[start + i + 5];
      r6 += a[start + i + 6];
      r7 += a[start + i + 7];
    }
    let res = (r0 + r1 + (r2 + r3)) + (r4 + r5 + (r6 + r7));
    for (; i < n; i += 1) res += a[start + i];
    return res;
  }
  let n2 = Math.floor(n / 2);
  n2 -= n2 % 8;
  return pairwiseSum(a, start, n2) + pairwiseSum(a, start + n2, n - n2);
}

/** numpy.sum for a 1-D float64 array. */
export const npSum = (a: ArrayLike<number>): number => 0.0 + pairwiseSum(a);

const npMean = (a: ArrayLike<number>): number => npSum(a) / a.length;

function npStd(a: ArrayLike<number>): number {
  const mean = npMean(a);
  const sq = new Float64Array(a.length);
  for (let i = 0; i < a.length; i += 1) {
    const d = a[i] - mean;
    sq[i] = d * d;
  }
  return Math.sqrt(npSum(sq) / a.length);
}

/** numpy.quantile(..., method='linear') on an already sorted array. */
export function quantileLinear(sorted: ArrayLike<number>, q: number): number {
  const n = sorted.length;
  const virtualIndex = n * q + (1 + q * -1) - 1;
  let prev = Math.floor(virtualIndex);
  const gamma = virtualIndex - prev;
  prev = Math.min(Math.max(prev, 0), n - 1);
  const next = Math.min(prev + 1, n - 1);
  const a = sorted[prev];
  const b = sorted[next];
  const diff = b - a;
  return gamma >= 0.5 ? b - diff * (1 - gamma) : a + diff * gamma;
}

export const PREFIX_LENGTH = 500;

/** The 31 prefix/state features in PROTOCOL.json.features.names order. */
export function computeFeatures(prefix: ArrayLike<number>, remaining: ArrayLike<number>): number[] {
  if (prefix.length !== PREFIX_LENGTH) throw new RangeError('prefix must contain 500 items');
  const p = Float64Array.from(prefix);
  const used: number[] = [];
  for (let i = 0; i < remaining.length; i += 1) if (remaining[i] < 100) used.push(remaining[i]);
  if (!used.length) throw new RangeError('no used bins in prefix state');

  const itemHist = new Array<number>(10).fill(0);
  for (const x of p) itemHist[Math.floor((x - 1) / 10)] += 1;
  const sorted = Float64Array.from(p).sort();
  let inc = 0;
  let dec = 0;
  for (let i = 1; i < p.length; i += 1) {
    if (p[i] > p[i - 1]) inc += 1;
    else if (p[i] < p[i - 1]) dec += 1;
  }
  const first100 = npMean(p.subarray(0, 100));
  const last100 = npMean(p.subarray(p.length - 100));
  const residualHist = new Array<number>(10).fill(0);
  for (const r of used) residualHist[Math.floor(r / 10)] += 1;
  const u = Float64Array.from(used);

  return [
    ...itemHist.map((c) => c / PREFIX_LENGTH),
    npMean(p) / 100,
    npStd(p) / 100,
    quantileLinear(sorted, 0.1) / 100,
    quantileLinear(sorted, 0.5) / 100,
    quantileLinear(sorted, 0.9) / 100,
    inc / (p.length - 1),
    dec / (p.length - 1),
    (last100 - first100) / 100,
    used.length / PREFIX_LENGTH,
    ...residualHist.map((c) => c / used.length),
    npMean(u) / 100,
    npStd(u) / 100,
  ];
}

export interface KnnResult {
  z: number[];
  distances: Float64Array;
  /** Training row order sorted by distance (stable), full length 144. */
  ranking: number[];
  neighbors: number[];
  squaredDistances: number[];
  predicted: [number, number];
  selectedIndex: number;
}

export function knn(features: number[], model: Model): KnnResult {
  const z = features.map((f, j) => (f - model.mean[j]) / model.scale[j]);
  const distances = new Float64Array(model.x.length);
  const row = new Float64Array(z.length);
  for (let i = 0; i < model.x.length; i += 1) {
    const xi = model.x[i];
    for (let j = 0; j < z.length; j += 1) {
      const d = xi[j] - z[j];
      row[j] = d * d;
    }
    distances[i] = npSum(row);
  }
  const ranking = Array.from(distances.keys()).sort((a, b) => distances[a] - distances[b] || a - b);
  const neighbors = ranking.slice(0, model.k);
  const sums: [number, number] = [0, 0];
  for (const i of neighbors) {
    sums[0] += model.y[i][0];
    sums[1] += model.y[i][1];
  }
  const predicted: [number, number] = [sums[0] / neighbors.length, sums[1] / neighbors.length];
  const selectedIndex = predicted[0] === predicted[1] ? model.sbs_index : predicted[0] < predicted[1] ? 0 : 1;
  return {
    z,
    distances,
    ranking,
    neighbors,
    squaredDistances: neighbors.map((i) => distances[i]),
    predicted,
    selectedIndex,
  };
}

/** Bin residuals after the first `steps` recorded assignments. */
export function remainingAfter(
  items: ArrayLike<number>,
  assignment: ArrayLike<number>,
  steps: number,
  slots = 5000,
  capacity = 100,
): Int32Array {
  const rem = new Int32Array(slots).fill(capacity);
  for (let i = 0; i < steps; i += 1) rem[assignment[i]] -= items[i];
  return rem;
}

export interface DecisionCheck {
  featuresCompared: number;
  featuresExact: number;
  featuresMaxAbs: number;
  neighborsMatch: boolean;
  distancesMaxAbs: number;
  predictionsMaxAbs: number;
  selectedMatch: boolean;
  recomputed: KnnResult;
  features: number[];
}

export function checkDecision(
  recorded: { features: number[]; neighbors: number[]; squared_distances: number[]; predicted_final_bins: number[]; selected_index: number },
  prefix: ArrayLike<number>,
  remaining: ArrayLike<number>,
  model: Model,
): DecisionCheck {
  const features = computeFeatures(prefix, remaining);
  let exact = 0;
  let maxAbs = 0;
  features.forEach((f, j) => {
    const diff = Math.abs(f - recorded.features[j]);
    if (diff === 0) exact += 1;
    maxAbs = Math.max(maxAbs, diff);
  });
  // Rank with the recomputed features; compare against the record.
  const result = knn(features, model);
  const neighborsMatch = result.neighbors.length === recorded.neighbors.length
    && result.neighbors.every((n, i) => n === recorded.neighbors[i]);
  const distancesMaxAbs = Math.max(
    ...result.squaredDistances.map((d, i) => Math.abs(d - recorded.squared_distances[i])),
  );
  const predictionsMaxAbs = Math.max(
    Math.abs(result.predicted[0] - recorded.predicted_final_bins[0]),
    Math.abs(result.predicted[1] - recorded.predicted_final_bins[1]),
  );
  return {
    featuresCompared: features.length,
    featuresExact: exact,
    featuresMaxAbs: maxAbs,
    neighborsMatch,
    distancesMaxAbs,
    predictionsMaxAbs,
    selectedMatch: result.selectedIndex === recorded.selected_index,
    recomputed: result,
    features,
  };
}
