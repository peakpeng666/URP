import { useMemo } from 'react';
import { ArrowRight, GitFork, TriangleAlert } from 'lucide-react';
import type { Route } from '../app/router';
import { buildHash, navigate } from '../app/router';
import { loadCatalog, loadDecision, loadMeta, useAsync } from '../data/api';
import type { Decision, Meta, Stream } from '../data/types';
import { BRANCH_LABEL, FAMILY_LABEL, ORDER_LABEL, ORDER_ORDER, PREF_LABEL } from '../data/labels';
import { fmt, fmtSigned, deltaWord } from '../lib/format';
import { Async, EmptyState, Panel, Spinner } from '../components/ui';
import { StatusTag } from '../components/Status';
import s from './RiskView.module.css';

export function RiskView({ route }: { route: Route }) {
  void route;
  const meta = useAsync('meta', () => loadMeta());
  const catalog = useAsync('catalog', () => loadCatalog());
  return (
    <div className={s.page}>
      <header className={s.header}>
        <h1 className={s.title}>同前缀，不同未来</h1>
        <p className={s.sub}>
          4 组构造风险流：每组用同一个固定的 500 项前缀，接三种不同的 4500 项未来（随机 / 升序 / 降序后缀）。
          合法的前缀选择器只看前 500 项，必须在三种未来下做出<strong>完全相同</strong>的决定。这单列呈现，不并入主指标，也不用于训练。
        </p>
      </header>
      <Async state={meta}>
        {(m) => <Async state={catalog}>{(c) => <RiskBody meta={m} streams={c.streams} />}</Async>}
      </Async>
    </div>
  );
}

function RiskBody({ meta, streams }: { meta: Meta; streams: Stream[] }) {
  const groups = useMemo(() => {
    const risk = streams.filter((st) => st.split === 'risk');
    const byGroup = new Map<string, Stream[]>();
    for (const st of risk) {
      const list = byGroup.get(st.group_id) ?? [];
      list.push(st);
      byGroup.set(st.group_id, list);
    }
    const summaries = new Map(meta.summary.risk.groups.map((g) => [g.group, g]));
    return [...byGroup.entries()]
      .map(([group, items]) => ({
        group,
        items: items.sort((a, b) => ORDER_ORDER.indexOf(a.order) - ORDER_ORDER.indexOf(b.order)),
        summary: summaries.get(group),
      }))
      .sort((a, b) => a.group.localeCompare(b.group));
  }, [streams, meta]);

  const risk = meta.summary.risk.summary;

  if (groups.length === 0) return <EmptyState title="没有风险组" />;

  return (
    <>
      <Panel>
        <div className={s.summaryRow}>
          <Stat label="相对训练 SBS 平均" value={`${fmtSigned(risk.selector_minus_SBS_mean, 3)} 箱`} tone="harm" />
          <Stat label="相对分支 oracle 平均后悔" value={`${fmt(risk.selector_oracle_regret, 2)} 箱`} tone="harm" />
          <Stat
            label="最坏事后后悔"
            value={`${fmt(Math.max(0, ...meta.summary.risk.groups.flatMap((g) => g.selector_regrets)), 0)} 箱`}
            tone="harm"
          />
          <Stat label="oracle 偏好反转的组" value={`${meta.summary.risk.groups.filter((g) => g.oracle_preference_reverses).length} / ${groups.length}`} tone="neutral" />
        </div>
      </Panel>

      {groups.map((g) => (
        <RiskGroup key={g.group} group={g} />
      ))}
    </>
  );
}

function RiskGroup({ group }: { group: { group: string; items: Stream[]; summary?: { choice: string; oracle_preference_reverses: boolean } } }) {
  const family = group.items[0]?.family;
  const choice = group.summary?.choice as 'BF' | 'BF_then_EoH' | undefined;
  const reverses = group.summary?.oracle_preference_reverses;

  // Load the three decisions and verify the prefix-safe fields are identical.
  const decisions = useAsync(group.group, async () => {
    const results = await Promise.all(
      group.items.map((st) => (st.decision_url ? loadDecision(st.decision_url) : Promise.resolve(null))),
    );
    return results;
  });

  return (
    <Panel
      id={`risk-group-${group.group}`}
      title={`${family ? FAMILY_LABEL[family] : group.group}前缀`}
      subtitle={`同一前缀，三种未来。前缀策略的选择固定为「${choice ? BRANCH_LABEL[choice] : '—'}」。`}
      aside={
        reverses ? (
          <StatusTag status="fail">
            <span className={s.reverseTag}>
              <TriangleAlert size={13} aria-hidden /> oracle 最优分支在不同未来下反转
            </span>
          </StatusTag>
        ) : (
          <StatusTag status="pending">oracle 偏好未反转</StatusTag>
        )
      }
    >
      <Async state={decisions} loading={<Spinner label="载入三种未来的决策…" />}>
        {(decs) => <Consistency decisions={decs} />}
      </Async>

      <div className={s.futures}>
        {group.items.map((st) => {
          const r = st.results;
          const matched = r.oracle_preferred === r.selected_branch || r.oracle_preferred === 'tie';
          return (
            <div key={st.instance_id} className={s.future}>
              <div className={s.futureHead}>
                <GitFork size={14} aria-hidden className={s.forkIcon} />
                <span className={s.futureOrder}>{ORDER_LABEL[st.order]}后缀</span>
              </div>
              <dl className={s.futureStats}>
                <FRow label="全程 BF" value={fmt(r.BF, 0)} />
                <FRow label="BF→EoH" value={fmt(r.BF_then_EoH, 0)} />
                <FRow label="选择器" value={r.SELECTOR == null ? '—' : fmt(r.SELECTOR, 0)} strong />
                <FRow label="分支 oracle" value={fmt(r.branch_oracle, 0)} />
                <FRow label="事后最优" value={PREF_LABEL[r.oracle_preferred]} />
                <FRow
                  label="选择器后悔"
                  value={`${fmt(r.selector_regret, 0)} 箱`}
                  tone={r.selector_regret && r.selector_regret > 0 ? 'harm' : 'ok'}
                />
              </dl>
              <div className={s.futureFoot} data-ok={matched || undefined} data-bad={!matched || undefined}>
                {matched ? '选择撞上事后最优' : `未撞上：${deltaWord(r.selector_regret)}对比 oracle`}
              </div>
              <button type="button" className={s.replayLink} onClick={() => navigate(buildHash('replay', st.instance_id, { a: 'SELECTOR', b: 'SBS', t: 500, view: 'observed' }))}>
                回放这个未来 <ArrowRight size={13} aria-hidden />
              </button>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function Consistency({ decisions }: { decisions: (Decision | null)[] }) {
  const decs = decisions.filter((d): d is Decision => d !== null);
  if (decs.length < 2) return null;
  const base = decs[0];
  const sameFeatures = decs.every((d) => d.features.length === base.features.length && d.features.every((f, i) => f === base.features[i]));
  const sameNeighbors = decs.every((d) => d.neighbors.length === base.neighbors.length && d.neighbors.every((n, i) => n === base.neighbors[i]));
  const samePred = decs.every((d) => d.predicted_final_bins.every((p, i) => p === base.predicted_final_bins[i]));
  const sameChoice = decs.every((d) => d.selected_index === base.selected_index);
  const allSame = sameFeatures && sameNeighbors && samePred && sameChoice;
  return (
    <div className={s.consistency} data-ok={allSame || undefined}>
      <StatusTag status={allSame ? 'pass' : 'fail'}>
        {allSame ? '前缀特征、5 个邻居、两分支预测与最终选择在三种未来下逐项一致' : '三种未来的前缀决策出现差异'}
      </StatusTag>
      <span className={s.consistencyNote}>（本浏览器即时比较三条流的 decision 记录）</span>
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone: 'harm' | 'neutral' }) {
  return (
    <div className={s.stat} data-tone={tone}>
      <span className={`${s.statValue} num`}>{value}</span>
      <span className={s.statLabel}>{label}</span>
    </div>
  );
}

function FRow({ label, value, strong, tone }: { label: string; value: string; strong?: boolean; tone?: 'harm' | 'ok' }) {
  return (
    <div className={s.fRow}>
      <dt className={s.fLabel}>{label}</dt>
      <dd className={`${s.fValue} num`} data-strong={strong || undefined} data-tone={tone}>
        {value}
      </dd>
    </div>
  );
}
