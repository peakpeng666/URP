import type { ButtonHTMLAttributes, ReactNode, SelectHTMLAttributes, InputHTMLAttributes } from 'react';
import { useId } from 'react';
import { CircleAlert, CircleCheck, Info, LoaderCircle, TriangleAlert, type LucideIcon } from 'lucide-react';
import type { ServiceState } from '../types';
import s from './mac.module.css';

const cx = (...names: (string | false | null | undefined)[]) => names.filter(Boolean).join(' ');

/* ------------------------------------------------------------- Button -- */
export function Button({
  variant = 'secondary',
  size = 'md',
  icon: Icon,
  loading = false,
  children,
  className,
  ...rest
}: {
  variant?: 'primary' | 'secondary' | 'plain' | 'destructive';
  size?: 'sm' | 'md' | 'lg';
  icon?: LucideIcon;
  loading?: boolean;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const iconSize = size === 'sm' ? 13 : 15;
  return (
    <button
      type="button"
      {...rest}
      disabled={rest.disabled || loading}
      aria-busy={loading || undefined}
      className={cx(
        s.button,
        size !== 'md' && s[size],
        variant !== 'secondary' && s[variant],
        !children && s.iconOnly,
        className,
      )}
    >
      {loading ? (
        <LoaderCircle size={iconSize} className={s.spin} aria-hidden />
      ) : (
        Icon && <Icon size={iconSize} strokeWidth={1.9} aria-hidden />
      )}
      {children}
    </button>
  );
}

/* ---------------------------------------------------------- Segmented -- */
export function Segmented<T extends string>({
  value,
  options,
  onChange,
  full = false,
  label,
}: {
  value: T;
  options: { value: T; label: ReactNode; icon?: LucideIcon; disabled?: boolean; title?: string }[];
  onChange: (value: T) => void;
  full?: boolean;
  label?: string;
}) {
  return (
    <div className={cx(s.segmented, full && s.segmentedFull)} role="group" aria-label={label}>
      {options.map((o) => {
        const Icon = o.icon;
        return (
          <button
            key={o.value}
            type="button"
            className={s.segment}
            aria-pressed={o.value === value}
            disabled={o.disabled}
            title={o.title}
            onClick={() => onChange(o.value)}
          >
            {Icon && <Icon size={13} strokeWidth={1.9} aria-hidden />}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------- Switch -- */
export function Switch({
  checked,
  onChange,
  label,
  disabled,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: ReactNode;
  disabled?: boolean;
}) {
  return (
    <label className={s.switchRow}>
      <input
        type="checkbox"
        role="switch"
        className={s.switchInput}
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      <span className={s.switchTrack} aria-hidden />
      {label && <span>{label}</span>}
    </label>
  );
}

/* ------------------------------------------------------------- Status -- */
export type Tone = 'ok' | 'warn' | 'error' | 'idle' | 'busy';

export function serviceTone(state: ServiceState | string): Tone {
  switch (state) {
    case 'running':
    case 'ready':
      return 'ok';
    case 'starting':
    case 'stopping':
      return 'busy';
    case 'degraded':
      return 'warn';
    case 'failed':
      return 'error';
    default:
      return 'idle';
  }
}

export const SERVICE_STATE_LABEL: Record<string, string> = {
  running: '运行中',
  ready: '就绪',
  stopped: '未运行',
  starting: '启动中',
  stopping: '停止中',
  degraded: '降级',
  failed: '失败',
  unavailable: '不可用',
};

export function StatusDot({ tone, title }: { tone: Tone; title?: string }) {
  return <span className={cx(s.dot, s[`dot_${tone}`])} title={title} aria-hidden={!title} role={title ? 'img' : undefined} aria-label={title} />;
}

export function StatusText({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span className={s.statusText}>
      <StatusDot tone={tone} />
      {children}
    </span>
  );
}

export function Badge({
  tone = 'gray',
  children,
  title,
}: {
  tone?: 'blue' | 'green' | 'orange' | 'red' | 'purple' | 'teal' | 'gray';
  children: ReactNode;
  title?: string;
}) {
  return (
    <span className={cx(s.badge, s[`tone_${tone}`])} title={title}>
      {children}
    </span>
  );
}

/** Source badge: keeps project / third-party / baseline / Nav2 visually distinct. */
export function SourceBadge({ source }: { source: string }) {
  const map: Record<string, { tone: 'blue' | 'purple' | 'gray' | 'orange'; text: string }> = {
    project: { tone: 'blue', text: '本项目' },
    third_party: { tone: 'purple', text: '第三方' },
    panel_baseline: { tone: 'gray', text: '面板基线' },
    nav2: { tone: 'orange', text: 'Nav2' },
  };
  const m = map[source] ?? { tone: 'gray' as const, text: source };
  return <Badge tone={m.tone}>{m.text}</Badge>;
}

/* --------------------------------------------------------------- Card -- */
export function Card({
  title,
  subtitle,
  actions,
  children,
  flush = false,
  className,
  id,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
  flush?: boolean;
  className?: string;
  id?: string;
}) {
  return (
    <section className={cx(s.card, className)} id={id}>
      {(title || actions) && (
        <header className={s.cardHead}>
          <div style={{ minWidth: 0 }}>
            {title && <h2 className={s.cardTitle}>{title}</h2>}
            {subtitle && <p className={s.cardSub}>{subtitle}</p>}
          </div>
          {actions && <div className={s.cardActions}>{actions}</div>}
        </header>
      )}
      {children !== undefined && <div className={flush ? s.cardFlush : s.cardBody}>{children}</div>}
    </section>
  );
}

/* ------------------------------------------------------ Grouped lists -- */
export function Group({ title, footer, children }: { title?: ReactNode; footer?: ReactNode; children: ReactNode }) {
  return (
    <div className={s.group}>
      {title && <h3 className={s.groupTitle}>{title}</h3>}
      <div className={s.groupBox}>{children}</div>
      {footer && <p className={s.groupFooter}>{footer}</p>}
    </div>
  );
}

export function Row({
  label,
  detail,
  value,
  leading,
  children,
}: {
  label: ReactNode;
  detail?: ReactNode;
  value?: ReactNode;
  leading?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className={s.row}>
      {leading}
      <div className={s.rowLabel}>
        <div className={s.rowLabelMain}>{label}</div>
        {detail && <div className={s.rowDetail}>{detail}</div>}
      </div>
      {value !== undefined && <div className={s.rowValue}>{value}</div>}
      {children}
    </div>
  );
}

/* ------------------------------------------------------------- Fields -- */
export function Field({ label, hint, children }: { label: ReactNode; hint?: ReactNode; children: (id: string) => ReactNode }) {
  const id = useId();
  return (
    <div className={s.field}>
      <label className={s.fieldLabel} htmlFor={id}>
        {label}
      </label>
      {children(id)}
      {hint && <span className={s.fieldHint}>{hint}</span>}
    </div>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cx(s.input, props.className)} />;
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cx(s.select, props.className)} />;
}

/* ------------------------------------------------------------ Toolbar -- */
export function Toolbar({ title, subtitle, children }: { title: ReactNode; subtitle?: ReactNode; children?: ReactNode }) {
  return (
    <div className={s.toolbar}>
      <div className={s.toolbarTitle}>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

/* -------------------------------------------------------------- Empty -- */
export function EmptyState({
  icon: Icon,
  title,
  detail,
  action,
}: {
  icon?: LucideIcon;
  title: ReactNode;
  detail?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className={s.empty}>
      {Icon && <Icon size={30} strokeWidth={1.4} className={s.emptyIcon} aria-hidden />}
      <p className={s.emptyTitle}>{title}</p>
      {detail && <p className={s.emptyDetail}>{detail}</p>}
      {action}
    </div>
  );
}

/* ------------------------------------------------------------- Notice -- */
export function Notice({ tone = 'info', children }: { tone?: 'info' | 'warn' | 'error' | 'ok'; children: ReactNode }) {
  const Icon = { info: Info, warn: TriangleAlert, error: CircleAlert, ok: CircleCheck }[tone];
  return (
    <div className={cx(s.notice, s[`notice_${tone}`])} role={tone === 'error' ? 'alert' : 'note'}>
      <Icon size={14} className={s.noticeIcon} aria-hidden />
      <div>{children}</div>
    </div>
  );
}

/* ------------------------------------------------------------- Metric -- */
export function Metric({ label, value, unit, title }: { label: ReactNode; value: ReactNode; unit?: ReactNode; title?: string }) {
  return (
    <div className={s.metric} title={title}>
      <span className={s.metricLabel}>{label}</span>
      <span className={s.metricValue}>
        {value}
        {unit && <span className={s.metricUnit}>{unit}</span>}
      </span>
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return <span className={s.spinner} role="status" aria-label={label ?? '载入中'} />;
}

/** Class names for tables so views share the same macOS list look. */
export const tableClass = s.table;
