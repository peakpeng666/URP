/** Pan / zoom SVG view in map coordinates (metres, y up) with a metre grid, origin axes and a cursor readout. */
import { useEffect, useRef, useState, type PointerEvent as RPointerEvent, type ReactNode } from 'react';
import { useElementSize } from '../../lib/useElementSize';
import { fitView, toScreen, toWorld, worldTransform, zoomAt, type View } from '../../lab/canvas/view';
import type { XY } from '../../lab/types';
import s from './assets.module.css';

const STEPS = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000];

export function MapView2D({ bounds, children, onClick, cursorExtra, fitKey, overlay }: {
  bounds: [number, number, number, number] | null; children: (view: View) => ReactNode; onClick?: (p: XY) => void;
  cursorExtra?: (p: XY) => string; fitKey: string; overlay?: ReactNode;
}) {
  const [box, size] = useElementSize<HTMLDivElement>();
  const [view, setView] = useState<View>({ k: 1, tx: 0, ty: 0 });
  const [cursor, setCursor] = useState<XY | null>(null);
  const drag = useRef<{ x: number; y: number; view: View; moved: boolean } | null>(null);
  const fitted = useRef('');
  useEffect(() => {
    if (!size.width || !size.height || !bounds) return;
    if (fitted.current === fitKey) return;
    fitted.current = fitKey;
    setView(fitView({ minX: bounds[0], minY: bounds[1], maxX: bounds[2], maxY: bounds[3] }, size.width, size.height, 30));
  }, [bounds, size.width, size.height, fitKey]);
  const local = (e: { clientX: number; clientY: number }) => {
    const r = box.current!.getBoundingClientRect();
    return [e.clientX - r.left, e.clientY - r.top] as XY;
  };
  const step = STEPS.find((st) => st * view.k >= 46) ?? 1000;
  const [x0, y1] = toWorld(view, 0, 0);
  const [x1, y0] = toWorld(view, size.width, size.height);
  const lines: ReactNode[] = [];
  if (size.width && view.k > 0) {
    for (let x = Math.ceil(x0 / step) * step; x <= x1; x += step) {
      const [sx] = toScreen(view, x, 0);
      lines.push(<line key={`x${x}`} x1={sx} x2={sx} y1={0} y2={size.height} stroke={Math.abs(x) < 1e-9 ? '#9aa1ad' : '#dfe3e8'} />);
    }
    for (let y = Math.ceil(y0 / step) * step; y <= y1; y += step) {
      const [, sy] = toScreen(view, 0, y);
      lines.push(<line key={`y${y}`} x1={0} x2={size.width} y1={sy} y2={sy} stroke={Math.abs(y) < 1e-9 ? '#9aa1ad' : '#dfe3e8'} />);
    }
  }
  const [ox, oy] = toScreen(view, 0, 0);
  return (
    <div ref={box} className={s.preview}>
      <svg className={s.previewSvg} width={size.width} height={size.height}
        onWheel={(e) => { const [sx, sy] = local(e); setView((v) => zoomAt(v, Math.exp(-e.deltaY * 0.0015), sx, sy, 1e-4, 4000)); }}
        onPointerDown={(e: RPointerEvent) => { (e.target as Element).setPointerCapture?.(e.pointerId); drag.current = { x: e.clientX, y: e.clientY, view, moved: false }; }}
        onPointerMove={(e) => {
          const [sx, sy] = local(e);
          setCursor(toWorld(view, sx, sy));
          const d = drag.current;
          if (!d) return;
          if (Math.hypot(e.clientX - d.x, e.clientY - d.y) > 3) d.moved = true;
          if (d.moved) setView({ ...d.view, tx: d.view.tx + e.clientX - d.x, ty: d.view.ty + e.clientY - d.y });
        }}
        onPointerUp={(e) => {
          const d = drag.current;
          drag.current = null;
          if (d && !d.moved && onClick) {
            const [sx, sy] = local(e);
            onClick(toWorld(view, sx, sy));
          }
        }}
        onPointerLeave={() => setCursor(null)}>
        {lines}
        <g transform={worldTransform(view)}>{children(view)}</g>
        <g>
          <line x1={ox} y1={oy} x2={ox + 40} y2={oy} stroke="#ff3b30" strokeWidth={2} />
          <line x1={ox} y1={oy} x2={ox} y2={oy - 40} stroke="#30b158" strokeWidth={2} />
          <text x={ox + 42} y={oy + 4} fontSize={10} fill="#ff3b30">x</text>
          <text x={ox - 3} y={oy - 44} fontSize={10} fill="#30b158">y</text>
        </g>
      </svg>
      {overlay && <div className={s.overlay}>{overlay}</div>}
      <div className={`${s.bottomLeft} ${s.glass}`} style={{ fontSize: 11 }}>网格 {step} m</div>
      {cursor && <div className={`${s.bottomRight} ${s.glass}`}>x {cursor[0].toFixed(2)} m, y {cursor[1].toFixed(2)} m{cursorExtra ? ` · ${cursorExtra(cursor)}` : ''}</div>}
    </div>
  );
}
