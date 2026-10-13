import { useId, useMemo } from 'react';
import { scaleLinear } from 'd3-scale';
import type { MeanBins } from '../data/types';
import { fmt } from '../lib/format';
import { niceTicks, pad } from './axes';
import { useTooltip, TooltipLayer } from '../components/Tooltip';
import s from './charts.module.css';

/**
 * Confirmation-set mean final bins per role, as a dot plot on a non-zero axis.
 * A dot plot (not bars) is deliberate: the spread is tiny relative to the
 * absolute count (~2730–2794 of ~2757), so a zero-based bar would hide it and a
 * truncated bar would exaggerate it — the same reason the original figure uses
 * dots. The axis start is labeled so the non-zero baseline is explicit.
 */
interface Row {
  key: keyof MeanBins;
  label: string;
  detail: string;
  color: string;
  shape: 'disc' | 'ring' | 'diamond';
  emphasis?: boolean;
}

const ROWS: Row[] = [
  { key: 'SELECTOR', label: '前缀选择器', detail: '只看前 500 项后选一次', color: 'var(--sel)', shape: 'disc', emphasis: true },
  { key: 'SBS', label: '训练 SBS（= BF→EoH）', detail: '训练选出的基线分支', color: 'var(--eoh)', shape: 'disc' },
  { key: 'BF', label: '全程 BF', detail: '另一条可执行分支', color: 'var(--bf)', shape: 'disc' },
  { key: 'branch_oracle', label: '同前缀分支 oracle', detail: '事后在两分支里取优，不可部署', color: 'var(--ink-3)', shape: 'ring' },
  { key: 'published_EoH', label: '全程 EoH', detail: '起点状态不同的固定基线', color: 'var(--full-eoh)', shape: 'diamond' },
];

export function MeanBinsDotPlot({ mean }: { mean: MeanBins }) {
  const titleId = useId();
  const { pos, show, hide } = useTooltip();
  const rows = ROWS.map((r) => ({ ...r, value: mean[r.key] }));

  const { scale, ticks, width } = useMemo(() => {
    const values = rows.map((r) => r.value);
    const domain = pad([Math.min(...values), Math.max(...values)], 0.12);
    const w = 560;
    return {
      width: w,
      scale: scaleLinear().domain(domain).range([0, w]),
      ticks: niceTicks(domain[0], domain[1], 5),
    };
  }, [rows]);

  const rowH = 46;
  const labelW = 190;
  const height = rows.length * rowH;

  return (
    <figure className={s.figure} aria-labelledby={titleId}>
      <figcaption id={titleId} className="visually-hidden">
        确认集 108 流各角色平均最终箱数，越少越好。
      </figcaption>
      <div className={s.scrollX}>
        <svg
          className={s.svg}
          viewBox={`0 0 ${labelW + width + 70} ${height + 44}`}
          role="img"
          style={{ minWidth: 640 }}
        >
          <g transform={`translate(${labelW}, 8)`}>
            {ticks.map((t) => (
              <g key={t} transform={`translate(${scale(t)}, 0)`}>
                <line y1={0} y2={height} className={s.grid} />
                <text y={height + 18} className={s.tickX} textAnchor="middle">
                  {fmt(t, 0)}
                </text>
              </g>
            ))}
            <text y={height + 36} x={width / 2} className={s.axisTitle} textAnchor="middle">
              平均最终箱数（越少越好）
            </text>

            {rows.map((r, i) => {
              const cy = i * rowH + rowH / 2;
              const cx = scale(r.value);
              return (
                <g
                  key={r.key}
                  transform={`translate(0, ${cy})`}
                  tabIndex={0}
                  role="listitem"
                  aria-label={`${r.label}：平均 ${fmt(r.value, 3)} 箱`}
                  className={s.rowHit}
                  onMouseMove={(e) => show(e.clientX, e.clientY, <TipRow label={r.label} detail={r.detail} value={r.value} />)}
                  onMouseLeave={hide}
                  onFocus={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    show(rect.right, rect.top, <TipRow label={r.label} detail={r.detail} value={r.value} />);
                  }}
                  onBlur={hide}
                >
                  <line x1={0} x2={width} className={s.rowRule} />
                  <Mark shape={r.shape} color={r.color} x={cx} emphasis={r.emphasis} />
                  <text x={cx} y={-14} className={`${s.dotValue} num`} textAnchor="middle">
                    {fmt(r.value, 3)}
                  </text>
                </g>
              );
            })}
          </g>

          {rows.map((r, i) => (
            <g key={r.key} transform={`translate(0, ${8 + i * rowH + rowH / 2})`}>
              <text x={labelW - 14} y={-2} className={s.rowLabel} textAnchor="end">
                {r.label}
              </text>
              <text x={labelW - 14} y={13} className={s.rowDetail} textAnchor="end">
                {r.detail}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <TooltipLayer pos={pos} />
    </figure>
  );
}

function Mark({ shape, color, x, emphasis }: { shape: Row['shape']; color: string; x: number; emphasis?: boolean }) {
  const r = emphasis ? 8 : 6.5;
  if (shape === 'ring') return <circle cx={x} cy={0} r={r} fill="var(--panel)" stroke={color} strokeWidth={2.4} />;
  if (shape === 'diamond') {
    return (
      <path
        d={`M${x} ${-r} L${x + r} 0 L${x} ${r} L${x - r} 0 Z`}
        fill="var(--panel)"
        stroke={color}
        strokeWidth={2.2}
      />
    );
  }
  return (
    <circle cx={x} cy={0} r={r} fill={color} stroke="var(--panel)" strokeWidth={emphasis ? 2.5 : 0} />
  );
}

function TipRow({ label, detail, value }: { label: string; detail: string; value: number }) {
  return (
    <div>
      <div>
        <span className="v">{fmt(value, 3)}</span> 箱
      </div>
      <div className="k">
        {label} · {detail}
      </div>
    </div>
  );
}
