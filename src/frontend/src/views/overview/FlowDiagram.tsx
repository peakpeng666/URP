import type { Meta } from '../../data/types';
import { fmt } from '../../lib/format';
import s from './FlowDiagram.module.css';

/** train → freeze → confirmation → risk, with real counts and what each gives. */
export function FlowDiagram({ meta }: { meta: Meta }) {
  const c = meta.counts;
  const train = meta.summary.training;
  return (
    <ol className={s.flow}>
      <li className={s.stage} data-split="train">
        <div className={s.stageHead}>
          <span className={s.stageName}>训练</span>
          <span className={`${s.stageCount} num`}>{c.streams_by_split.train} 流 · {c.runs_by_split.train} 运行</span>
        </div>
        <p className={s.stageBody}>
          每流执行全程 BF 与 BF→EoH 两条真实分支，得到 288 个标签。选出训练 SBS = <strong>BF→EoH</strong>
          （平均 {fmt(train.mean_bins[1], 1)} 箱，低于全程 BF 的 {fmt(train.mean_bins[0], 1)} 箱）。
        </p>
      </li>
      <li className={s.arrow} aria-hidden>
        →
      </li>
      <li className={s.stage} data-split="freeze">
        <div className={s.stageHead}>
          <span className={s.stageName}>冻结模型</span>
          <span className={s.stageCount}>k = 5 · 31 维特征</span>
        </div>
        <p className={s.stageBody}>
          用 144 训练行拟合 kNN 代价回归并写入 MODEL.json，哈希后才打开确认与风险结果。没有按测试结果调参。
        </p>
      </li>
      <li className={s.arrow} aria-hidden>
        →
      </li>
      <li className={s.stage} data-split="confirmation">
        <div className={s.stageHead}>
          <span className={s.stageName}>确认</span>
          <span className={`${s.stageCount} num`}>{c.streams_by_split.confirmation} 流 · {c.runs_by_split.confirmation} 运行</span>
        </div>
        <p className={s.stageBody}>
          每流执行全 BF、BF→EoH、全 EoH 与实际选择器。<strong>主指标只来自这里</strong>：选择器 − SBS。
        </p>
      </li>
      <li className={s.arrow} aria-hidden>
        →
      </li>
      <li className={s.stage} data-split="risk">
        <div className={s.stageHead}>
          <span className={s.stageName}>构造风险</span>
          <span className={`${s.stageCount} num`}>{c.streams_by_split.risk} 流 · {c.runs_by_split.risk} 运行</span>
        </div>
        <p className={s.stageBody}>
          4 组同前缀、不同未来的构造流，单列检验稳定性，<strong>不并入主指标</strong>。
        </p>
      </li>
    </ol>
  );
}
