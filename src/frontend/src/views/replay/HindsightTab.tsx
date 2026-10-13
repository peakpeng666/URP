import type { Meta, Stream } from '../../data/types';
import { BRANCH_LABEL, PREF_LABEL } from '../../data/labels';
import { fmt, fmtSigned, deltaWord } from '../../lib/format';
import { EvidenceButton } from '../../components/EvidenceButton';
import { srcRef, metaChecks } from '../overview/provenance';
import s from './HindsightTab.module.css';

/** Future outcomes for this stream — explicitly the hindsight view. */
export function HindsightTab({ stream, meta }: { stream: Stream; meta: Meta }) {
  const r = stream.results;
  const isTrain = stream.split === 'train';

  if (isTrain) {
    return (
      <div className={s.wrap}>
        <p className={s.lead}>训练流只有两条真实分支，没有选择器运行。</p>
        <FinalBars
          rows={[
            { label: '全程 BF', value: r.BF, kind: r.oracle_preferred === 'BF' ? 'oracle' : 'plain' },
            { label: 'BF→EoH', value: r.BF_then_EoH, kind: r.oracle_preferred === 'BF_then_EoH' ? 'oracle' : 'plain' },
          ]}
        />
        <dl className={s.stats}>
          <Stat label="训练 SBS（本流取值）" value={`${fmt(r.SBS, 0)} 箱`} />
          <Stat label="分支 oracle（事后取优）" value={`${fmt(r.branch_oracle, 0)} 箱`} />
          <Stat label="SBS 相对分支 oracle 余地" value={`${fmt(r.SBS_regret, 0)} 箱`} />
        </dl>
      </div>
    );
  }

  const selBranch = r.selected_branch as 'BF' | 'BF_then_EoH';
  const matchedOracle = r.oracle_preferred === selBranch || r.oracle_preferred === 'tie';

  return (
    <div className={s.wrap}>
      <p className={s.lead}>
        以下是全部未来处理完后的真实结果——事后视角。合法的前缀选择在第 500 项时并不能看到这些。
      </p>

      <FinalBars
        rows={[
          { label: '全程 BF', value: r.BF, kind: 'plain' },
          { label: 'BF→EoH', value: r.BF_then_EoH, kind: 'plain' },
          { label: '全程 EoH', value: r.published_EoH ?? null, kind: 'muted' },
          { label: '选择器', value: r.SELECTOR ?? null, kind: 'selector' },
        ]}
        oracle={r.branch_oracle}
      />

      <div className={s.choiceRow}>
        <div className={s.choiceCard}>
          <span className={s.choiceLabel}>选择器选了</span>
          <span className={s.choiceValue}>{BRANCH_LABEL[selBranch]}</span>
        </div>
        <div className={s.choiceCard}>
          <span className={s.choiceLabel}>事后最优分支</span>
          <span className={s.choiceValue}>{PREF_LABEL[r.oracle_preferred]}</span>
        </div>
        <div className={s.choiceCard} data-ok={matchedOracle || undefined} data-bad={!matchedOracle || undefined}>
          <span className={s.choiceLabel}>是否撞上事后最优</span>
          <span className={s.choiceValue}>{matchedOracle ? '是' : '否'}</span>
        </div>
      </div>

      <dl className={s.stats}>
        <Stat
          label="选择器 − 训练 SBS"
          value={`${fmtSigned(r.selector_minus_SBS, 0)} 箱`}
          hint={deltaWord(r.selector_minus_SBS)}
          tone={numTone(r.selector_minus_SBS ?? 0)}
          evidence={
            <EvidenceButton
              provenance={{
                title: `${stream.instance_id}：选择器 − SBS`,
                value: `${fmtSigned(r.selector_minus_SBS, 0)} 箱`,
                meaning: '该流选择器最终箱数减训练 SBS 最终箱数。负数表示这条流上选择器更省。',
                derivation: 'analysis/confirmation_per_stream.csv（或 risk_per_stream.csv）对应行。',
                sources: [srcRef(meta, `analysis/${stream.split === 'risk' ? 'risk' : 'confirmation'}_per_stream.csv`, `${stream.instance_id} 行`)],
                checks: metaChecks(meta, ['project']),
              }}
            />
          }
        />
        <Stat label="选择器相对分支 oracle 后悔" value={`${fmt(r.selector_regret, 0)} 箱`} tone={numTone(r.selector_regret ?? 0)} />
        <Stat
          label="选择器 − 全程 EoH"
          value={`${fmtSigned(r.selector_minus_full_EoH, 0)} 箱`}
          hint="全程 EoH 启动状态不同，仅作说明性参照"
        />
        <Stat label="完整流 oracle（min 全BF/全EoH）" value={`${fmt(r.full_run_oracle, 0)} 箱`} hint="不同启动路径，不可部署，不替代分支 oracle" />
      </dl>
    </div>
  );
}

function numTone(v: number): 'save' | 'harm' | 'neutral' {
  return v < 0 ? 'save' : v > 0 ? 'harm' : 'neutral';
}

function FinalBars({
  rows,
  oracle,
}: {
  rows: { label: string; value: number | null; kind: 'plain' | 'muted' | 'selector' | 'oracle' }[];
  oracle?: number;
}) {
  const values = rows.map((r) => r.value).filter((v): v is number => v !== null);
  const min = Math.min(...values, oracle ?? Infinity);
  const max = Math.max(...values, oracle ?? -Infinity);
  const span = max - min || 1;
  const pct = (v: number) => `${((v - min) / span) * 100}%`;
  return (
    <div className={s.bars}>
      <p className={s.oracleNote}>
        条形从本组最小值 {fmt(min, 0)} 箱起算，用于比较差异；右侧为实际箱数。
      </p>
      {rows.map((row) => (
        <div key={row.label} className={s.barRow} data-kind={row.kind}>
          <span className={s.barLabel}>{row.label}</span>
          <div className={s.barTrack}>
            {row.value !== null && (
              <div className={s.barFill} style={{ width: pct(row.value) }} data-kind={row.kind} />
            )}
          </div>
          <span className={`${s.barValue} num`}>{row.value === null ? '—' : fmt(row.value, 0)}</span>
        </div>
      ))}
      {oracle !== undefined && (
        <p className={s.oracleNote}>
          同前缀分支 oracle = <span className="num">{fmt(oracle, 0)}</span> 箱（事后在两分支里取优，本身不可部署）。
        </p>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
  tone,
  evidence,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: 'save' | 'harm' | 'neutral';
  evidence?: React.ReactNode;
}) {
  return (
    <div className={s.stat}>
      <dt className={s.statLabel}>
        {label}
        {evidence}
      </dt>
      <dd className={s.statValue} data-tone={tone}>
        <span className="num">{value}</span>
        {hint && <span className={s.statHint}>{hint}</span>}
      </dd>
    </div>
  );
}
