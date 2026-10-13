import { useId, useMemo } from 'react';
import { scaleLinear } from 'd3-scale';
import type { StreamResults } from '../data/types';
import { streamTitle } from '../data/labels';
import { fmtSigned, deltaWord } from '../lib/format';
import { niceTicks, pad } from './axes';
import { useTooltip, TooltipLayer } from '../components/Tooltip';
import { navigate, buildHash } from '../app/router';
import s from './charts.module.css';

/**
 * Per-stream selector−SBS for the confirmation set as a beeswarm-ish strip:
 * each stream is one dot, negative = savings (left/green). Clicking a dot opens
 * that stream's replay at the decision point. Diverging color + sign, with a
 * neutral zero line.
 */
export function DeltaStrip({ rows }: { rows: StreamResults[] }) {
  const titleId = useId();
  const { pos, show, hide } = useTooltip();
  const width = 680;
  const radius = 4;
  const margin = { top: 16, right: 20, bottom: 36, left: 20 };
  const plotW = width - margin.left - margin.right;

  const { scale, ticks, dots, plotH, height } = useMemo(() => {
    const deltas = rows.map((r) => r.selector_minus_SBS ?? 0);
    const domain = pad([Math.min(...deltas, 0), Math.max(...deltas, 0)], 0.08);
    const sc = scaleLinear().domain(domain).range([0, plotW]);
    const bucket = radius * 2 + 1;
    // First pass: how many dots land in the densest x-bucket.
    const counts = new Map<number, number>();
    const assigned = rows
      .map((r) => ({ r, x: sc(r.selector_minus_SBS ?? 0) }))
      .sort((a, b) => a.x - b.x)
      .map(({ r, x }) => {
        const bin = Math.round(x / bucket);
        const n = counts.get(bin) ?? 0;
        counts.set(bin, n + 1);
        return { r, x, bin, n };
      });
    const maxCount = Math.max(1, ...counts.values());
    // Spacing so even the densest column (56 ties at Δ=0) fits inside the plot.
    const spacing = Math.min(bucket, 150 / maxCount);
    const half = ((maxCount - 1) / 2) * spacing;
    const ph = Math.max(90, half * 2 + radius * 2 + 12);
    const placed = assigned.map(({ r, x, n }) => {
      const row = n % 2 === 0 ? n / 2 : -(n + 1) / 2;
      return { r, x, y: ph / 2 + row * spacing };
    });
    return {
      scale: sc,
      ticks: niceTicks(domain[0], domain[1], 6),
      dots: placed,
      plotH: ph,
      height: ph + margin.top + margin.bottom,
    };
  }, [rows, plotW]);

  return (
    <figure className={s.figure} aria-labelledby={titleId}>
      <figcaption id={titleId} className="visually-hidden">
        108 条确认流的选择器减训练 SBS 箱数分布，负数在左表示节省。点击圆点打开该流回放。
      </figcaption>
      <div className={s.scrollX}>
        <svg className={s.svg} viewBox={`0 0 ${width} ${height}`} role="img" style={{ minWidth: 560 }}>
          <g transform={`translate(${margin.left}, ${margin.top})`}>
            {ticks.map((t) => (
              <g key={t} transform={`translate(${scale(t)}, 0)`}>
                <line y1={0} y2={plotH} className={t === 0 ? s.zeroLine : s.grid} />
                <text y={plotH + 16} className={s.tickX} textAnchor="middle">
                  {fmtSigned(t, 0)}
                </text>
              </g>
            ))}
            <text y={plotH + 32} x={plotW / 2} className={s.axisTitle} textAnchor="middle">
              选择器 − 训练 SBS（箱）· 左侧节省，右侧变差
            </text>
            {dots.map(({ r, x, y }) => {
              const delta = r.selector_minus_SBS ?? 0;
              const color = delta < 0 ? 'var(--save)' : delta > 0 ? 'var(--harm)' : 'var(--ink-4)';
              return (
                <circle
                  key={r.instance_id}
                  cx={x}
                  cy={y}
                  r={radius}
                  fill={color}
                  fillOpacity={0.82}
                  stroke="var(--panel)"
                  strokeWidth={1}
                  className={s.clickDot}
                  tabIndex={0}
                  role="button"
                  aria-label={`${streamTitle(r)}：${deltaWord(delta)}，打开回放`}
                  onClick={() => navigate(buildHash('replay', r.instance_id, { a: 'SELECTOR', b: 'SBS', view: 'observed', t: 500 }))}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      navigate(buildHash('replay', r.instance_id, { a: 'SELECTOR', b: 'SBS', view: 'observed', t: 500 }));
                    }
                  }}
                  onMouseMove={(e) => show(e.clientX, e.clientY, <Tip r={r} delta={delta} />)}
                  onMouseLeave={hide}
                  onFocus={(e) => {
                    const rect = (e.currentTarget as SVGCircleElement).getBoundingClientRect();
                    show(rect.right, rect.top, <Tip r={r} delta={delta} />);
                  }}
                  onBlur={hide}
                />
              );
            })}
          </g>
        </svg>
      </div>
      <TooltipLayer pos={pos} />
    </figure>
  );
}

function Tip({ r, delta }: { r: StreamResults; delta: number }) {
  return (
    <div>
      <div>
        <span className="v">{fmtSigned(delta, 0)}</span> 箱（{deltaWord(delta)}）
      </div>
      <div className="k">{streamTitle(r)}</div>
      <div className="k">点击打开回放（选择器 vs SBS）</div>
    </div>
  );
}
