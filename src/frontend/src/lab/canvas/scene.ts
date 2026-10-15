import type { XY } from '../types';
import type { CanvasPath, CanvasScene } from './types';
import { boundsOf, cumulative, emptyBounds, extend, isEmpty, mapPlacement, pathD, type Bounds } from './view';

/** Content bounds for fit-to-content; falls back to the map extent when there is nothing else. */
export function sceneBounds(scene: CanvasScene): Bounds {
  const b = emptyBounds();
  for (const p of scene.polygons ?? []) boundsOf(p.ring, b);
  for (const n of scene.nodes ?? []) extend(b, n.xy[0], n.xy[1]);
  for (const p of scene.paths ?? []) boundsOf(p.points, b);
  for (const m of scene.markers ?? []) extend(b, m.xy[0], m.xy[1]);
  for (const r of scene.robots ?? []) extend(b, r.xy[0], r.xy[1]);
  if (isEmpty(b) && scene.map) {
    const m = mapPlacement(scene.map);
    extend(b, m.x, m.yBottom);
    extend(b, m.x + m.width, m.yTop);
  }
  return b;
}

/** Typical spacing between labelled nodes in world units (for label decluttering). */
export function typicalSpacing(points: readonly XY[]): number {
  if (points.length < 2) return Infinity;
  const b = boundsOf(points);
  const area = Math.max((b.maxX - b.minX) * (b.maxY - b.minY), 1e-12);
  const spanSpacing = Math.max(b.maxX - b.minX, b.maxY - b.minY) / points.length;
  return Math.max(Math.sqrt(area / points.length), spanSpacing);
}

const geometryCache = new WeakMap<readonly XY[], { d: string; cum: Float64Array }>();

/** Cached path data + cumulative length per points array (points arrays are treated as immutable). */
export function pathGeometry(points: readonly XY[]) {
  let g = geometryCache.get(points);
  if (!g) {
    g = { d: pathD(points), cum: cumulative(points) };
    geometryCache.set(points, g);
  }
  return g;
}

export const pathLayer = (p: CanvasPath) => p.layer ?? 'routes';
