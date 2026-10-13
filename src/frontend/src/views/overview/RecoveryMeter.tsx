import { useId } from 'react';
import { scaleLinear } from 'd3-scale';
import type { Meta } from '../../data/types';
import { fmt, fmtPct } from '../../lib/format';
import { EvidenceButton } from '../../components/EvidenceButton';
import { srcRef, metaChecks } from './provenance';
import s from './RecoveryMeter.module.css';

/**
 * The headroom story as a horizontal scale: the branch oracle (best of the two
 * executable continuations) at the good end, SBS at the other, and the selector
 * marked where it lands — close to the oracle. The recovered fraction is the
 * share of the SBS→oracle gap the selector closes.
 */
export function RecoveryMeter({
  sbsBins,
  selectorBins,
  oracleBins,
  headroom,
  regret,
  recovered,
  meta,
}: {
  sbsBins: number;
  selectorBins: number;
  oracleBins: number;
  headroom: number;
  regret: number;
  recovered: number | null;
  meta: Meta;
}) {
  const titleId = useId();
  const width = 300;
  const padX = 18;
  // Oracle is the best (fewest bins); SBS the reference. Map onto a track.
  const domainLo = Math.min(oracleBins, selectorBins) - headroom * 0.08;
  const domainHi = sbsBins + headroom * 0.12;
  const x = scaleLinear().domain([domainLo, domainHi]).range([padX, width - padX]);
  const trackY = 54;

  return (
    <aside className={s.meter} aria-labelledby={titleId}>
      <div className={s.meterHead}>
        <h2 id={titleId} className={s.meterTitle}>
          收回了可改善余地的 {fmtPct(recovered, 1)}
          <EvidenceButton
            provenance={{
              title: '收回余地比例',
              value: fmtPct(recovered, 4),
              meaning:
                '（SBS 相对分支 oracle 的余地 − 选择器相对分支 oracle 的后悔）/ 余地。衡量选择器把 SBS 与两分支事后最优之间的差距收回了多少，不是装箱效率提高的百分比。',
              derivation: `(${fmt(headroom, 3)} − ${fmt(regret, 3)}) / ${fmt(headroom, 3)} = ${fmtPct(recovered, 4)}`,
              sources: [srcRef(meta, 'analysis/SUMMARY.json', 'confirmation.headroom_recovered_fraction')],
              checks: metaChecks(meta, ['historical', 'project']),
            }}
          />
        </h2>
      </div>

      <svg className={s.svg} viewBox={`0 0 ${width} 108`} role="img" aria-hidden>
        {/* full headroom, oracle → SBS (neutral) */}
        <line x1={x(oracleBins)} x2={x(sbsBins)} y1={trackY} y2={trackY} className={s.gap} />
        {/* recovered share, selector → SBS (green = the 88.17% closed) */}
        <line x1={x(selectorBins)} x2={x(sbsBins)} y1={trackY} y2={trackY} className={s.recovered} />

        {/* oracle marker (label below to avoid colliding with the close selector label) */}
        <g transform={`translate(${x(oracleBins)}, ${trackY})`}>
          <circle r={5} fill="var(--panel)" stroke="var(--ink-3)" strokeWidth={2} />
          <text y={26} className={s.markTop} textAnchor="middle">
            分支 oracle
          </text>
          <text y={39} className={`${s.markNum} num`} textAnchor="middle">
            {fmt(oracleBins, 1)}
          </text>
        </g>
        {/* selector marker (label raised with a short leader) */}
        <g transform={`translate(${x(selectorBins)}, ${trackY})`}>
          <line y1={-6} y2={-20} stroke="var(--ink-4)" strokeWidth={1} />
          <circle r={6.5} fill="var(--sel)" stroke="var(--panel)" strokeWidth={2} />
          <text y={-24} className={s.markTopStrong} textAnchor="middle">
            选择器 {fmt(selectorBins, 1)}
          </text>
        </g>
        {/* SBS marker */}
        <g transform={`translate(${x(sbsBins)}, ${trackY})`}>
          <circle r={5} fill="var(--panel)" stroke="var(--eoh)" strokeWidth={2.4} />
          <text y={-14} className={s.markTop} textAnchor="middle">
            SBS
          </text>
          <text y={26} className={`${s.markNum} num`} textAnchor="middle">
            {fmt(sbsBins, 1)}
          </text>
        </g>
      </svg>

      <dl className={s.legend}>
        <div>
          <dt>已收回（SBS − 选择器）</dt>
          <dd className="num">{fmt(sbsBins - selectorBins, 2)} 箱</dd>
        </div>
        <div>
          <dt>剩余后悔（选择器 − oracle）</dt>
          <dd className="num">{fmt(regret, 2)} 箱</dd>
        </div>
      </dl>
    </aside>
  );
}
