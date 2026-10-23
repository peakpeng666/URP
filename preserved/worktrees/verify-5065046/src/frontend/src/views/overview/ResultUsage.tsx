import { Check, X } from 'lucide-react';
import { Panel } from '../../components/ui';
import s from './ResultUsage.module.css';

/** What the result does and does not support, straight from REPORT_ZH.md. */
export function ResultUsage() {
  return (
    <Panel title="结论与适用范围" subtitle="根据实验报告与独立审计整理。">
      <div className={s.cols}>
        <section className={s.col} data-kind="can">
          <h3 className={s.colHead}>
            <Check size={16} aria-hidden /> 实验结论
          </h3>
          <ul className={s.list}>
            <li>在预先固定、等权组合的六个尺寸族与三种到达顺序上，选择器仅根据前 500 项取得上述收益。记录包含负例、同状态 oracle 后悔值和计算成本。</li>
            <li>主要收益指标为箱数，CPU 耗时分项列出。</li>
          </ul>
        </section>
        <section className={s.col} data-kind="cannot">
          <h3 className={s.colHead}>
            <X size={16} aria-hidden /> 尚未验证
          </h3>
          <ul className={s.list}>
            <li>本次实验未重新确认原 132 研究，也未实现完整 AutoFolio / RAISE 方法。</li>
            <li>完整流 oracle 依赖事后信息，仅作参照；任意未来和新分布上的收益尚待验证。</li>
            <li>训练与确认同分布族、样本小、顺序结构固定；预测器可能依赖这种稳定性。</li>
          </ul>
        </section>
      </div>
      <div className={s.limits}>
        <h3 className={s.limitsHead}>实验条件</h3>
        <ol className={s.limitList}>
          <li>六个固定尺寸族，训练/确认同族；bootstrap 条件于固定训练数据与模型，不含重新拟合不确定性或新族泛化。</li>
          <li>实验固定在第 500 项选择两种分支之一；选择器的最优性与通用性尚未验证。</li>
          <li>选择接口仅访问前缀；宿主可读完整输入，未采用对抗性沙箱隔离。</li>
          <li>标量与 NumPy 评分在本机正式轨迹上一致；跨平台位级一致性待验证。</li>
          <li>分支 oracle 是事后参照，本身不可部署；全程 EoH oracle 启动状态不同，不可混用。</li>
          <li>科学数据核验已通过；历史整体 900 CPU 秒预算合规性仍无法认证。</li>
        </ol>
      </div>
    </Panel>
  );
}
