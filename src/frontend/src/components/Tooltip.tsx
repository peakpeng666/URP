import { useCallback, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import s from './Tooltip.module.css';

interface Pos {
  x: number;
  y: number;
  content: ReactNode;
}

/**
 * Lightweight pointer-follow tooltip layer for a chart. The chart calls show()
 * on hover/focus with client coordinates; the layer clamps to the viewport.
 */
export function useTooltip() {
  const [pos, setPos] = useState<Pos | null>(null);
  const show = useCallback((x: number, y: number, content: ReactNode) => setPos({ x, y, content }), []);
  const hide = useCallback(() => setPos(null), []);
  return { pos, show, hide };
}

export function TooltipLayer({ pos }: { pos: Pos | null }) {
  const ref = useRef<HTMLDivElement>(null);
  const [offset, setOffset] = useState({ dx: 12, dy: 12 });

  useLayoutEffect(() => {
    if (!pos || !ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    let dx = 12;
    let dy = 12;
    if (pos.x + 12 + rect.width > window.innerWidth) dx = -rect.width - 12;
    if (pos.y + 12 + rect.height > window.innerHeight) dy = -rect.height - 12;
    setOffset({ dx, dy });
  }, [pos]);

  if (!pos) return null;
  return (
    <div
      ref={ref}
      className={s.tip}
      role="tooltip"
      style={{ left: pos.x + offset.dx, top: pos.y + offset.dy }}
    >
      {pos.content}
    </div>
  );
}
