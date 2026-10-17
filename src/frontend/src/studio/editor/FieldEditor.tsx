import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent as RPointerEvent, type ReactNode, type WheelEvent as RWheelEvent } from 'react';
import { useElementSize } from '../../lib/useElementSize';
import { fitView, toScreen, toWorld, worldTransform, zoomAt, type View } from '../../lab/canvas/view';
import type { XY } from '../../lab/types';
import type { FleetInstance, FleetRoute, ObstacleKind, Selection, Tool } from '../types';
import {
  OBSTACLE_STYLE,
  along,
  boundsOf,
  centroid,
  nextObstacleId,
  obstacleShape,
  pointInPolygon,
  rect,
  round,
  taskIssues,
  translate,
  vehicleOfTask,
} from './geometry';
import s from './editor.module.css';

export interface FieldEditorProps {
  inst: FleetInstance;
  routes: FleetRoute[];
  hidden: string[];
  playback: number | null;
  tool: Tool;
  obstacleKind: ObstacleKind;
  selection: Selection;
  editable: boolean;
  fitKey: string;
  /** Lane centre lines between crop rows (drawn faintly when vehicles travel along the rows). */
  lanes?: XY[][];
  violations?: XY[];
  /** Display-only layer under the plots (a map asset in task-map metres); never hit-tested. */
  background?: ReactNode;
  /** Extra world-space layer above the routes (e.g. a simulation replay); receives the view for pixel-sized marks. */
  overlay?: (view: View) => ReactNode;
  onEdit: (fn: (i: FleetInstance) => FleetInstance) => void;
  onSelect: (s: Selection) => void;
  onCursor?: (p: XY | null) => void;
}

type Drag =
  | { kind: 'pan'; sx: number; sy: number; view: View }
  | { kind: 'task'; id: number; from: XY; orig: XY }
  | { kind: 'depot'; from: XY; orig: XY }
  | { kind: 'poly'; target: 'obstacle' | 'plot'; id: string; from: XY; orig: XY[] }
  | { kind: 'vertex'; target: 'obstacle' | 'plot' | 'boundary'; id: string; index: number }
  | { kind: 'shape'; target: 'obstacle' | 'plot'; from: XY; to: XY };

const GRID_STEPS = [0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500];

export function FieldEditor(props: FieldEditorProps) {
  const { inst, routes, hidden, playback, tool, obstacleKind, selection, editable, fitKey, lanes, violations, background, overlay, onEdit, onSelect, onCursor } = props;
  const [box, size] = useElementSize<HTMLDivElement>();
  const [view, setView] = useState<View>({ k: 1, tx: 0, ty: 0 });
  const [preview, setPreview] = useState<FleetInstance | null>(null);
  const [shape, setShape] = useState<{ a: XY; b: XY; target: 'obstacle' | 'plot' } | null>(null);
  const drag = useRef<Drag | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const fittedFor = useRef('');
  // Until the user pans or zooms, the map refits whenever its panel resizes.
  const touched = useRef(false);
  const shown = preview ?? inst;

  const fit = useCallback(() => {
    if (!size.width || !size.height) return;
    touched.current = false;
    const [x0, y0, x1, y1] = boundsOf(inst);
    setView(fitView({ minX: x0, minY: y0, maxX: x1, maxY: y1 }, size.width, size.height, 28));
  }, [inst, size.width, size.height]);
  const fitRef = useRef(fit);
  fitRef.current = fit;

  useEffect(() => {
    if (!size.width || !size.height) return;
    if (fittedFor.current !== fitKey || !touched.current) {
      fittedFor.current = fitKey;
      fitRef.current();
    }
  }, [fitKey, size.width, size.height]);

  useEffect(() => {
    const onFit = () => fit();
    window.addEventListener('studio:fit', onFit);
    return () => window.removeEventListener('studio:fit', onFit);
  }, [fit]);

  // Centre on a point (e.g. an anomaly in a replay), showing about `span` metres across.
  useEffect(() => {
    const onCenter = (e: Event) => {
      const { xy, span = 24 } = (e as CustomEvent<{ xy: XY; span?: number }>).detail ?? {};
      if (!xy || !size.width || !size.height) return;
      touched.current = true;
      setView(fitView({ minX: xy[0] - span / 2, minY: xy[1] - span / 2, maxX: xy[0] + span / 2, maxY: xy[1] + span / 2 }, size.width, size.height, 28));
    };
    window.addEventListener('studio:center', onCenter);
    return () => window.removeEventListener('studio:center', onCenter);
  }, [size.width, size.height]);

  const issues = useMemo(() => taskIssues(shown), [shown]);
  const visibleRoutes = useMemo(() => routes.filter((r) => !hidden.includes(r.vehicle_name)), [routes, hidden]);
  const taskOwner = useMemo(() => vehicleOfTask(visibleRoutes), [visibleRoutes]);
  // Where each task is served when that is not the task point itself (from a lane or the headland).
  const stops = useMemo(() => {
    const at = new Map(inst.tasks.map((t) => [t.id, t.xy] as const));
    return visibleRoutes.flatMap((r) => r.services.flatMap((sv) => {
      const stop = (sv as { stop?: XY }).stop;
      const xy = at.get(sv.task);
      return stop && xy && Math.hypot(stop[0] - xy[0], stop[1] - xy[1]) > 0.05 ? [{ key: `${r.vehicle_name}-${sv.task}`, xy, stop, color: r.color }] : [];
    }));
  }, [visibleRoutes, inst.tasks]);

  const world = (e: { clientX: number; clientY: number }): XY => {
    const rect0 = svg.current!.getBoundingClientRect();
    return toWorld(view, e.clientX - rect0.left, e.clientY - rect0.top);
  };

  function onPointerDown(e: RPointerEvent<SVGSVGElement>) {
    const el = (e.target as Element).closest('[data-hit]') as HTMLElement | SVGElement | null;
    const hit = el?.getAttribute('data-hit') ?? '';
    const id = el?.getAttribute('data-id') ?? '';
    const p = world(e);
    svg.current?.setPointerCapture(e.pointerId);
    const panning = e.button === 1 || tool === 'pan' || (e.button === 0 && e.shiftKey && tool === 'select');
    if (panning) {
      drag.current = { kind: 'pan', sx: e.clientX, sy: e.clientY, view };
      return;
    }
    if (e.button !== 0) return;
    if (tool === 'select' || !editable) {
      if (hit === 'vertex' && editable) {
        const [target, owner, index] = id.split(':');
        drag.current = { kind: 'vertex', target: target as 'obstacle' | 'plot' | 'boundary', id: owner, index: Number(index) };
        return;
      }
      if (hit === 'task') {
        const t = inst.tasks.find((x) => x.id === Number(id));
        onSelect({ type: 'task', id: Number(id) });
        if (t && editable) drag.current = { kind: 'task', id: t.id, from: p, orig: t.xy };
        return;
      }
      if (hit === 'depot') {
        onSelect({ type: 'depot' });
        if (editable) drag.current = { kind: 'depot', from: p, orig: inst.depot };
        return;
      }
      if (hit === 'obstacle' || hit === 'plot') {
        const list = hit === 'obstacle' ? inst.obstacles : inst.plots;
        const item = list.find((x) => x.id === id);
        onSelect(hit === 'obstacle' ? { type: 'obstacle', id } : { type: 'plot', id });
        if (item && editable) drag.current = { kind: 'poly', target: hit, id, from: p, orig: item.polygon };
        return;
      }
      if (hit === 'boundary') {
        onSelect({ type: 'boundary' });
        return;
      }
      onSelect(null);
      drag.current = { kind: 'pan', sx: e.clientX, sy: e.clientY, view };
      return;
    }
    if (tool === 'task') {
      if (!pointInPolygon(p, inst.boundary)) return;
      const nid = Math.max(0, ...inst.tasks.map((t) => t.id)) + 1;
      onEdit((i) => ({ ...i, tasks: [...i.tasks, { id: nid, xy: [round(p[0]), round(p[1])], demand: 1, label: `T${nid}`, plot: null }] }));
      onSelect({ type: 'task', id: nid });
      return;
    }
    if (tool === 'depot') {
      onEdit((i) => ({ ...i, depot: [round(p[0]), round(p[1])] }));
      onSelect({ type: 'depot' });
      return;
    }
    if (tool === 'obstacle' || tool === 'plot') {
      drag.current = { kind: 'shape', target: tool, from: p, to: p };
      setShape({ a: p, b: p, target: tool });
    }
  }

  function onPointerMove(e: RPointerEvent<SVGSVGElement>) {
    const p = world(e);
    onCursor?.(p);
    const d = drag.current;
    if (!d) return;
    if (d.kind === 'pan') {
      touched.current = true;
      setView({ ...d.view, tx: d.view.tx + (e.clientX - d.sx), ty: d.view.ty + (e.clientY - d.sy) });
      return;
    }
    if (d.kind === 'shape') {
      d.to = p;
      setShape({ a: d.from, b: p, target: d.target });
      return;
    }
    const base = preview ?? inst;
    if (d.kind === 'task') {
      const xy: XY = [round(d.orig[0] + p[0] - d.from[0]), round(d.orig[1] + p[1] - d.from[1])];
      setPreview({ ...base, tasks: base.tasks.map((t) => (t.id === d.id ? { ...t, xy } : t)) });
    } else if (d.kind === 'depot') {
      setPreview({ ...base, depot: [round(d.orig[0] + p[0] - d.from[0]), round(d.orig[1] + p[1] - d.from[1])] });
    } else if (d.kind === 'poly') {
      const moved = translate(d.orig, p[0] - d.from[0], p[1] - d.from[1]);
      setPreview(d.target === 'obstacle'
        ? { ...base, obstacles: base.obstacles.map((o) => (o.id === d.id ? { ...o, polygon: moved } : o)) }
        : { ...base, plots: base.plots.map((o) => (o.id === d.id ? { ...o, polygon: moved } : o)) });
    } else if (d.kind === 'vertex') {
      const xy: XY = [round(p[0]), round(p[1])];
      const set = (poly: XY[]) => poly.map((q, i) => (i === d.index ? xy : q));
      if (d.target === 'boundary') setPreview({ ...base, boundary: set(base.boundary) });
      else if (d.target === 'obstacle') setPreview({ ...base, obstacles: base.obstacles.map((o) => (o.id === d.id ? { ...o, polygon: set(o.polygon) } : o)) });
      else setPreview({ ...base, plots: base.plots.map((o) => (o.id === d.id ? { ...o, polygon: set(o.polygon) } : o)) });
    }
  }

  function onPointerUp() {
    const d = drag.current;
    drag.current = null;
    if (!d) return;
    if (d.kind === 'shape') {
      setShape(null);
      const small = Math.hypot(d.to[0] - d.from[0], d.to[1] - d.from[1]) < 0.8;
      const a = small ? ([d.from[0] - 3, d.from[1] - 2] as XY) : d.from;
      const b = small ? ([d.from[0] + 3, d.from[1] + 2] as XY) : d.to;
      if (d.target === 'obstacle') {
        const polygon = obstacleKind === 'tree' && small ? obstacleShape('tree', d.from, [d.from[0] + 1.2, d.from[1]]) : obstacleShape(obstacleKind, a, b);
        let newId = '';
        onEdit((i) => {
          newId = nextObstacleId(i.obstacles);
          return { ...i, obstacles: [...i.obstacles, { id: newId, kind: obstacleKind, name: OBSTACLE_STYLE[obstacleKind].label, polygon }] };
        });
        if (newId) onSelect({ type: 'obstacle', id: newId });
      } else {
        const letter = String.fromCharCode(65 + (inst.plots.length % 26));
        let pid = letter;
        let k = 2;
        while (inst.plots.some((pl) => pl.id === pid)) pid = `${letter}${k++}`;
        onEdit((i) => ({ ...i, plots: [...i.plots, { id: pid, name: `${pid} 区`, crop: '', rows_deg: 0, polygon: rect(a, b) }] }));
        onSelect({ type: 'plot', id: pid });
      }
      return;
    }
    if (d.kind !== 'pan' && preview) {
      const committed = preview;
      setPreview(null);
      onEdit(() => committed);
    }
  }

  function onWheel(e: RWheelEvent<SVGSVGElement>) {
    const rect0 = svg.current!.getBoundingClientRect();
    touched.current = true;
    setView((v) => zoomAt(v, Math.exp(-e.deltaY * 0.0015), e.clientX - rect0.left, e.clientY - rect0.top, 0.05, 400));
  }

  const scr = (p: XY) => toScreen(view, p[0], p[1]);
  const gridStep = GRID_STEPS.find((g) => g * view.k >= 40) ?? 1000;
  const [bx0, by0, bx1, by1] = boundsOf(shown);
  const playbackPos = useMemo(() => {
    if (playback === null) return [];
    return visibleRoutes.map((r) => ({ r, ...along(r.polyline, playback * (inst.vehicles.speed_mps || 1)) }));
  }, [playback, visibleRoutes, inst.vehicles.speed_mps]);

  const selPoly =
    selection?.type === 'obstacle' ? shown.obstacles.find((o) => o.id === selection.id)?.polygon :
    selection?.type === 'plot' ? shown.plots.find((o) => o.id === selection.id)?.polygon :
    selection?.type === 'boundary' ? shown.boundary : undefined;
  const selTarget = selection?.type === 'obstacle' || selection?.type === 'plot' || selection?.type === 'boundary' ? selection.type : null;
  const selId = selection && 'id' in selection ? String(selection.id) : 'boundary';

  return (
    <div ref={box} className={s.editor} data-tool={tool}>
      <svg
        ref={svg}
        className={s.svg}
        width={size.width}
        height={size.height}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={() => onCursor?.(null)}
        onWheel={onWheel}
        role="application"
        aria-label="任务地图编辑器"
      >
        <defs>
          {shown.plots.map((pl) => (
            <pattern key={pl.id} id={`rows-${pl.id}`} width="3" height="3" patternUnits="userSpaceOnUse" patternTransform={`rotate(${pl.rows_deg ?? 0})`}>
              <line x1="0" y1="1.5" x2="3" y2="1.5" className={s.cropRow} />
            </pattern>
          ))}
        </defs>
        <rect className={s.backdrop} width={size.width} height={size.height} />
        <Grid view={view} step={gridStep} width={size.width} height={size.height} />
        <g transform={worldTransform(view)}>
          <polygon data-hit="boundary" className={s.boundary} points={shown.boundary.map((p) => p.join(',')).join(' ')} />
          {background}
          {shown.plots.map((pl) => (
            <g key={pl.id}>
              <polygon className={s.plot} points={pl.polygon.map((p) => p.join(',')).join(' ')} />
              <polygon data-hit="plot" data-id={pl.id} className={s.plotRows} style={{ fill: `url(#rows-${pl.id})` }} points={pl.polygon.map((p) => p.join(',')).join(' ')} />
            </g>
          ))}
          {lanes && lanes.length > 0 && (
            <g className={s.lanes}>
              {lanes.map((ln, i) => <polyline key={i} points={ln.map((p) => p.join(',')).join(' ')} />)}
            </g>
          )}
          {shown.obstacles.map((o) => (
            <polygon
              key={o.id}
              data-hit="obstacle"
              data-id={o.id}
              className={s.obstacle}
              style={{ fill: OBSTACLE_STYLE[o.kind].fill, stroke: OBSTACLE_STYLE[o.kind].stroke }}
              points={o.polygon.map((p) => p.join(',')).join(' ')}
            />
          ))}
          {visibleRoutes.map((r) => (
            <polyline key={r.vehicle_name} className={s.route} style={{ stroke: r.color }} points={r.polyline.map((p) => p.join(',')).join(' ')} />
          ))}
          {stops.map((st) => (
            <line key={st.key} className={s.stopLink} style={{ stroke: st.color }} x1={st.xy[0]} y1={st.xy[1]} x2={st.stop[0]} y2={st.stop[1]} />
          ))}
          {overlay?.(view)}
          {selPoly && <polygon className={s.selected} points={selPoly.map((p) => p.join(',')).join(' ')} />}
        </g>
        {visibleRoutes.map((r) => <Arrows key={r.vehicle_name} poly={r.polyline} view={view} color={r.color} />)}
        {shown.plots.map((pl) => {
          const [cx, cy] = scr(centroid(pl.polygon));
          return (
            <text key={pl.id} x={cx} y={cy} className={s.plotLabel}>
              {pl.name}{pl.crop ? ` · ${pl.crop}` : ''}
            </text>
          );
        })}
        {shape && (() => {
          const poly = shape.target === 'obstacle' ? obstacleShape(obstacleKind, shape.a, shape.b) : rect(shape.a, shape.b);
          return <polygon className={s.rubber} points={poly.map((p) => scr(p).join(',')).join(' ')} />;
        })()}
        {(violations ?? []).map((p, i) => {
          const [x, y] = scr(p);
          return <circle key={i} cx={x} cy={y} r={9} className={s.violation} />;
        })}
        {shown.tasks.map((t) => {
          const [x, y] = scr(t.xy);
          const owner = taskOwner.get(t.id);
          const bad = issues.get(t.id);
          const sel = selection?.type === 'task' && selection.id === t.id;
          return (
            <g key={t.id} data-hit="task" data-id={t.id} className={s.taskG}>
              <title>{`${t.label} · 需求 ${t.demand}${owner ? ` · ${owner.vehicle} 第 ${owner.trip} 趟第 ${owner.order} 站` : ''}${bad ? ` · ${bad}` : ''}`}</title>
              {sel && <circle cx={x} cy={y} r={11} className={s.taskHalo} />}
              <circle cx={x} cy={y} r={owner ? 6.5 : 5.5} className={bad ? s.taskBad : s.task} style={owner ? { stroke: owner.color } : undefined} />
              {owner && view.k > 1.1 && (
                <text x={x} y={y + 3} className={s.order} style={{ fill: owner.color }}>{owner.order}</text>
              )}
              {view.k > 2.2 && <text x={x + 9} y={y - 7} className={s.taskLabel}>{t.label}</text>}
            </g>
          );
        })}
        <Depot xy={scr(shown.depot)} selected={selection?.type === 'depot'} />
        {playbackPos.map(({ r, xy, heading }) => {
          const [x, y] = scr(xy);
          return (
            <g key={r.vehicle_name} transform={`translate(${x} ${y}) rotate(${(-heading * 180) / Math.PI})`} className={s.vehicle}>
              <circle r={9} style={{ fill: r.color }} />
              <path d="M -3 -4 L 5 0 L -3 4 Z" fill="#fff" />
            </g>
          );
        })}
        {selPoly && selTarget && editable &&
          selPoly.map((p, i) => {
            const [x, y] = scr(p);
            return <rect key={i} data-hit="vertex" data-id={`${selTarget}:${selId}:${i}`} x={x - 4.5} y={y - 4.5} width={9} height={9} className={s.vertex} />;
          })}
        <ScaleBar step={gridStep} k={view.k} height={size.height} />
        <text x={size.width - 10} y={size.height - 10} className={s.extent}>{`${(bx1 - bx0).toFixed(0)} × ${(by1 - by0).toFixed(0)} m`}</text>
      </svg>
    </div>
  );
}

function Grid({ view, step, width, height }: { view: View; step: number; width: number; height: number }) {
  const [wx0, wy1] = toWorld(view, 0, 0);
  const [wx1, wy0] = toWorld(view, width, height);
  const xs: number[] = [];
  const ys: number[] = [];
  for (let x = Math.ceil(wx0 / step) * step; x <= wx1 && xs.length < 400; x += step) xs.push(x);
  for (let y = Math.ceil(wy0 / step) * step; y <= wy1 && ys.length < 400; y += step) ys.push(y);
  return (
    <g className={s.grid}>
      {xs.map((x) => {
        const [sx] = toScreen(view, x, 0);
        return <line key={`x${x}`} x1={sx} x2={sx} y1={0} y2={height} />;
      })}
      {ys.map((y) => {
        const [, sy] = toScreen(view, 0, y);
        return <line key={`y${y}`} x1={0} x2={width} y1={sy} y2={sy} />;
      })}
    </g>
  );
}

function ScaleBar({ step, k, height }: { step: number; k: number; height: number }) {
  const w = step * k;
  return (
    <g transform={`translate(14 ${height - 18})`} className={s.scale}>
      <line x1={0} x2={w} y1={0} y2={0} />
      <line x1={0} x2={0} y1={-4} y2={4} />
      <line x1={w} x2={w} y1={-4} y2={4} />
      <text x={w + 6} y={4}>{step} m</text>
    </g>
  );
}

function Depot({ xy, selected }: { xy: XY; selected: boolean }) {
  const [x, y] = xy;
  return (
    <g data-hit="depot" className={s.depot} transform={`translate(${x} ${y})`}>
      <title>车库（所有车辆出发与返回）</title>
      {selected && <circle r={15} className={s.taskHalo} />}
      <rect x={-10} y={-10} width={20} height={20} rx={5} />
      <path d="M -6 1 L 0 -5 L 6 1 M -4 0 L -4 6 L 4 6 L 4 0" />
    </g>
  );
}

function Arrows({ poly, view, color }: { poly: XY[]; view: View; color: string }) {
  const marks: { x: number; y: number; a: number }[] = [];
  let acc = 0;
  for (let i = 1; i < poly.length; i++) {
    const [x0, y0] = toScreen(view, poly[i - 1][0], poly[i - 1][1]);
    const [x1, y1] = toScreen(view, poly[i][0], poly[i][1]);
    const seg = Math.hypot(x1 - x0, y1 - y0);
    let at = 70 - acc;
    while (at < seg) {
      const f = at / seg;
      marks.push({ x: x0 + f * (x1 - x0), y: y0 + f * (y1 - y0), a: (Math.atan2(y1 - y0, x1 - x0) * 180) / Math.PI });
      at += 110;
    }
    acc = (acc + seg) % 110;
    if (marks.length > 300) break;
  }
  return (
    <g style={{ fill: color }} className={s.arrows}>
      {marks.map((m, i) => (
        <path key={i} d="M -4 -3.5 L 4 0 L -4 3.5 Z" transform={`translate(${m.x} ${m.y}) rotate(${m.a})`} />
      ))}
    </g>
  );
}
