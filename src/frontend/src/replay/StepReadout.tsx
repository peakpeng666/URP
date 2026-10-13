import type { SideState, StepView } from './controller';
import { fmt } from '../lib/format';
import s from './StepReadout.module.css';

/** Current-step facts for one side: the item, where it went, residuals, counts. */
export function StepReadout({
  state,
  step,
  capacity,
  slotCount,
}: {
  state: SideState | null;
  step: StepView | null;
  capacity: number;
  slotCount: number;
}) {
  if (!state || state.processed === 0 || !step) {
    return <p className={s.idle}>初态：5000 个空槽，容量 100，尚未处理任何物品。按播放或单步开始。</p>;
  }
  const emptySlots = step.feasibleSlots; // includes unused empty slots
  return (
    <div className={s.wrap}>
      <div className={s.lead}>
        <div className={s.leadItem}>
          <span className={s.leadLabel}>第 {fmt(step.itemNumber, 0)} 项尺寸</span>
          <span className={`${s.leadValue} num`}>{fmt(step.size, 0)}</span>
        </div>
        <div className={s.leadItem}>
          <span className={s.leadLabel}>放入箱（0 基索引）</span>
          <span className={`${s.leadValue} num`}>#{fmt(step.bin, 0)}</span>
        </div>
      </div>

      <dl className={s.grid}>
        <Row label="该箱残量：放入前 → 放入后">
          <span className="num">{fmt(step.before, 0)}</span>
          <span className={s.arrow}>→</span>
          <span className="num">{fmt(step.after, 0)}</span>
        </Row>
        <Row label="累计已用箱数">
          <span className="num">{fmt(state.usedBins, 0)}</span>
        </Row>
        <Row label="当步是否开新箱">
          <span>{step.openedBin ? '是，开了一个新箱' : '否，放入已用箱'}</span>
        </Row>
        <Row label="可行槽位数（含未使用空槽）">
          <span className="num">{fmt(emptySlots, 0)}</span>
        </Row>
        <Row label="当前整体占用率">
          <span className="num">{state.fillRatio === null ? '—' : `${(state.fillRatio * 100).toFixed(1)}%`}</span>
        </Row>
      </dl>

      <p className={s.note}>
        箱号是 0 基槽位索引，不等于已用箱数；可行槽位数包含仍为空的槽，不能当作“可行的已用箱数”。
        残量只描述当步选中的箱。总槽位 {fmt(slotCount, 0)}，容量 {fmt(capacity, 0)}。
      </p>
    </div>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className={s.row}>
      <dt className={s.rowLabel}>{label}</dt>
      <dd className={s.rowValue}>{children}</dd>
    </div>
  );
}
