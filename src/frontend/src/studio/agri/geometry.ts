/**
 * 农业场景构建用的几何工具：确定性随机、多边形包含/距离、可放置性检查。
 *
 * 可放置性规则镜像后端 validate.py：位置必须在边界内、距边界 ≥ r、
 * 不在任何障碍内且距障碍 ≥ r。构建器与后端共用同一套规则，
 * 避免"前端能放、后端 400"的偏差（混合机队半径见 builders 镜像测试）。
 */

export type XY = [number, number];
export type Ring = XY[];

/** 确定性随机数（mulberry32 变体）：同一种子同一实例，保证可复现。 */
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 1831565813) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function pointInPolygon(p: XY, poly: Ring): boolean {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    if (yi > p[1] !== yj > p[1] && p[0] < ((xj - xi) * (p[1] - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

export function segDist(p: XY, a: XY, b: XY): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const l2 = dx * dx + dy * dy;
  const t = l2 === 0 ? 0 : Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2));
  return Math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy));
}

export function distToPolygon(p: XY, poly: Ring): number {
  let d = Infinity;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) d = Math.min(d, segDist(p, poly[j], poly[i]));
  return d;
}

/** 后端 validate.py 放置校验的镜像：在边界内、离边界 ≥ r、不在障碍内、离障碍 ≥ r。 */
export function placeable(p: XY, boundary: Ring, obstacles: Ring[], r: number): boolean {
  if (!pointInPolygon(p, boundary)) return false;
  if (distToPolygon(p, boundary) < r) return false;
  for (const ob of obstacles) {
    if (pointInPolygon(p, ob)) return false;
    if (distToPolygon(p, ob) < r) return false;
  }
  return true;
}

/** 圆盘多边形近似。 */
export function disc(cx: number, cy: number, r: number, n = 12, rot = 0): Ring {
  const pts: Ring = [];
  for (let i = 0; i < n; i++) {
    const a = rot + (2 * Math.PI * i) / n;
    pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
  }
  return pts;
}

export function rect(x0: number, y0: number, x1: number, y1: number): Ring {
  return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
}

/** L 形田块（非凸用例）。 */
export function lShape(w: number, h: number): Ring {
  const cw = w * 0.55;
  const ch = h * 0.55;
  return [[0, 0], [w, 0], [w, ch], [cw, ch], [cw, h], [0, h]];
}

/** 圆角两位小数：构建产物坐标稳定、便于 diff 与缓存。 */
export function round2(x: number): number {
  return Math.round(x * 100) / 100;
}

/** 环形布置（葡萄园/茶园条垄等）。 */
export function ringPoints(cx: number, cy: number, r: number, n: number, rot = 0): Ring {
  return disc(cx, cy, r, n, rot);
}
