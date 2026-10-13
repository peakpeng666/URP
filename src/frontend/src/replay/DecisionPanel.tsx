import { useMemo, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import type { Branch, Model, RunRecord } from '../data/types';
import { BRANCH_HEX, BRANCH_LABEL, FAMILY_LABEL, FEATURE_GROUPS, ORDER_LABEL, featureLabel } from '../data/labels';
import { fmt, fmtExp, fmtSigned } from '../lib/format';
import { checkDecision, remainingAfter, type DecisionCheck } from '../lib/recompute';
import { StatusMark } from '../components/Status';
import { navigate, buildHash } from '../app/router';
import s from './DecisionPanel.module.css';

interface DecisionData {
  branch: Branch;
  features: number[];
  feature_names?: string[];
  neighbors: number[];
  squared_distances: number[];
  predicted_final_bins: number[];
  selected_index: number;
  neighbor_rows?: {
    index: number;
    instance_id: string;
    family: string;
    order: string;
    labels: number[];
    squared_distance: number;
  }[];
}

/**
 * The frozen decision at item 500: predicted finals for both branches, the five
 * training neighbours, the 31 features (progressively disclosed) and an on-demand
 * browser re-derivation that only CHECKS the recorded values.
 */
export function DecisionPanel({
  decision,
  run,
  model,
  featureNames,
}: {
  decision: DecisionData;
  run: RunRecord | null;
  model: Model | null;
  featureNames: string[];
}) {
  const [openGroup, setOpenGroup] = useState<string | null>('item_hist');
  const [check, setCheck] = useState<DecisionCheck | null>(null);
  const [checkError, setCheckError] = useState<string | null>(null);

  const selected = decision.selected_index as 0 | 1;
  const predBF = decision.predicted_final_bins[0];
  const predEoH = decision.predicted_final_bins[1];
  const tie = predBF === predEoH;

  const zScores = useMemo(() => {
    if (!model) return null;
    return decision.features.map((f, j) => (f - model.mean[j]) / model.scale[j]);
  }, [decision.features, model]);

  const runCheck = () => {
    if (!run || !model) return;
    try {
      const rem = remainingAfter(run.items, run.assignment, 500);
      const result = checkDecision(decision, run.items.slice(0, 500), rem, model);
      setCheck(result);
      setCheckError(null);
    } catch (e) {
      setCheckError((e as Error).message);
    }
  };

  return (
    <div className={s.panel}>
      <div className={s.intro}>
        <p className={s.when}>第 500 项刚处理完，第 501 项尚未到达。选择器读取此刻的前缀与箱残量，只决定一次。</p>
      </div>

      <div className={s.branches}>
        {([0, 1] as const).map((idx) => {
          const branch: Branch = idx === 0 ? 'BF' : 'BF_then_EoH';
          const pred = idx === 0 ? predBF : predEoH;
          const isSel = selected === idx;
          return (
            <div key={branch} className={s.branchCard} data-selected={isSel || undefined} style={isSel ? { borderColor: BRANCH_HEX[branch] } : undefined}>
              <div className={s.branchHead}>
                <span className={s.branchSwatch} style={{ background: BRANCH_HEX[branch] }} aria-hidden />
                <span className={s.branchName}>{BRANCH_LABEL[branch]}</span>
                {isSel && <span className={s.chosen}>选中</span>}
              </div>
              <div className={`${s.pred} num`}>{fmt(pred, 1)}</div>
              <div className={s.predLabel}>预测最终箱数</div>
            </div>
          );
        })}
      </div>
      <p className={s.rule}>
        {tie ? (
          <>两分支预测相同，按平局规则退回训练 SBS（{BRANCH_LABEL[model ? (['BF', 'BF_then_EoH'][model.sbs_index] as Branch) : 'BF_then_EoH']}）。</>
        ) : (
          <>
            选择预测更小的一支：{BRANCH_LABEL[selected === 0 ? 'BF' : 'BF_then_EoH']}（少 {fmt(Math.abs(predBF - predEoH), 1)} 箱）。
            预测为 5 个邻居对应分支真实终箱数的等权均值。平方距离不是概率或置信度。
          </>
        )}
      </p>

      <section className={s.section}>
        <h3 className={s.h3}>5 个训练邻居</h3>
        <div className={s.neighbors}>
          <div className={`${s.nRow} ${s.nHead}`}>
            <span>训练流</span>
            <span className={s.nNum}>继续 BF</span>
            <span className={s.nNum}>切 EoH</span>
            <span className={s.nNum}>平方距离</span>
          </div>
          {decision.neighbors.map((nIdx, i) => {
            const row = decision.neighbor_rows?.[i];
            const d = decision.squared_distances[i];
            return (
              <button
                key={nIdx}
                type="button"
                className={s.nRow}
                onClick={() => row && navigate(buildHash('replay', row.instance_id, { a: 'BF', b: 'BF_then_EoH', t: 500, view: 'observed' }))}
                title={row ? `打开训练流 ${row.instance_id} 的回放` : undefined}
              >
                <span className={s.nName}>
                  {row ? (
                    <>
                      <span className={s.nFam}>
                        {FAMILY_LABEL[row.family as keyof typeof FAMILY_LABEL] ?? row.family} · {ORDER_LABEL[row.order as keyof typeof ORDER_LABEL] ?? row.order}
                      </span>
                      <span className={`${s.nId} mono`}>#{nIdx}</span>
                    </>
                  ) : (
                    <span className="mono">训练行 #{nIdx}</span>
                  )}
                </span>
                <span className={`${s.nNum} num`}>{row ? fmt(row.labels[0], 0) : '—'}</span>
                <span className={`${s.nNum} num`}>{row ? fmt(row.labels[1], 0) : '—'}</span>
                <span className={`${s.nNum} ${s.nDist} num`}>{fmtExp(d)}</span>
              </button>
            );
          })}
        </div>
        <p className={s.hint}>点击邻居可打开该训练流的回放（全程 BF vs BF→EoH）。</p>
      </section>

      <section className={s.section}>
        <h3 className={s.h3}>31 维前缀特征</h3>
        <div className={s.groups}>
          {FEATURE_GROUPS.map((g) => {
            const open = openGroup === g.key;
            return (
              <div key={g.key} className={s.group}>
                <button
                  type="button"
                  className={s.groupHead}
                  aria-expanded={open}
                  onClick={() => setOpenGroup(open ? null : g.key)}
                >
                  <ChevronDown size={15} className={s.chev} data-open={open || undefined} aria-hidden />
                  <span className={s.groupLabel}>{g.label}</span>
                  <span className={s.groupRange}>{g.to - g.from} 维</span>
                </button>
                {open && (
                  <>
                    <p className={s.groupHint}>{g.hint}</p>
                    <div className={s.featGrid}>
                      {Array.from({ length: g.to - g.from }, (_, k) => {
                        const j = g.from + k;
                        const name = featureNames[j] ?? decision.feature_names?.[j] ?? `f${j}`;
                        return (
                          <div key={j} className={s.feat}>
                            <span className={s.featName}>{featureLabel(name)}</span>
                            <span className={`${s.featVal} num`}>{fmt(decision.features[j], 3)}</span>
                            {zScores && <span className={s.featZ}>z {fmtSigned(zScores[j], 2)}</span>}
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <section className={s.section}>
        <div className={s.recHead}>
          <h3 className={s.h3}>在本浏览器复算核对</h3>
          {!check && (
            <button type="button" className={s.recBtn} onClick={runCheck} disabled={!run || !model}>
              运行复算
            </button>
          )}
        </div>
        <p className={s.hint}>
          由记录的前缀物品与内核回放的 500 项残量重算特征，用冻结模型重做 kNN，与记录逐项对照。界面显示的仍是记录值。
        </p>
        {checkError && <p className={s.recErr}>复算失败：{checkError}</p>}
        {check && (
          <ul className={s.recList}>
            <RecItem
              ok={check.featuresMaxAbs <= 1e-9}
              label="31 维特征"
              detail={`${check.featuresExact}/31 位级一致，最大偏差 ${check.featuresMaxAbs === 0 ? '0' : check.featuresMaxAbs.toExponential(1)}`}
            />
            <RecItem ok={check.neighborsMatch} label="5 个邻居与顺序" detail={check.neighborsMatch ? '完全一致' : '不一致'} />
            <RecItem
              ok={check.distancesMaxAbs <= 1e-9}
              label="平方距离"
              detail={`最大偏差 ${check.distancesMaxAbs === 0 ? '0' : check.distancesMaxAbs.toExponential(1)}`}
            />
            <RecItem
              ok={check.predictionsMaxAbs === 0}
              label="两分支预测"
              detail={check.predictionsMaxAbs === 0 ? '完全一致' : `最大偏差 ${check.predictionsMaxAbs.toExponential(1)}`}
            />
            <RecItem ok={check.selectedMatch} label="最终选择" detail={check.selectedMatch ? '一致' : '不一致'} />
          </ul>
        )}
      </section>
    </div>
  );
}

function RecItem({ ok, label, detail }: { ok: boolean; label: string; detail: string }) {
  return (
    <li className={s.recItem}>
      <StatusMark status={ok ? 'pass' : 'fail'} size={15} />
      <span className={s.recLabel}>{label}</span>
      <span className={s.recDetail}>{detail}</span>
    </li>
  );
}
