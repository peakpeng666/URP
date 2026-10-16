import { memo, useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from 'react';
import { Maximize, Minus, Plus } from 'lucide-react';
import type { XY } from '../types';
import { useElementSize, usePrefersReducedMotion } from '../../lib/useElementSize';
import { DEFAULT_LAYERS, type CanvasMarker, type CanvasNode, type CanvasScene, type LayerKey } from './types';
import { pathGeometry, pathLayer, sceneBounds, typicalSpacing } from './scene';
import * as V from './view';
import s from './canvas.module.css';
import '../ui/lab.css';

export interface CanvasClick {
  altKey: boolean;
  shiftKey: boolean;
  metaKey: boolean;
  ctrlKey: boolean;
}

export interface MapCanvasProps {
  scene: CanvasScene;
  layers?: Partial<Record<LayerKey, boolean>>;
  /** Changing this re-fits the view to the content once content exists. */
  fitKey?: string;
  onNodeClick?: (node: CanvasNode, mods: CanvasClick) => void;
  onBackgroundClick?: (xy: XY, mods: CanvasClick) => void;
  cursor?: 'default' | 'crosshair';
  /** Floating controls at the top of the canvas. */
  toolbar?: ReactNode;
  /** Floating content at the bottom-left (above the scale bar), e.g. a legend. */
  overlay?: ReactNode;
  emptyText?: ReactNode;
  ariaLabel: string;
}

type Hover = { kind: 'node'; node: CanvasNode; sx: number; sy: number } | { kind: 'marker'; marker: CanvasMarker; sx: number; sy: number };

const KIND_TEXT: Record<string, string> = { depot: '仓库 / 出发点', task: '任务点', start: '作业起点', other: '路网节点' };
const STATE_TEXT: Record<string, string> = { pending: '待访', reached: '已到达', missed: '未到达' };
const ROLE_TEXT: Record<string, string> = { depot: '仓库', headland: '地头', row: '作物行', grid: '网格' };

const mods = (e: { altKey: boolean; shiftKey: boolean; metaKey: boolean; ctrlKey: boolean }): CanvasClick => ({
  altKey: e.altKey,
  shiftKey: e.shiftKey,
  metaKey: e.metaKey,
  ctrlKey: e.ctrlKey,
});

/** Interactive 2D canvas (SVG) with y-up world coordinates, pan/zoom, fit, grid, scale bar and hover tooltips. */
export function MapCanvas({
  scene,
  layers: layerProp,
  fitKey,
  onNodeClick,
  onBackgroundClick,
  cursor = 'default',
  toolbar,
  overlay,
  emptyText,
  ariaLabel,
}: MapCanvasProps) {
  const [ref, size] = useElementSize<HTMLDivElement>();
  const reduced = usePrefersReducedMotion();
  const [view, setView] = useState<V.View | null>(null);
  const viewRef = useRef(view);
  viewRef.current = view;
  // Until the user pans or zooms, the map keeps refitting when its panel resizes.
  const touched = useRef(false);
  const moveView = useCallback((f: (v: V.View | null) => V.View | null) => {
    touched.current = true;
    setView(f);
  }, []);
  const [hover, setHover] = useState<Hover | null>(null);
  const [pointer, setPointer] = useState<XY | null>(null);
  const [dragging, setDragging] = useState(false);
  const layers = useMemo(() => ({ ...DEFAULT_LAYERS, ...layerProp }), [layerProp]);
  const bounds = useMemo(() => sceneBounds(scene), [scene]);
  const units = scene.units;

  /* ------------------------------------------------------------ fitting -- */
  const anim = useRef(0);
  const stopAnim = () => {
    if (anim.current) cancelAnimationFrame(anim.current);
    anim.current = 0;
  };
  const animateTo = useCallback(
    (target: V.View) => {
      stopAnim();
      const from = viewRef.current;
      if (!from || reduced) {
        setView(target);
        return;
      }
      const t0 = performance.now();
      const tick = (now: number) => {
        const t = Math.min(1, (now - t0) / 260);
        const e = 1 - Math.pow(1 - t, 3);
        setView(V.lerpView(from, target, e));
        anim.current = t < 1 ? requestAnimationFrame(tick) : 0;
      };
      anim.current = requestAnimationFrame(tick);
    },
    [reduced],
  );
  useEffect(() => stopAnim, []);

  const fit = useCallback(() => {
    touched.current = false;
    if (size.width && size.height) animateTo(V.fitView(bounds, size.width, size.height, 44));
  }, [animateTo, bounds, size.width, size.height]);

  const pendingFit = useRef(true);
  const lastFitKey = useRef(fitKey);
  if (lastFitKey.current !== fitKey) {
    lastFitKey.current = fitKey;
    pendingFit.current = true;
  }
  const prevSize = useRef(size);
  useEffect(() => {
    const prev = prevSize.current;
    prevSize.current = size;
    if (!size.width || !size.height) return;
    if (pendingFit.current && !V.isEmpty(bounds)) {
      pendingFit.current = false;
      touched.current = false;
      if (viewRef.current) animateTo(V.fitView(bounds, size.width, size.height, 44));
      else setView(V.fitView(bounds, size.width, size.height, 44));
      return;
    }
    if (!viewRef.current) {
      setView(V.fitView(bounds, size.width, size.height, 44));
      return;
    }
    if (prev.width && prev.height && (prev.width !== size.width || prev.height !== size.height)) {
      if (!touched.current) setView(V.fitView(bounds, size.width, size.height, 44));
      else setView((v) => v && V.panBy(v, (size.width - prev.width) / 2, (size.height - prev.height) / 2));
    }
  }, [bounds, size, fitKey, animateTo]);

  /* ---------------------------------------------------------- hit tests -- */
  const hitTest = useCallback(
    (sx: number, sy: number): Hover | null => {
      const v = viewRef.current;
      if (!v) return null;
      if (layers.markers && scene.markers?.length) {
        const pts = scene.markers.map((m) => V.toScreen(v, m.xy[0], m.xy[1]));
        const i = V.nearest(pts, sx, sy, 9);
        if (i >= 0) return { kind: 'marker', marker: scene.markers[i], sx: pts[i][0], sy: pts[i][1] };
      }
      if (layers.nodes && scene.nodes?.length) {
        const pts = scene.nodes.map((n) => V.toScreen(v, n.xy[0], n.xy[1]));
        // Prefer tasks/depot over tiny graph nodes when both are close.
        const major = V.nearest(
          pts.map((p, i) => (scene.nodes![i].kind === 'other' ? ([Infinity, Infinity] as XY) : p)),
          sx,
          sy,
          11,
        );
        const i = major >= 0 ? major : V.nearest(pts, sx, sy, 7);
        if (i >= 0) return { kind: 'node', node: scene.nodes[i], sx: pts[i][0], sy: pts[i][1] };
      }
      return null;
    },
    [layers.markers, layers.nodes, scene.markers, scene.nodes],
  );

  /* ------------------------------------------------------------ pointer -- */
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const gesture = useRef<{ x: number; y: number; moved: boolean; pinch: number | null } | null>(null);
  const local = (e: { clientX: number; clientY: number }) => {
    const r = ref.current!.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };
  const isUi = (target: EventTarget | null) => target instanceof Element && !!target.closest('[data-canvas-ui]');

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    if (isUi(e.target) || (e.pointerType === 'mouse' && e.button !== 0)) return;
    stopAnim();
    const p = local(e);
    pointers.current.set(e.pointerId, p);
    e.currentTarget.setPointerCapture(e.pointerId);
    if (pointers.current.size === 1) gesture.current = { x: p.x, y: p.y, moved: false, pinch: null };
    else if (pointers.current.size === 2 && gesture.current) {
      const [a, b] = [...pointers.current.values()];
      gesture.current.pinch = Math.hypot(a.x - b.x, a.y - b.y);
      gesture.current.moved = true;
    }
  };

  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    if (isUi(e.target) && !pointers.current.size) {
      setHover(null);
      return;
    }
    const p = local(e);
    const v = viewRef.current;
    if (v) setPointer(V.toWorld(v, p.x, p.y));
    const prev = pointers.current.get(e.pointerId);
    if (!prev) {
      setHover(hitTest(p.x, p.y));
      return;
    }
    const g = gesture.current;
    if (pointers.current.size >= 2 && g?.pinch) {
      const others = [...pointers.current.entries()].filter(([id]) => id !== e.pointerId).map(([, q]) => q);
      const o = others[0];
      const dist = Math.hypot(p.x - o.x, p.y - o.y);
      const mid = { x: (p.x + o.x) / 2, y: (p.y + o.y) / 2 };
      const prevMid = { x: (prev.x + o.x) / 2, y: (prev.y + o.y) / 2 };
      const factor = dist / g.pinch;
      g.pinch = dist;
      moveView((cur) => cur && V.zoomAt(V.panBy(cur, mid.x - prevMid.x, mid.y - prevMid.y), factor, mid.x, mid.y));
    } else if (g) {
      if (!g.moved && Math.hypot(p.x - g.x, p.y - g.y) > 4) {
        g.moved = true;
        setDragging(true);
        setHover(null);
      }
      if (g.moved) moveView((cur) => cur && V.panBy(cur, p.x - prev.x, p.y - prev.y));
    }
    pointers.current.set(e.pointerId, p);
  };

  const endPointer = (e: PointerEvent<HTMLDivElement>, cancelled: boolean) => {
    if (!pointers.current.has(e.pointerId)) return;
    pointers.current.delete(e.pointerId);
    const g = gesture.current;
    if (pointers.current.size === 0) {
      gesture.current = null;
      setDragging(false);
      if (!cancelled && g && !g.moved) {
        const p = local(e);
        const hit = hitTest(p.x, p.y);
        const v = viewRef.current;
        if (hit?.kind === 'node' && onNodeClick) onNodeClick(hit.node, mods(e));
        else if (v && onBackgroundClick) onBackgroundClick(V.toWorld(v, p.x, p.y), mods(e));
        setHover(hit);
      }
    } else if (g) {
      g.pinch = null;
    }
  };

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (isUi(e.target)) return;
      e.preventDefault();
      stopAnim();
      const r = el.getBoundingClientRect();
      const scale = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1;
      const factor = Math.exp(-e.deltaY * scale * (e.ctrlKey ? 0.01 : 0.0018));
      moveView((v) => v && V.zoomAt(v, factor, e.clientX - r.left, e.clientY - r.top));
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [ref, moveView]);

  const zoomCenter = (factor: number) => {
    stopAnim();
    moveView((v) => v && V.zoomAt(v, factor, size.width / 2, size.height / 2));
  };

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (isUi(e.target)) return;
    const step = 60;
    const actions: Record<string, () => void> = {
      '+': () => zoomCenter(1.4),
      '=': () => zoomCenter(1.4),
      '-': () => zoomCenter(1 / 1.4),
      _: () => zoomCenter(1 / 1.4),
      '0': fit,
      ArrowLeft: () => moveView((v) => v && V.panBy(v, step, 0)),
      ArrowRight: () => moveView((v) => v && V.panBy(v, -step, 0)),
      ArrowUp: () => moveView((v) => v && V.panBy(v, 0, step)),
      ArrowDown: () => moveView((v) => v && V.panBy(v, 0, -step)),
      Escape: () => setHover(null),
    };
    const action = actions[e.key];
    if (action && !e.metaKey && !e.ctrlKey && !e.altKey) {
      e.preventDefault();
      action();
    }
  };

  /* ------------------------------------------------------------- render -- */
  const w = size.width;
  const h = size.height;
  const hasContent = !V.isEmpty(bounds) || !!scene.map;
  const scale = view ? V.scaleBar(view.k, units, 110) : null;

  return (
    <div
      ref={ref}
      className={s.canvas}
      tabIndex={0}
      role="application"
      aria-roledescription="二维画布"
      aria-label={`${ariaLabel}。拖动平移，滚轮或双指缩放，加减号缩放，0 适应内容。`}
      data-dragging={dragging || undefined}
      data-cursor={cursor}
      data-hover={hover && hover.kind === 'node' && onNodeClick ? 'true' : undefined}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={(e) => endPointer(e, false)}
      onPointerCancel={(e) => endPointer(e, true)}
      onPointerLeave={() => {
        if (!pointers.current.size) {
          setHover(null);
          setPointer(null);
        }
      }}
      onKeyDown={onKeyDown}
    >
      {view && w > 0 && h > 0 && (
        <svg className={s.svg} width={w} height={h} aria-hidden>
          {scene.map && layers.map && (
            <g transform={V.worldTransform(view)}>
              <image
                className={s.mapImage}
                href={scene.map.image}
                width={scene.map.width}
                height={scene.map.height}
                preserveAspectRatio="none"
                transform={V.mapImageTransform(scene.map)}
                style={{ imageRendering: view.k * scene.map.resolution >= 3 ? 'pixelated' : 'auto' }}
              />
            </g>
          )}
          {layers.grid && <Grid view={view} w={w} h={h} />}
          <g transform={V.worldTransform(view)}>
            <WorldLayer scene={scene} layers={layers} k={view.k} />
          </g>
          <ScreenLayer scene={scene} layers={layers} view={view} w={w} h={h} hover={hover} />
        </svg>
      )}
      {!hasContent && emptyText && <div className={s.empty}>{emptyText}</div>}
      {toolbar && (
        <div className={s.toolbar} data-canvas-ui>
          {toolbar}
        </div>
      )}
      <div className={s.bottomLeft}>
        {overlay && <div data-canvas-ui style={{ pointerEvents: 'auto' }}>{overlay}</div>}
        {scale && (
          <div className={`${s.glass} ${s.scale}`} title={units === 'm' ? 'map 坐标系，单位米' : '基准算例坐标，无物理单位'}>
            {scale.label}
            <div className={s.scaleBar} style={{ width: scale.px }} />
          </div>
        )}
      </div>
      <div className={s.bottomRight} data-canvas-ui>
        {pointer && (
          <div className={`${s.glass} ${s.readout}`} aria-hidden>
            {V.formatXY(pointer, units)}
          </div>
        )}
        <div className={`${s.glass} ${s.zoom}`}>
          <button type="button" className={s.zoomButton} onClick={() => zoomCenter(1.4)} title="放大（+）" aria-label="放大">
            <Plus size={14} />
          </button>
          <button type="button" className={s.zoomButton} onClick={() => zoomCenter(1 / 1.4)} title="缩小（-）" aria-label="缩小">
            <Minus size={14} />
          </button>
          <button type="button" className={s.zoomButton} onClick={fit} title="适应内容（0）" aria-label="适应内容">
            <Maximize size={13} />
          </button>
        </div>
      </div>
      {hover && <Tooltip hover={hover} units={units} w={w} h={h} hints={hover.kind === 'node' ? scene.turnHints?.(hover.node.id).length ?? 0 : 0} />}
    </div>
  );
}

/* ----------------------------------------------------------------- grid -- */
function Grid({ view, w, h }: { view: V.View; w: number; h: number }) {
  const g = V.gridLines(view, w, h, 64);
  let minor = '';
  let major = '';
  const isMajor = (x: number) => Math.abs(Math.round(x / (g.step * 5)) * g.step * 5 - x) < g.step * 1e-6;
  for (const x of g.xs) {
    const sx = Math.round(view.tx + view.k * x) + 0.5;
    const seg = `M${sx} 0V${h}`;
    if (isMajor(x)) major += seg;
    else minor += seg;
  }
  for (const y of g.ys) {
    const sy = Math.round(view.ty - view.k * y) + 0.5;
    const seg = `M0 ${sy}H${w}`;
    if (isMajor(y)) major += seg;
    else minor += seg;
  }
  return (
    <g>
      <path className={s.grid} d={minor} strokeWidth={1} />
      <path className={`${s.grid} ${s.gridMajor}`} d={major} strokeWidth={1} />
    </g>
  );
}

/* ---------------------------------------------------------- world layer -- */
const WorldLayer = memo(function WorldLayer({
  scene,
  layers,
  k,
}: {
  scene: CanvasScene;
  layers: Record<LayerKey, boolean>;
  k: number;
}) {
  const px = 1 / k;
  const arcsD = useMemo(() => (scene.arcs ? V.segmentsD(scene.arcs.map((a) => [a.a, a.b] as const)) : ''), [scene.arcs]);
  const dots = useMemo(
    () => V.dotsD((scene.nodes ?? []).filter((n) => n.kind === 'other').map((n) => n.xy)),
    [scene.nodes],
  );
  const polys = useMemo(
    () => (scene.polygons ?? []).map((p) => ({ ...p, d: `${V.pathD(p.ring)}Z` })),
    [scene.polygons],
  );
  return (
    <>
      {layers.areas &&
        polys.map((p) => <path key={p.id} d={p.d} className={s[`poly_${p.kind}`]} strokeWidth={px} />)}
      {layers.arcs && arcsD && <path d={arcsD} className={s.arcs} strokeWidth={1.1 * px} />}
      {layers.nodes && dots && <path d={dots} className={s.dots} strokeWidth={3.2 * px} />}
      {(scene.paths ?? []).map((p) => {
        if (!layers[pathLayer(p)] || p.points.length < 2) return null;
        const { d } = pathGeometry(p.points);
        return (
          <g key={p.id} opacity={p.opacity ?? 1}>
            {p.swath ? <path d={d} className={s.swath} style={{ stroke: p.color }} strokeWidth={p.swath} /> : null}
            <path
              d={d}
              className={s.route}
              style={{ stroke: p.color }}
              strokeWidth={(p.width ?? 2.5) * px}
              strokeDasharray={p.dash ? p.dash.map((x) => x * px).join(' ') : undefined}
            />
          </g>
        );
      })}
    </>
  );
});

/* --------------------------------------------------------- screen layer -- */
function ScreenLayer({
  scene,
  layers,
  view,
  w,
  h,
  hover,
}: {
  scene: CanvasScene;
  layers: Record<LayerKey, boolean>;
  view: V.View;
  w: number;
  h: number;
  hover: Hover | null;
}) {
  const inside = (p: XY, m = 24) => p[0] > -m && p[1] > -m && p[0] < w + m && p[1] < h + m;
  const spacing = useMemo(
    () => typicalSpacing((scene.nodes ?? []).filter((n) => n.kind === 'task').map((n) => n.xy)),
    [scene.nodes],
  );
  const taskCount = scene.nodes?.reduce((c, n) => c + (n.kind === 'task' ? 1 : 0), 0) ?? 0;
  const showLabels = layers.labels && (taskCount <= 14 || view.k * spacing >= 34);
  const sp = (xy: XY) => V.toScreen(view, xy[0], xy[1]);

  const arrows: ReactNode[] = [];
  if (layers.arcs && scene.arcs) {
    for (let i = 0; i < scene.arcs.length && arrows.length < 800; i++) {
      const a = scene.arcs[i];
      if (!a.oneWay) continue;
      const pa = sp(a.a);
      const pb = sp(a.b);
      const len = Math.hypot(pb[0] - pa[0], pb[1] - pa[1]);
      if (len < 46) continue;
      const m: XY = [pa[0] + (pb[0] - pa[0]) * 0.6, pa[1] + (pb[1] - pa[1]) * 0.6];
      if (!inside(m)) continue;
      const ang = (Math.atan2(pb[1] - pa[1], pb[0] - pa[0]) * 180) / Math.PI;
      arrows.push(<path key={i} className={s.arrow} d="M4 0L-3 -3.2L-3 3.2Z" transform={`translate(${m[0]} ${m[1]}) rotate(${ang})`} />);
    }
  }

  const pathGlyphs: ReactNode[] = [];
  for (const p of scene.paths ?? []) {
    if (!layers[pathLayer(p)] || p.points.length < 2) continue;
    if (layers.chevrons && p.chevrons) {
      const { cum } = pathGeometry(p.points);
      const ch = V.chevrons(p.points, cum, view, w, h, 84, 500);
      pathGlyphs.push(
        <g key={`${p.id}:ch`} opacity={p.opacity ?? 1}>
          {ch.map((c, i) => (
            <g key={i} transform={`translate(${c.x.toFixed(1)} ${c.y.toFixed(1)}) rotate(${c.angle.toFixed(1)})`}>
              <circle r={5.2} className={s.chevronBg} style={{ fill: p.color }} />
              <path d="M-1.6 -2.4L1.4 0L-1.6 2.4" className={s.chevron} />
            </g>
          ))}
        </g>,
      );
    }
    if (layers.order && p.order?.length) {
      pathGlyphs.push(
        <g key={`${p.id}:ord`} opacity={p.opacity ?? 1}>
          {p.order.map((o, i) => {
            const q = sp(o.xy);
            if (!inside(q)) return null;
            return (
              <g key={i} transform={`translate(${(q[0] + 10).toFixed(1)} ${(q[1] - 10).toFixed(1)})`}>
                <circle r={7.5} style={{ fill: p.color }} stroke="#fff" strokeWidth={1.2} />
                <text className={s.order}>{o.text}</text>
              </g>
            );
          })}
        </g>,
      );
    }
    if (p.tag) {
      const mid = p.points[Math.floor(p.points.length / 2)];
      const q = sp(mid);
      if (inside(q))
        pathGlyphs.push(
          <text key={`${p.id}:tag`} x={q[0] + 8} y={q[1] - 8} className={`${s.tag} ${s.halo}`} style={{ fill: p.color }}>
            {p.tag}
          </text>,
        );
    }
  }

  const nodes: ReactNode[] = [];
  if (layers.nodes) {
    for (const n of scene.nodes ?? []) {
      if (n.kind === 'other') continue;
      const q = sp(n.xy);
      if (!inside(q)) continue;
      const [x, y] = [q[0], q[1]];
      let glyph: ReactNode;
      if (n.kind === 'depot') glyph = <path className={s.depot} d={`M${x} ${y - 8}L${x + 8} ${y}L${x} ${y + 8}L${x - 8} ${y}Z`} />;
      else if (n.kind === 'start') glyph = <path className={s.start} d={`M${x - 6} ${y + 6}L${x} ${y - 8}L${x + 6} ${y + 6}Z`} />;
      else glyph = <circle cx={x} cy={y} r={5.2} className={n.state ? s[`task_${n.state}`] : s.task} />;
      const label = n.kind === 'task' && showLabels && n.label ? `${n.label}${n.demand != null ? ` · ${n.demand}` : ''}` : n.kind !== 'task' && layers.labels ? n.label : undefined;
      nodes.push(
        <g key={n.id}>
          {n.focus && <circle cx={x} cy={y} r={10} className={s.focusRing} />}
          {glyph}
          {label && (
            <text x={x + 8} y={y + 14} className={`${s.labelMuted} ${s.halo}`}>
              {label}
            </text>
          )}
        </g>,
      );
    }
  }

  const sceneLabels =
    layers.labels &&
    (scene.labels ?? []).map((l, i) => {
      const q = sp(l.xy);
      return inside(q) ? (
        <text key={i} x={q[0]} y={q[1]} className={`${s.sceneLabel} ${s.halo}`} textAnchor="middle">
          {l.text}
        </text>
      ) : null;
    });

  const markers =
    layers.markers &&
    (scene.markers ?? []).map((m) => {
      const q = sp(m.xy);
      if (!inside(q)) return null;
      return m.kind === 'violation' ? (
        <g key={m.id} transform={`translate(${q[0]} ${q[1]})`}>
          <circle r={6.5} className={s.violation} />
          <path d="M-2.6 -2.6L2.6 2.6M2.6 -2.6L-2.6 2.6" className={s.violationX} />
        </g>
      ) : (
        <circle key={m.id} cx={q[0]} cy={q[1]} r={4} fill="var(--mac-accent)" />
      );
    });

  const robots = (scene.robots ?? []).map((r) => {
    const q = sp(r.xy);
    const rr = (r.radius ?? 0) * view.k;
    const ang = (-r.yaw * 180) / Math.PI;
    return (
      <g key={r.id}>
        {rr > 5 && !r.ghost && <circle cx={q[0]} cy={q[1]} r={rr} className={s.footprint} style={{ fill: r.color, stroke: r.color }} />}
        <g transform={`translate(${q[0].toFixed(1)} ${q[1].toFixed(1)}) rotate(${ang.toFixed(1)})`}>
          <title>{r.title}</title>
          <path
            d="M11 0L-7 -7.5L-3.5 0L-7 7.5Z"
            className={r.ghost ? s.robotGhost : s.robotBody}
            style={r.ghost ? { stroke: r.color } : { fill: r.color }}
          />
        </g>
      </g>
    );
  });

  let hoverLayer: ReactNode = null;
  if (hover?.kind === 'node') {
    const hints = scene.turnHints?.(hover.node.id) ?? [];
    const n = hover.node;
    hoverLayer = (
      <g>
        {hints.map((line, i) => {
          const pts = line.map(sp);
          const last = pts[pts.length - 1];
          const prev = pts[pts.length - 2] ?? last;
          const ang = (Math.atan2(last[1] - prev[1], last[0] - prev[0]) * 180) / Math.PI;
          return (
            <g key={i}>
              <path className={s.hint} d={pts.map((p, j) => `${j ? 'L' : 'M'}${p[0]} ${p[1]}`).join('')} />
              <path className={s.hintHead} d="M5 0L-3 -4L-3 4Z" transform={`translate(${last[0]} ${last[1]}) rotate(${ang})`} />
            </g>
          );
        })}
        <circle cx={hover.sx} cy={hover.sy} r={n.kind === 'other' ? 6 : 10} className={s.hoverRing} />
        {n.kind === 'task' && !showLabels && n.label && (
          <text x={hover.sx + 9} y={hover.sy + 15} className={`${s.label} ${s.halo}`}>
            {n.label}
          </text>
        )}
      </g>
    );
  }

  return (
    <g>
      {arrows}
      {sceneLabels}
      {pathGlyphs}
      {nodes}
      {markers}
      {robots}
      {hoverLayer}
    </g>
  );
}

/* -------------------------------------------------------------- tooltip -- */
function Tooltip({ hover, units, w, h, hints }: { hover: Hover; units: V.Units; w: number; h: number; hints: number }) {
  const width = 240;
  const left = hover.sx + 16 + width > w ? Math.max(4, hover.sx - 16 - width) : hover.sx + 16;
  const top = hover.sy + 16 + 110 > h ? Math.max(4, hover.sy - 110) : hover.sy + 16;
  let body: ReactNode;
  if (hover.kind === 'marker') {
    body = (
      <>
        <strong>{hover.marker.kind === 'violation' ? '地图检查违规' : '标记'}</strong>
        <div>{hover.marker.title}</div>
        <div className={s.muted}>{V.formatXY(hover.marker.xy, units)}</div>
      </>
    );
  } else {
    const n = hover.node;
    body = (
      <>
        <strong>{n.label ?? `节点 ${n.id}`}</strong>{' '}
        <span className={s.muted}>
          {KIND_TEXT[n.kind]}
          {n.role && n.kind !== 'depot' ? ` · ${ROLE_TEXT[n.role] ?? n.role}` : ''}
        </span>
        <div className={s.muted}>节点 id {n.id}</div>
        <div>{V.formatXY(n.xy, units)}</div>
        {n.demand != null && <div>需求 {n.demand}</div>}
        {n.state && <div>状态：{STATE_TEXT[n.state]}</div>}
        {hints > 0 && <div style={{ color: 'var(--mac-red)' }}>经此节点的禁止转弯 {hints} 处（红色虚线）</div>}
        {n.extra?.map((t, i) => (
          <div key={i} className={s.muted}>
            {t}
          </div>
        ))}
      </>
    );
  }
  return (
    <div className={`${s.glass} ${s.tooltip}`} style={{ left, top, width }} role="tooltip">
      {body}
    </div>
  );
}
