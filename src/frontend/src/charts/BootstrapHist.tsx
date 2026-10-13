import { useId, useMemo } from 'react';
import { scaleLinear } from 'd3-scale';
import { fmt, fmtSigned } from '../lib/format';
import { niceTicks } from './axes';
import { useTooltip, TooltipLayer } from '../components/Tooltip';
import s from './charts.module.css';

/**
 * Histogram of the 10,000 cluster-bootstrap mean deltas (decoded from
 * cluster_bootstrap.npz in the browser), with the recorded 95% percentile
 * interval and the point estimate marked. Sequential one-hue bars.
 */
export function BootstrapHist({
  samples,
  ci,
  point,
  bins = 48,
}: {
  samples: Float64Array;
  ci: [number, number];
  point: number;
  bins?: number;
}) {
  const titleId = useId();
  const { pos, show, hide } = useTooltip();
  const width = 680;
  const height = 220;
  const margin = { top: 16, right: 18, bottom: 40, left: 44 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;

  const { bars, x, y, ticks, lo, hi } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    for (const v of samples) {
      if (v < min) min = v;
      if (v > max) max = v;
    }
    const span = max - min || 1;
    min -= span * 0.02;
    max += span * 0.02;
    const width1 = (max - min) / bins;
    const counts = new Array<number>(bins).fill(0);
    for (const v of samples) {
      const idx = Math.min(bins - 1, Math.floor((v - min) / width1));
      counts[idx] += 1;
    }
    const xs = scaleLinear().domain([min, max]).range([0, plotW]);
    const ys = scaleLinear()
      .domain([0, Math.max(...counts)])
      .range([plotH, 0]);
    return {
      bars: counts.map((c, i) => ({ c, x0: min + i * width1, x1: min + (i + 1) * width1 })),
      x: xs,
      y: ys,
      ticks: niceTicks(min, max, 6),
      lo: min,
      hi: max,
    };
  }, [samples, bins, plotW, plotH]);

  return (
    <figure className={s.figure} aria-labelledby={titleId}>
      <figcaption id={titleId} className="visually-hidden">
        10000 次族内多重集组自助重抽样得到的平均选择器减 SBS 分布，含 95% 百分位区间。
      </figcaption>
      <div className={s.scrollX}>
        <svg className={s.svg} viewBox={`0 0 ${width} ${height}`} role="img" style={{ minWidth: 560 }}>
          <g transform={`translate(${margin.left}, ${margin.top})`}>
            {y.ticks(4).map((t) => (
              <g key={t} transform={`translate(0, ${y(t)})`}>
                <line x1={0} x2={plotW} className={s.grid} />
                <text x={-8} y={4} className={s.tickY} textAnchor="end">
                  {fmt(t, 0)}
                </text>
              </g>
            ))}

            {/* CI band */}
            <rect
              x={x(Math.max(lo, ci[0]))}
              y={0}
              width={Math.max(0, x(Math.min(hi, ci[1])) - x(Math.max(lo, ci[0])))}
              height={plotH}
              fill="var(--bf-wash)"
            />

            {bars.map((b, i) => {
              const bx = x(b.x0);
              const bw = Math.max(0.5, x(b.x1) - x(b.x0) - 2);
              const bh = plotH - y(b.c);
              return (
                <rect
                  key={i}
                  x={bx}
                  y={y(b.c)}
                  width={bw}
                  height={bh}
                  rx={1.5}
                  fill="var(--bf)"
                  fillOpacity={0.78}
                  onMouseMove={(e) =>
                    show(
                      e.clientX,
                      e.clientY,
                      <div>
                        <div>
                          <span className="v">{b.c}</span> 次重抽样
                        </div>
                        <div className="k">
                          {fmtSigned(b.x0, 1)} … {fmtSigned(b.x1, 1)} 箱
                        </div>
                      </div>,
                    )
                  }
                  onMouseLeave={hide}
                />
              );
            })}

            {[ci[0], ci[1]].map((v, i) => (
              <g key={i} transform={`translate(${x(v)}, 0)`}>
                <line y1={0} y2={plotH} className={s.zeroLine} />
                <text y={plotH + 26} className={`${s.tickX}`} textAnchor="middle">
                  {fmt(v, 2)}
                </text>
              </g>
            ))}
            <g transform={`translate(${x(point)}, 0)`}>
              <line y1={-4} y2={plotH} stroke="var(--ink)" strokeWidth={2} />
              <circle cy={-4} r={3.5} fill="var(--ink)" />
            </g>

            {ticks.map((t) => (
              <text key={t} x={x(t)} y={plotH + 14} className={s.tickX} textAnchor="middle">
                {fmtSigned(t, 0)}
              </text>
            ))}
            <text x={plotW / 2} y={plotH + 38} className={s.axisTitle} textAnchor="middle">
              重抽样平均（选择器 − SBS，箱）· 竖线为 95% 百分位区间，黑线为点估计
            </text>
          </g>
        </svg>
      </div>
      <TooltipLayer pos={pos} />
    </figure>
  );
}
