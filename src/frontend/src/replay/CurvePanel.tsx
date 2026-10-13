import { useId, useMemo } from 'react';
import { scaleLinear } from 'd3-scale';
import { fmt, fmtSigned } from '../lib/format';
import { niceTicks } from '../charts/axes';
import s from './CurvePanel.module.css';

/**
 * Cumulative used-bins curve (single run) or the running A−B difference (two
 * runs). Observed mode draws only up to the current t; retrospective draws the
 * full recorded curve. Point 0 is the empty initial state.
 */
export function CurvePanel({
  curveA,
  curveB,
  labelA,
  labelB,
  colorA,
  colorB,
  t,
  total,
  boundary,
  retrospective,
  sharedPrefix,
}: {
  curveA: Int32Array;
  curveB: Int32Array | null;
  labelA: string;
  labelB: string | null;
  colorA: string;
  colorB: string;
  t: number;
  total: number;
  boundary: number;
  retrospective: boolean;
  /** Both runs share the BF prefix (true only for BF/BF_then_EoH/SELECTOR pairs). */
  sharedPrefix: boolean;
}) {
  const titleId = useId();
  const comparing = curveB !== null;
  const width = 640;
  const height = 210;
  const margin = { top: 14, right: 16, bottom: 34, left: 52 };
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const visibleEnd = retrospective ? total : t;

  const { x, y, pathA, pathB, pathDelta, yTicks, zeroY } = useMemo(() => {
    const xs = scaleLinear().domain([0, total]).range([0, plotW]);
    const step = Math.max(1, Math.floor(total / 900));
    const at = (arr: Int32Array, i: number) => (i <= 0 ? 0 : arr[i - 1]);
    // Axis bounds inspect every known point, including the current endpoint
    // and short-lived differences between sampled drawing points. Only path
    // drawing is sampled. Observed mode never scans beyond visibleEnd.

    if (comparing && curveB) {
      let lo = 0;
      let hi = 0;
      for (let i = 0; i <= visibleEnd; i += 1) {
        const d = at(curveA, i) - at(curveB, i);
        if (d < lo) lo = d;
        if (d > hi) hi = d;
      }
      if (hi - lo < 4) {
        hi += 2;
        lo -= 2;
      }
      const ys = scaleLinear().domain([lo - 1, hi + 1]).range([plotH, 0]);
      let d = '';
      for (let i = 0; i <= visibleEnd; i += step) {
        d += `${i === 0 ? 'M' : 'L'}${xs(i).toFixed(1)} ${ys(at(curveA, i) - at(curveB, i)).toFixed(1)}`;
      }
      if (visibleEnd % step !== 0) d += `L${xs(visibleEnd).toFixed(1)} ${ys(at(curveA, visibleEnd) - at(curveB, visibleEnd)).toFixed(1)}`;
      return { x: xs, y: ys, pathA: '', pathB: '', pathDelta: d, yTicks: niceTicks(lo - 1, hi + 1, 5), zeroY: ys(0) };
    }

    let hi = 0;
    for (let i = 0; i <= visibleEnd; i += 1) hi = Math.max(hi, at(curveA, i));
    const ys = scaleLinear().domain([0, Math.max(hi * 1.04, 10)]).range([plotH, 0]);
    let d = '';
    for (let i = 0; i <= visibleEnd; i += step) {
      d += `${i === 0 ? 'M' : 'L'}${xs(i).toFixed(1)} ${ys(at(curveA, i)).toFixed(1)}`;
    }
    if (visibleEnd % step !== 0) d += `L${xs(visibleEnd).toFixed(1)} ${ys(at(curveA, visibleEnd)).toFixed(1)}`;
    return { x: xs, y: ys, pathA: d, pathB: '', pathDelta: '', yTicks: niceTicks(0, Math.max(hi * 1.04, 10), 5), zeroY: ys(0) };
  }, [curveA, curveB, comparing, total, visibleEnd, plotW, plotH]);

  const deltaNow = comparing && curveB ? (t <= 0 ? 0 : curveA[t - 1] - curveB[t - 1]) : 0;

  return (
    <figure className={s.fig} aria-labelledby={titleId}>
      <figcaption id={titleId} className={s.cap}>
        {comparing ? (
          <>
            累计箱数之差（{labelA} − {labelB}）随已处理项数变化。
            {sharedPrefix ? (
              <>两者共享 BF 前缀，前 {boundary} 项差为 0。</>
            ) : (
              <>其中全程 EoH 从第 1 项即用 EoH，启动状态不同，前 {boundary} 项不共享前缀。</>
            )}{' '}
            当前差 <strong className="num">{fmtSigned(deltaNow, 0)}</strong> 箱。
          </>
        ) : (
          <>{labelA} 的累计已用箱数随已处理项数变化。点 0 为初态。</>
        )}
      </figcaption>
      <svg className={s.svg} viewBox={`0 0 ${width} ${height}`} role="img">
        <g transform={`translate(${margin.left}, ${margin.top})`}>
          {yTicks.map((tk) => (
            <g key={tk} transform={`translate(0, ${y(tk)})`}>
              <line x1={0} x2={plotW} className={s.grid} />
              <text x={-8} y={4} className={s.tickY} textAnchor="end">
                {comparing ? fmtSigned(tk, 0) : fmt(tk, 0)}
              </text>
            </g>
          ))}
          {[0, boundary, total].map((xt) => (
            <g key={xt} transform={`translate(${x(xt)}, 0)`}>
              <line y1={0} y2={plotH} className={xt === boundary ? s.boundary : s.gridX} />
              <text y={plotH + 16} className={s.tickX} textAnchor="middle">
                {fmt(xt, 0)}
              </text>
            </g>
          ))}
          <text x={plotW / 2} y={plotH + 30} className={s.axisTitle} textAnchor="middle">
            已处理项数
          </text>

          {comparing && <line x1={0} x2={plotW} y1={zeroY} y2={zeroY} className={s.zero} />}
          {comparing ? (
            <path d={pathDelta} className={s.deltaLine} />
          ) : (
            <path d={pathA} fill="none" stroke={colorA} strokeWidth={2} strokeLinejoin="round" />
          )}
          {pathB && <path d={pathB} fill="none" stroke={colorB} strokeWidth={2} strokeLinejoin="round" />}

          {/* current position marker */}
          <line x1={x(t)} x2={x(t)} y1={0} y2={plotH} className={s.cursor} />
        </g>
      </svg>
    </figure>
  );
}
