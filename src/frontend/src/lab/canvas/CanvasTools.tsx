import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { ChevronDown, type LucideIcon } from 'lucide-react';
import { Switch } from '../ui';
import { LAYER_LABELS, type LayerKey } from './types';
import t from './tools.module.css';

/** Glass toolbar button that opens a popover panel below it. */
export function Popover({ icon: Icon, label, children, width = 260 }: { icon?: LucideIcon; label: string; children: ReactNode; width?: number }) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const id = useId();
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('pointerdown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('pointerdown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);
  return (
    <div className={t.pop} ref={root}>
      <button type="button" className={t.tool} aria-expanded={open} aria-controls={id} onClick={() => setOpen((o) => !o)}>
        {Icon && <Icon size={14} strokeWidth={1.9} aria-hidden />}
        {label}
        <ChevronDown size={12} aria-hidden className={t.caret} />
      </button>
      {open && (
        <div id={id} className={t.panel} style={{ width }} role="dialog" aria-label={label}>
          {children}
        </div>
      )}
    </div>
  );
}

export function ToolButton({ icon: Icon, children, onClick, title, pressed }: { icon?: LucideIcon; children?: ReactNode; onClick: () => void; title?: string; pressed?: boolean }) {
  return (
    <button type="button" className={t.tool} onClick={onClick} title={title} aria-pressed={pressed}>
      {Icon && <Icon size={14} strokeWidth={1.9} aria-hidden />}
      {children}
    </button>
  );
}

export function ToolChip({ tone = 'info', children }: { tone?: 'info' | 'warn' | 'edit'; children: ReactNode }) {
  return <div className={`${t.chip} ${t[`chip_${tone}`]}`}>{children}</div>;
}

export function LayerMenu({
  keys,
  layers,
  onChange,
}: {
  keys: LayerKey[];
  layers: Record<LayerKey, boolean>;
  onChange: (key: LayerKey, on: boolean) => void;
}) {
  return (
    <div className={t.layerList}>
      {keys.map((k) => (
        <Switch key={k} checked={layers[k]} onChange={(on) => onChange(k, on)} label={LAYER_LABELS[k]} />
      ))}
    </div>
  );
}

/** One legend line: a small glyph followed by text. */
export function LegendItem({ glyph, children }: { glyph: ReactNode; children: ReactNode }) {
  return (
    <div className={t.legendItem}>
      <svg width={26} height={14} aria-hidden className={t.legendGlyph}>
        {glyph}
      </svg>
      <div>{children}</div>
    </div>
  );
}

export const LegendLine = ({ color, dash, width = 2.5 }: { color: string; dash?: string; width?: number }) => (
  <path d="M2 7H24" style={{ stroke: color }} strokeWidth={width} strokeDasharray={dash} strokeLinecap="round" fill="none" />
);

export function LegendTitle({ children }: { children: ReactNode }) {
  return <div className={t.legendTitle}>{children}</div>;
}
