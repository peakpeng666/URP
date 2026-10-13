import { Check, X } from 'lucide-react';
import { Panel } from '../../components/ui';
import s from './ResultUsage.module.css';

/** What the result does and does not support, straight from REPORT_ZH.md. */
export function ResultUsage() {
  return (
    <Panel title="结果应如何使用" subtitle="以下结论与限制取自报告与独立审计原文，不扩大解释。">
      <div className={s.cols}>
        <section className={s.col} data-kind="can">
          <h3 className={s.colHead}>
            <Check size={16} aria-hidden /> 可以报告
          </h3>
          <ul className={s.list}>
            <li>在预冻的六尺寸族 × 三到达顺序等权合成混合中，一个只见前 500 项的固定选择器取得上述可复查收益，含负例、同状态 oracle 后悔与已测成本。</li>
            <li>收益以箱数为主质量指标；CPU 已分项记录，未与箱数混为一谈。</li>
          </ul>
        </section>
        <section className={s.col} data-kind="cannot">
          <h3 className={s.colHead}>
            <X size={16} aria-hidden /> 不能报告
          </h3>
          <ul className={s.list}>
            <li>不能说原 132 研究已通过新确认，或实现了完整 AutoFolio / RAISE 方法。</li>
            <li>不能把完整流 oracle 当作可部署，或声称任意未来、未知新分布也享有同样收益。</li>
            <li>训练与确认同分布族、样本小、顺序结构固定；预测器可能依赖这种稳定性。</li>
          </ul>
        </section>
      </div>
      <div className={s.limits}>
        <h3 className={s.limitsHead}>仍适用的限制</h3>
        <ol className={s.limitList}>
          <li>六个固定尺寸族，训练/确认同族；bootstrap 条件于固定训练数据与模型，不含重新拟合不确定性或新族泛化。</li>
          <li>500 项时点与两种固定分支是冻结原型，不是最优选择器或通用超启发式的证明。</li>
          <li>宿主可读完整输入，但冻结选择接口没有未来访问；不是对抗性隔离沙箱。</li>
          <li>标量/NumPy 评分在本机正式轨迹一致；跨平台位级一致性未承诺。</li>
          <li>分支 oracle 是事后参照，本身不可部署；全程 EoH oracle 启动状态不同，不可混用。</li>
          <li>科学数据 PASS 不消除会计限制：历史整体 900 CPU 秒合规仍无法认证。</li>
        </ol>
      </div>
    </Panel>
  );
}
