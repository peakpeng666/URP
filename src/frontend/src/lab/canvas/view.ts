/**
 * World ↔ screen math for the lab canvas. World is y-up (ROS map frame and
 * benchmark coordinates alike); screen is y-down CSS pixels:
 *   sx = tx + k·x,  sy = ty − k·y
 */
import type { XY } from '../types';

export interface View {
  k: number;
  tx: number;
  ty: number;
}

export interface Bounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

export type Units = 'm' | 'unitless';

export const MIN_K = 1e-3;
export const MAX_K = 1e5;

export const toScreen = (v: View, x: number, y: number): XY => [v.tx + v.k * x, v.ty - v.k * y];
export const toWorld = (v: View, sx: number, sy: number): XY => [(sx - v.tx) / v.k, (v.ty - sy) / v.k];

/** SVG transform placing world coordinates (y-up) into screen space. */
export const worldTransform = (v: View) => `matrix(${v.k} 0 0 ${-v.k} ${v.tx} ${v.ty})`;

export function emptyBounds(): Bounds {
  return { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity };
}

export function extend(b: Bounds, x: number, y: number): Bounds {
  if (!Number.isFinite(x) || !Number.isFinite(y)) return b;
  if (x < b.minX) b.minX = x;
  if (y < b.minY) b.minY = y;
  if (x > b.maxX) b.maxX = x;
  if (y > b.maxY) b.maxY = y;
  return b;
}

export function boundsOf(points: Iterable<XY>, into: Bounds = emptyBounds()): Bounds {
  for (const p of points) extend(into, p[0], p[1]);
  return into;
}

export const isEmpty = (b: Bounds) => !(b.maxX >= b.minX && b.maxY >= b.minY);

/** View that fits bounds into a w×h viewport with `pad` px margins (degenerate bounds get a unit box). */
export function fitView(b: Bounds, w: number, h: number, pad = 36): View {
  if (isEmpty(b) || w <= 0 || h <= 0) return { k: 1, tx: w / 2, ty: h / 2 };
  let { minX, minY, maxX, maxY } = b;
  const span = Math.max(maxX - minX, maxY - minY);
  const minSpan = span > 0 ? span * 0.05 : 1;
  if (maxX - minX < minSpan) {
    const c = (minX + maxX) / 2;
    minX = c - minSpan / 2;
    maxX = c + minSpan / 2;
  }
  if (maxY - minY < minSpan) {
    const c = (minY + maxY) / 2;
    minY = c - minSpan / 2;
    maxY = c + minSpan / 2;
  }
  const px = Math.min(pad, w / 4);
  const py = Math.min(pad, h / 4);
  const k = clampK(Math.min((w - 2 * px) / (maxX - minX), (h - 2 * py) / (maxY - minY)));
  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  return { k, tx: w / 2 - k * cx, ty: h / 2 + k * cy };
}

export const clampK = (k: number) => Math.min(MAX_K, Math.max(MIN_K, k));

/** Zoom by `factor` keeping the world point under (sx, sy) fixed. */
export function zoomAt(v: View, factor: number, sx: number, sy: number, minK = MIN_K, maxK = MAX_K): View {
  const k = Math.min(maxK, Math.max(minK, v.k * factor));
  const f = k / v.k;
  return { k, tx: sx - (sx - v.tx) * f, ty: sy - (sy - v.ty) * f };
}

export const panBy = (v: View, dx: number, dy: number): View => ({ k: v.k, tx: v.tx + dx, ty: v.ty + dy });

export function lerpView(a: View, b: View, t: number): View {
  // Interpolate scale geometrically so zoom feels uniform.
  const k = a.k * Math.pow(b.k / a.k, t);
  // Keep the screen centre's world point moving linearly.
  const s = (v: View) => [v.tx / v.k, v.ty / v.k];
  const [ax, ay] = s(a);
  const [bx, by] = s(b);
  return { k, tx: (ax + (bx - ax) * t) * k, ty: (ay + (by - ay) * t) * k };
}

/** Largest 1/2/5·10^n not above `x`. */
export function niceStep(x: number): number {
  if (!(x > 0) || !Number.isFinite(x)) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(x)));
  const m = x / p;
  return (m >= 5 ? 5 : m >= 2 ? 2 : 1) * p;
}

/** Smallest 1/2/5·10^n not below `x`. */
export function niceCeil(x: number): number {
  if (!(x > 0) || !Number.isFinite(x)) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(x)));
  const m = x / p;
  return (m <= 1 ? 1 : m <= 2 ? 2 : m <= 5 ? 5 : 10) * p;
}

export function formatLength(value: number, units: Units): string {
  const digits = value >= 1 ? 0 : Math.min(6, Math.ceil(-Math.log10(value)) + 1);
  const text = Number(value.toFixed(digits)).toString();
  if (units === 'm') return value < 1 ? `${Number((value * 100).toFixed(Math.max(0, digits - 2)))} cm` : `${text} m`;
  return `${text}（无量纲）`;
}

/** Scale bar of a "nice" world length whose screen length is ≤ maxPx. */
export function scaleBar(k: number, units: Units, maxPx = 120): { world: number; px: number; label: string } {
  const world = niceStep(maxPx / k);
  return { world, px: world * k, label: formatLength(world, units) };
}

export function visibleWorld(v: View, w: number, h: number): Bounds {
  const [x0, y1] = toWorld(v, 0, 0);
  const [x1, y0] = toWorld(v, w, h);
  return { minX: x0, minY: y0, maxX: x1, maxY: y1 };
}

/** Grid lines (world values) at a nice step at least `minPx` apart; capped for safety. */
export function gridLines(v: View, w: number, h: number, minPx = 56): { step: number; xs: number[]; ys: number[] } {
  const step = niceCeil(minPx / v.k);
  const vb = visibleWorld(v, w, h);
  const xs: number[] = [];
  const ys: number[] = [];
  for (let x = Math.ceil(vb.minX / step) * step; x <= vb.maxX && xs.length < 400; x += step) xs.push(x);
  for (let y = Math.ceil(vb.minY / step) * step; y <= vb.maxY && ys.length < 400; y += step) ys.push(y);
  return { step, xs, ys };
}

/** Occupancy map PNG placement in world units (row 0 of the PNG is the maximum y). */
export function mapPlacement(meta: { resolution: number; origin: readonly number[]; width: number; height: number }) {
  const w = meta.width * meta.resolution;
  const h = meta.height * meta.resolution;
  return { x: meta.origin[0], yTop: meta.origin[1] + h, yBottom: meta.origin[1], width: w, height: h };
}

/** SVG transform (inside the world group) that draws a w×h pixel image at the map's world placement. */
export function mapImageTransform(meta: { resolution: number; origin: readonly number[]; width: number; height: number }) {
  const p = mapPlacement(meta);
  return `translate(${p.x} ${p.yTop}) scale(${meta.resolution} ${-meta.resolution})`;
}

/** Path data in world coordinates; non-finite points break the line. */
export function pathD(points: readonly XY[]): string {
  let d = '';
  let pen = false;
  for (const p of points) {
    if (!p || !Number.isFinite(p[0]) || !Number.isFinite(p[1])) {
      pen = false;
      continue;
    }
    d += `${pen ? 'L' : 'M'}${round(p[0])} ${round(p[1])}`;
    pen = true;
  }
  return d;
}

/** Many independent segments as one path (cheap to draw thousands of arcs). */
export function segmentsD(segments: readonly (readonly [XY, XY])[]): string {
  let d = '';
  for (const [a, b] of segments) d += `M${round(a[0])} ${round(a[1])}L${round(b[0])} ${round(b[1])}`;
  return d;
}

/** Zero-length subpaths drawn with round caps render as dots. */
export function dotsD(points: readonly XY[]): string {
  let d = '';
  for (const p of points) d += `M${round(p[0])} ${round(p[1])}h0`;
  return d;
}

const round = (x: number) => Math.round(x * 10000) / 10000;

export function cumulative(points: readonly XY[]): Float64Array {
  const out = new Float64Array(points.length);
  for (let i = 1; i < points.length; i++) {
    out[i] = out[i - 1] + Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]);
  }
  return out;
}

export const polylineLength = (points: readonly XY[]) => (points.length ? cumulative(points)[points.length - 1] : 0);

/**
 * Direction chevrons every `spacingPx` screen pixels along a polyline, in
 * screen coordinates with angle in degrees (screen, clockwise). Only points
 * inside the viewport (+margin) are returned; capped at `max`.
 */
export function chevrons(
  points: readonly XY[],
  cum: Float64Array,
  v: View,
  w: number,
  h: number,
  spacingPx = 90,
  max = 400,
): { x: number; y: number; angle: number }[] {
  const out: { x: number; y: number; angle: number }[] = [];
  const n = points.length;
  if (n < 2) return out;
  const total = cum[n - 1];
  const step = spacingPx / v.k;
  if (!(total > 0) || !(step > 0)) return out;
  let i = 1;
  for (let s = step / 2; s < total && out.length < max; s += step) {
    while (i < n - 1 && cum[i] < s) i++;
    const seg = cum[i] - cum[i - 1];
    if (seg <= 0) continue;
    const t = (s - cum[i - 1]) / seg;
    const [ax, ay] = points[i - 1];
    const [bx, by] = points[i];
    const [sx, sy] = toScreen(v, ax + (bx - ax) * t, ay + (by - ay) * t);
    if (sx < -20 || sy < -20 || sx > w + 20 || sy > h + 20) continue;
    out.push({ x: sx, y: sy, angle: (Math.atan2(-(by - ay), bx - ax) * 180) / Math.PI });
  }
  return out;
}

/** Index of the nearest screen point within `radius` px, or -1. */
export function nearest(screen: readonly XY[], x: number, y: number, radius: number): number {
  let best = -1;
  let bestD = radius * radius;
  for (let i = 0; i < screen.length; i++) {
    const dx = screen[i][0] - x;
    const dy = screen[i][1] - y;
    const d = dx * dx + dy * dy;
    if (d <= bestD) {
      bestD = d;
      best = i;
    }
  }
  return best;
}

/** Distance from point p to the polyline (∞ when empty). */
export function distanceToPolyline(p: XY, line: readonly XY[]): number {
  if (line.length === 0) return Infinity;
  if (line.length === 1) return Math.hypot(p[0] - line[0][0], p[1] - line[0][1]);
  let best = Infinity;
  for (let i = 1; i < line.length; i++) {
    const [ax, ay] = line[i - 1];
    const [bx, by] = line[i];
    const dx = bx - ax;
    const dy = by - ay;
    const len2 = dx * dx + dy * dy;
    const t = len2 > 0 ? Math.max(0, Math.min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / len2)) : 0;
    const d = Math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy));
    if (d < best) best = d;
  }
  return best;
}

export function formatXY(p: XY, units: Units): string {
  const digits = units === 'm' ? 2 : 3;
  const f = (x: number) => Number(x.toFixed(digits)).toString();
  return units === 'm' ? `x ${f(p[0])} m, y ${f(p[1])} m` : `(${f(p[0])}, ${f(p[1])}) 无量纲`;
}
