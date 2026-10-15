import { describe, expect, it } from 'vitest';
import type { XY } from '../types';
import {
  boundsOf,
  chevrons,
  cumulative,
  distanceToPolyline,
  fitView,
  formatLength,
  gridLines,
  mapPlacement,
  nearest,
  niceCeil,
  niceStep,
  pathD,
  scaleBar,
  toScreen,
  toWorld,
  zoomAt,
} from './view';
import { sceneBounds, typicalSpacing } from './scene';

describe('world ↔ screen', () => {
  it('is y-up and invertible', () => {
    const v = { k: 10, tx: 100, ty: 200 };
    expect(toScreen(v, 0, 0)).toEqual([100, 200]);
    expect(toScreen(v, 1, 1)).toEqual([110, 190]);
    const [x, y] = toWorld(v, ...toScreen(v, 3.25, -7.5));
    expect(x).toBeCloseTo(3.25);
    expect(y).toBeCloseTo(-7.5);
  });

  it('fits bounds centred with padding and handles degenerate bounds', () => {
    const v = fitView({ minX: 0, minY: 0, maxX: 10, maxY: 5 }, 400, 300, 20);
    expect(v.k).toBeCloseTo(36);
    const [cx, cy] = toScreen(v, 5, 2.5);
    expect(cx).toBeCloseTo(200);
    expect(cy).toBeCloseTo(150);
    const single = fitView({ minX: 2, minY: 2, maxX: 2, maxY: 2 }, 400, 300);
    expect(Number.isFinite(single.k)).toBe(true);
    expect(toScreen(single, 2, 2)[0]).toBeCloseTo(200);
  });

  it('zooms around the cursor', () => {
    const v = { k: 2, tx: 10, ty: 50 };
    const before = toWorld(v, 120, 80);
    const z = zoomAt(v, 3, 120, 80);
    expect(z.k).toBe(6);
    const after = toWorld(z, 120, 80);
    expect(after[0]).toBeCloseTo(before[0]);
    expect(after[1]).toBeCloseTo(before[1]);
  });
});

describe('scale bar and grid', () => {
  it('picks 1/2/5 steps', () => {
    expect(niceStep(7.3)).toBe(5);
    expect(niceStep(0.031)).toBeCloseTo(0.02);
    expect(niceCeil(7.3)).toBe(10);
    expect(niceCeil(0.031)).toBeCloseTo(0.05);
  });

  it('labels units honestly', () => {
    expect(formatLength(5, 'm')).toBe('5 m');
    expect(formatLength(0.5, 'm')).toBe('50 cm');
    expect(formatLength(20, 'unitless')).toBe('20（无量纲）');
    const bar = scaleBar(30, 'm', 120);
    expect(bar.world).toBe(2);
    expect(bar.px).toBe(60);
    expect(bar.label).toBe('2 m');
  });

  it('places grid lines inside the viewport at ≥ minPx spacing', () => {
    const v = fitView({ minX: 0, minY: 0, maxX: 100, maxY: 100 }, 500, 500, 0);
    const g = gridLines(v, 500, 500, 56);
    expect(g.step * v.k).toBeGreaterThanOrEqual(56);
    expect(g.xs[0]).toBeGreaterThanOrEqual(0);
    expect(g.xs.at(-1)!).toBeLessThanOrEqual(100);
  });
});

describe('map image placement', () => {
  it('puts PNG row 0 at the maximum y', () => {
    const p = mapPlacement({ resolution: 0.05, origin: [-10, -5, 0], width: 400, height: 200 });
    expect(p.x).toBe(-10);
    expect(p.yBottom).toBe(-5);
    expect(p.yTop).toBeCloseTo(5);
    expect(p.width).toBeCloseTo(20);
  });
});

describe('polylines', () => {
  const line: XY[] = [
    [0, 0],
    [10, 0],
    [10, 10],
  ];

  it('builds path data and breaks on non-finite points', () => {
    expect(pathD(line)).toBe('M0 0L10 0L10 10');
    expect(pathD([[0, 0], [NaN, 1], [2, 2]])).toBe('M0 0M2 2');
  });

  it('accumulates length', () => {
    expect(Array.from(cumulative(line))).toEqual([0, 10, 20]);
  });

  it('places chevrons along the path with screen angles', () => {
    const v = { k: 10, tx: 0, ty: 200 };
    const ch = chevrons(line, cumulative(line), v, 400, 400, 50);
    expect(ch.length).toBe(4);
    expect(ch[0].angle).toBeCloseTo(0);
    // Going +y in the world is "up" on screen: −90°.
    expect(ch.at(-1)!.angle).toBeCloseTo(-90);
  });

  it('caps chevrons for long dense paths', () => {
    const pts: XY[] = Array.from({ length: 2000 }, (_, i) => [i, Math.sin(i / 10)]);
    const ch = chevrons(pts, cumulative(pts), { k: 50, tx: 0, ty: 100 }, 1e9, 1e9, 10, 300);
    expect(ch.length).toBe(300);
  });

  it('finds nearest points and distance to polylines', () => {
    expect(nearest([[0, 0], [5, 5], [9, 9]], 6, 6, 3)).toBe(1);
    expect(nearest([[0, 0]], 50, 50, 3)).toBe(-1);
    expect(distanceToPolyline([5, 3], line)).toBeCloseTo(3);
    expect(distanceToPolyline([12, 5], line)).toBeCloseTo(2);
    expect(distanceToPolyline([1, 1], [])).toBe(Infinity);
  });
});

describe('scene helpers', () => {
  it('bounds content and falls back to the map extent', () => {
    const b = sceneBounds({ units: 'm', nodes: [{ id: '1', xy: [1, 2], kind: 'task' }], paths: [{ id: 'p', points: [[-1, 5], [3, 3]], color: '#000' }] });
    expect(b).toEqual({ minX: -1, minY: 2, maxX: 3, maxY: 5 });
    const m = sceneBounds({ units: 'm', map: { image: '', resolution: 0.1, origin: [0, 0, 0], width: 10, height: 20 } });
    expect(m.maxY).toBeCloseTo(2);
    expect(m.maxX).toBeCloseTo(1);
  });

  it('estimates label spacing', () => {
    expect(typicalSpacing([[0, 0]])).toBe(Infinity);
    expect(typicalSpacing([[0, 0], [10, 10]])).toBeCloseTo(7.07, 1);
    expect(boundsOf([]).minX).toBe(Infinity);
  });
});
