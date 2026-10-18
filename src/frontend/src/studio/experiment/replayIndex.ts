import type { SimResult, TrailPoint } from './replay';

export const DEFAULT_MAX_GAP_S = 0.25;
export interface TrailIndex {
  ordered: boolean;
  gapLimit: number;
  distance: Float64Array;
  deviationSum: Float64Array;
  deviationMax: Float64Array;
  deviationCount: Uint32Array;
  missing: Float64Array;
  gaps: { start: number; end: number }[];
  segments: TrailPoint[][];
}

export function gapLimit(result?: SimResult): number {
  const limit = result?.replay_contract?.max_interpolation_gap_s;
  return typeof limit === 'number' && Number.isFinite(limit) && limit > 0 ? limit : DEFAULT_MAX_GAP_S;
}

export function distanceToPath(x: number, y: number, path: [number, number][]): number {
  let best = Infinity;
  for (let i = 1; i < path.length; i++) {
    const a = path[i - 1], b = path[i], dx = b[0] - a[0], dy = b[1] - a[1];
    const length = dx * dx + dy * dy;
    const f = length ? Math.max(0, Math.min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / length)) : 0;
    best = Math.min(best, Math.hypot(x - a[0] - f * dx, y - a[1] - f * dy));
  }
  return best;
}

const orderCache = new WeakMap<TrailPoint[], boolean>();
export function orderedTrail(trail: TrailPoint[]): boolean {
  const found = orderCache.get(trail);
  if (found !== undefined) return found;
  const value = trail.every((p, i) => p.length === 4 && p.every(Number.isFinite) && (!i || p[0] > trail[i - 1][0]));
  orderCache.set(trail, value);
  return value;
}

const cache = new WeakMap<SimResult, Map<string, TrailIndex>>();
/** One immutable result builds its cumulative arrays once; playback seeks are O(log n). */
export function replayIndex(result: SimResult, vehicle: string): TrailIndex {
  let vehicles = cache.get(result);
  if (!vehicles) { vehicles = new Map(); cache.set(result, vehicles); }
  const existing = vehicles.get(vehicle);
  if (existing) return existing;
  const trail = result.trails[vehicle] ?? [];
  const path = result.execution_plan?.vehicles?.find((item) => item.name === vehicle)?.path ?? [];
  const n = trail.length, limit = gapLimit(result);
  const index: TrailIndex = {
    ordered: orderedTrail(trail), gapLimit: limit, distance: new Float64Array(n), deviationSum: new Float64Array(n),
    deviationMax: new Float64Array(n), deviationCount: new Uint32Array(n), missing: new Float64Array(n), gaps: [], segments: [],
  };
  if (index.ordered) {
    let segment: TrailPoint[] = [];
    for (let i = 0; i < n; i++) {
      const p = trail[i], previous = trail[i - 1];
      const dt = previous ? p[0] - previous[0] : 0;
      const missing = dt > limit + 1e-9;
      if (missing) {
        if (segment.length) index.segments.push(segment);
        segment = [];
        index.gaps.push({ start: previous[0], end: p[0] });
      }
      segment.push(p);
      index.distance[i] = (index.distance[i - 1] ?? 0) + (previous && !missing ? Math.hypot(p[1] - previous[1], p[2] - previous[2]) : 0);
      index.missing[i] = (index.missing[i - 1] ?? 0) + (missing ? dt : 0);
      const deviation = distanceToPath(p[1], p[2], path);
      const measured = Number.isFinite(deviation);
      index.deviationSum[i] = (index.deviationSum[i - 1] ?? 0) + (measured ? deviation : 0);
      index.deviationMax[i] = Math.max(index.deviationMax[i - 1] ?? 0, measured ? deviation : 0);
      index.deviationCount[i] = (index.deviationCount[i - 1] ?? 0) + Number(measured);
    }
    if (segment.length) index.segments.push(segment);
  }
  vehicles.set(vehicle, index);
  return index;
}

/** Preserves sample order and gaps; visual decimation does not change the record. */
export function displaySegments(index: TrailIndex, until = Infinity, maxPoints = 1800): TrailPoint[][] {
  return index.segments.map((segment) => {
    let lo = 0, hi = segment.length;
    while (lo < hi) { const mid = (lo + hi) >> 1; if (segment[mid][0] <= until) lo = mid + 1; else hi = mid; }
    const stride = Math.max(1, Math.ceil(lo / maxPoints));
    const out: TrailPoint[] = [];
    for (let i = 0; i < lo; i += stride) out.push(segment[i]);
    if (lo && out.at(-1) !== segment[lo - 1]) out.push(segment[lo - 1]);
    return out;
  }).filter((segment) => segment.length > 0);
}
