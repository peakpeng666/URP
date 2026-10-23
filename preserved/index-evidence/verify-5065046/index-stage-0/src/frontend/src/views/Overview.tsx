import { ArrowRight } from 'lucide-react';
import { loadBytes, loadCells, loadMeta, loadCatalog, useAsync } from '../data/api';
import type { Cell, Meta, Stream } from '../data/types';
import { parseNpz } from '../lib/npz';
import { sha256Hex } from '../lib/sha256';
import { fmt, fmtPct, fmtSigned } from '../lib/format';
import { Async, EmptyState, Panel } from '../components/ui';
import { EvidenceButton } from '../components/EvidenceButton';
import { StatusTag } from '../components/Status';
import { MeanBinsDotPlot } from '../charts/MeanBinsDotPlot';
import { DeltaStrip } from '../charts/DeltaStrip';
import { CellMatrix } from '../charts/CellMatrix';
import { BootstrapHist } from '../charts/BootstrapHist';
import { RecoveryMeter } from './overview/RecoveryMeter';
import { FlowDiagram } from './overview/FlowDiagram';
import { ResultUsage } from './overview/ResultUsage';
import { srcRef, metaChecks } from './overview/provenance';
import s from './Overview.module.css';

export function Overview() {
  const meta = useAsync('meta', () => loadMeta());
  return (
    <div className={s.page}>
      <Async state={meta}>{(data) => <OverviewBody meta={data} />}</Async>
    </div>
  );
}

function OverviewBody({ meta }: { meta: Meta }) {
  const conf = meta.summary.confirmation;
  const risk = meta.summary.risk.summary;
  const [w, t, l] = conf.W_T_L_vs_SBS;
  const ci = conf.cluster_bootstrap_95_percentile_CI ?? null;
  const pv = meta.project_validation;
  const projectStatus = pv.status === 'PASS' ? 'pass' : pv.status === 'FAIL' ? 'fail' : 'pending';
  // Worst post-hoc regret is the max over risk streams' regret-to-branch-oracle,
  // not worst_harm_vs_SBS (they happen to both be 152 here, but differ in meaning).
  const worstRiskRegret = Math.max(
    0,
    ...meta.summary.risk.groups.flatMap((g) => g.selector_regrets),
  );

  return (
    <>
      <header className={s.hero}>
        <div className={s.heroText}>
          <p className={s.kicker}>确认集 · 108 条完整输入流 · 每流 5000 项 / 容量 100</p>
          <h1 className={s.headline}>
            只看前 500 项、再决定一次，<br />
            平均省下 <span className={s.bigDelta}>{fmt(-conf.selector_minus_SBS_mean, 2)}</span> 个箱子
          </h1>
          <p className={s.lede}>
            前 500 项由 BF 处理，再根据已到物品和箱残量选择继续 BF 或切换到固定 EoH，之后不再切换。
            相对训练选出的基线 SBS（= BF→EoH），它在确认集上平均{' '}
            <strong>{fmtSigned(conf.selector_minus_SBS_mean, 2)} 箱</strong>
            （负数表示更省）。
            <EvidenceButton
              provenance={{
                title: '主指标：选择器 − 训练 SBS 平均',
                value: `${fmtSigned(conf.selector_minus_SBS_mean, 6)} 箱`,
                meaning:
                  '108 条确认流上，选择器最终箱数减训练 SBS（BF→EoH）最终箱数的平均。负数表示选择器更省箱。这是预冻结的主指标，只来自确认集。',
                derivation:
                  '每流读取 analysis/confirmation_per_stream.csv 的 selector_minus_SBS，对 108 行取平均；由 analysis/SUMMARY.json 记录。',
                sources: [srcRef(meta, 'analysis/SUMMARY.json', 'confirmation.selector_minus_SBS_mean'), srcRef(meta, 'analysis/confirmation_per_stream.csv', 'selector_minus_SBS 列')],
                checks: metaChecks(meta, ['historical', 'project']),
              }}
            />
          </p>
          <div className={s.heroChips}>
            <HeroChip label="逐流 胜 / 平 / 负" value={`${w} / ${t} / ${l}`} tone={w > l ? 'save' : 'neutral'} />
            <HeroChip
              label="组 bootstrap 95% 区间"
              value={ci ? `[${fmt(ci[0], 2)}, ${fmt(ci[1], 2)}]` : '未计算'}
              tone="neutral"
            />
            <HeroChip label="最坏比 SBS 多用" value={`${fmt(conf.worst_harm_vs_SBS, 0)} 箱`} tone={conf.worst_harm_vs_SBS > 0 ? 'warn' : 'neutral'} />
          </div>
        </div>
        <RecoveryMeter
          sbsBins={conf.mean_bins.SBS}
          selectorBins={conf.mean_bins.SELECTOR}
          oracleBins={conf.mean_bins.branch_oracle}
          headroom={conf.SBS_oracle_headroom}
          regret={conf.selector_oracle_regret}
          recovered={conf.headroom_recovered_fraction}
          meta={meta}
        />
      </header>

      <div className={s.statusRow}>
        <StatusTag status="pass">包内独立审计：科学数据与预定分析 PASS</StatusTag>
        <StatusTag status={projectStatus}>
          本项目数据核验：
          {projectStatus === 'pass' ? '全量通过' : projectStatus === 'fail' ? '发现不一致' : '进行中'}
        </StatusTag>
        <StatusTag status="none">历史整体 900 CPU 秒预算：无法认证</StatusTag>
        <a className={s.statusMore} href="#/evidence">
          证据与核验范围 <ArrowRight size={13} aria-hidden />
        </a>
      </div>

      <Panel
        title="三个集合，一次冻结"
        subtitle="训练集运行两条分支，选出 SBS 并拟合邻居标签。冻结模型后评估确认集与风险集，主指标取自确认集。"
      >
        <FlowDiagram meta={meta} />
      </Panel>

      <Panel
        title="确认集各角色平均最终箱数"
        subtitle="箱数越少越好。各角色均值为 2730–2794 箱，横轴起点已标注。"
        aside={
          <EvidenceButton
            provenance={{
              title: '确认集平均最终箱数',
              meaning: '7 个角色在 108 条确认流上的平均最终箱数。SBS 与分支 oracle 取自已有运行；全程 EoH 使用不同起始状态。',
              derivation: '由 analysis/SUMMARY.json 的 confirmation.mean_bins 读取，等于各策略 108 流最终箱数的平均。',
              sources: [srcRef(meta, 'analysis/SUMMARY.json', 'confirmation.mean_bins')],
              checks: metaChecks(meta, ['historical', 'project']),
            }}
          />
        }
      >
        <MeanBinsDotPlot mean={conf.mean_bins} />
      </Panel>

      <div className={s.twoCol}>
        <Panel
          title="108 条确认流的逐流表现"
          subtitle="每点一条流，横轴为选择器 − SBS，负数在左表示节省。点击任一点打开该流回放。"
        >
          <ConfirmationStrip />
        </Panel>
        <Panel title="收益从哪里来" subtitle="选择器把 SBS 相对同前缀分支 oracle 的可改善余地收回了大部分。">
          <ul className={s.defList}>
            <HeadroomItem label="SBS 相对分支 oracle 的余地" value={`${fmt(conf.SBS_oracle_headroom, 3)} 箱`} />
            <HeadroomItem label="选择器相对分支 oracle 的后悔" value={`${fmt(conf.selector_oracle_regret, 3)} 箱`} />
            <HeadroomItem
              label="收回余地比例"
              value={fmtPct(conf.headroom_recovered_fraction, 2)}
              emphasis
            />
          </ul>
          <p className={s.note}>
            88.17% 表示选择器缩小了 SBS 与同前缀分支 oracle 之间的箱数差距，按这部分差距计算。
            分支 oracle 事后取两条分支中的最优结果，仅作比较参照。
          </p>
        </Panel>
      </div>

      <Panel
        title="18 个确认单元：尺寸族 × 到达顺序"
        subtitle="每格为 6 条新多重集流的选择器 − SBS 均值。同一多重集的三种顺序按一组统计；点击查看构成。"
        aside={
          <EvidenceButton
            provenance={{
              title: '18 个确认单元',
              meaning: '6 个尺寸族 × 3 种到达顺序，每格 6 流，18 格等权计入主指标。升序和降序由输入预先设定，在线算法按到达顺序处理。',
              derivation: '由 analysis/family_order_summary.csv 读取，派生为 cells.json。',
              sources: [srcRef(meta, 'analysis/family_order_summary.csv', '每族每顺序一行')],
              checks: metaChecks(meta, ['historical', 'project']),
            }}
          />
        }
      >
        <CellMatrixLoader />
      </Panel>

      <Panel
        title="不确定性：族内多重集组自助重抽样"
        subtitle="显示 cluster_bootstrap.npz 中的 10000 次重抽样均值。区间适用于本次预先固定的合成混合。"
        aside={
          <EvidenceButton
            provenance={{
              title: '组 bootstrap 95% 百分位区间',
              value: ci ? `[${fmt(ci[0], 6)}, ${fmt(ci[1], 6)}]` : '未计算',
              meaning:
                '按族内多重集分组重抽样，每组三种顺序一同抽取。区间取 10000 次均值分布的 2.5% 和 97.5% 分位，仅适用于本次预设合成混合的整体统计。新分布与筛选子集需另行估计。',
              derivation: 'analysis/cluster_bootstrap.npz 的 mean_deltas 数组（10000 个），百分位由 numpy.quantile 记录在 SUMMARY.json。',
              sources: [srcRef(meta, 'analysis/cluster_bootstrap.npz', 'mean_deltas / group_deltas / indices'), srcRef(meta, 'analysis/SUMMARY.json', 'confirmation.cluster_bootstrap_95_percentile_CI')],
              checks: metaChecks(meta, ['historical', 'project']),
            }}
          />
        }
      >
        {ci ? (
          <BootstrapLoader point={conf.selector_minus_SBS_mean} ci={ci} />
        ) : (
          <EmptyState title="未提供区间" detail="该数据集未记录 bootstrap 百分位区间，不绘制分布。" />
        )}
      </Panel>

      <Panel
        title="构造风险集：同前缀，不同未来"
        subtitle="4 组固定的 500 项前缀，各接三种 4500 项后缀。前缀选择应保持一致；风险结果单列，不计入确认收益。"
        id="risk-summary"
      >
        <div className={s.riskGrid}>
          <RiskStat label="相对训练 SBS 平均" value={`${fmtSigned(risk.selector_minus_SBS_mean, 3)} 箱`} tone="warn" />
          <RiskStat label="相对分支 oracle 平均后悔" value={`${fmt(risk.selector_oracle_regret, 2)} 箱`} tone="warn" />
          <RiskStat label="最坏事后后悔" value={`${fmt(worstRiskRegret, 0)} 箱`} tone="warn" />
          <RiskStat label="逐流 胜 / 平 / 负" value={risk.W_T_L_vs_SBS.join(' / ')} tone="neutral" />
        </div>
        <p className={s.note}>
          4 组中有 2 组在不同未来下出现严格相反的 oracle 最优分支。风险集这 12 流单列，不混入主指标，也不用于重新训练。
          <a className={s.inlineLink} href="#/risk">
            查看四组的逐一对照 <ArrowRight size={13} aria-hidden />
          </a>
        </p>
      </Panel>

      <ResultUsage />
    </>
  );
}

function ConfirmationStrip() {
  const catalog = useAsync('catalog', () => loadCatalog());
  return (
    <Async state={catalog}>
      {(data) => {
        const rows = data.streams.filter((s2: Stream) => s2.split === 'confirmation').map((s2) => s2.results);
        return <DeltaStrip rows={rows} />;
      }}
    </Async>
  );
}

function CellMatrixLoader() {
  const cells = useAsync('cells', () => loadCells());
  return <Async state={cells}>{(data) => <CellMatrix cells={data.cells as Cell[]} />}</Async>;
}

function BootstrapLoader({ point, ci }: { point: number; ci: [number, number] }) {
  const meta = useAsync('meta', () => loadMeta());
  const ref = meta.status === 'ready' ? meta.data.sources['analysis/cluster_bootstrap.npz'] : null;
  const url = ref?.url ?? null;
  const npz = useAsync(url, async (signal) => {
    const bytes = await loadBytes(url!, signal);
    // Verify the raw bytes against the recorded hash before trusting the
    // distribution — a decodable-but-altered file must not be drawn as real.
    if (ref?.sha256) {
      const actual = await sha256Hex(bytes);
      if (actual.toLowerCase() !== ref.sha256.toLowerCase()) {
        const err = new Error(`cluster_bootstrap.npz 的 SHA-256 与目录记录不符，已停止使用该文件。`) as Error & { code?: string; url?: string };
        err.code = 'HASH_MISMATCH';
        err.url = url!;
        throw err;
      }
    }
    const arrays = parseNpz(bytes);
    const md = arrays.mean_deltas;
    if (!md) throw new Error('cluster_bootstrap.npz 缺少 mean_deltas 数组');
    if (md.data.length !== 10000) throw new Error(`重抽样数组长度应为 10000，实际 ${md.data.length}`);
    for (let i = 0; i < md.data.length; i += 1) {
      if (!Number.isFinite(md.data[i])) throw new Error(`重抽样数组第 ${i} 个值非有限`);
    }
    return md.data as Float64Array;
  });
  if (!url) return null;
  return (
    <Async state={npz} loading={<div className={s.note}>正在解码重抽样数组…</div>}>
      {(samples) => <BootstrapHist samples={samples} ci={ci} point={point} />}
    </Async>
  );
}

function HeroChip({ label, value, tone }: { label: string; value: string; tone: 'save' | 'warn' | 'neutral' }) {
  return (
    <div className={s.heroChip} data-tone={tone}>
      <span className={s.heroChipLabel}>{label}</span>
      <span className={`${s.heroChipValue} num`}>{value}</span>
    </div>
  );
}

function HeadroomItem({ label, value, emphasis }: { label: string; value: string; emphasis?: boolean }) {
  return (
    <li className={s.defItem} data-emphasis={emphasis || undefined}>
      <span className={s.defLabel}>{label}</span>
      <span className={`${s.defValue} num`}>{value}</span>
    </li>
  );
}

function RiskStat({ label, value, tone }: { label: string; value: string; tone: 'warn' | 'neutral' }) {
  return (
    <div className={s.riskStat} data-tone={tone}>
      <span className={`${s.riskValue} num`}>{value}</span>
      <span className={s.riskLabel}>{label}</span>
    </div>
  );
}
