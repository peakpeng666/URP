import type { Recommendation } from '../lab/types';
import { depotsOf } from './fleet';
import type { FleetInstance } from './types';

export const B7_FRONTEND_FILTER = {
  issue: 'B7',
  removeWhen: '后端推荐对异构、多库构造基线返回 applicable=false，且默认 compare 与提交准入经同一实例复验一致后移除',
} as const;

const CONSTRUCTIVE_BASELINES = new Set(['panel.cluster_first', 'panel.savings_fleet', 'panel.sweep']);

export function planningBlockReason(inst: FleetInstance, algorithmId: string): string | null {
  if (!CONSTRUCTIVE_BASELINES.has(algorithmId)) return null;
  if ((inst.vehicles.fleet?.length ?? 0) > 1) return `${B7_FRONTEND_FILTER.issue}：构造基线只支持同构单库输入，当前为 ${inst.vehicles.fleet!.length} 类车队`;
  if (depotsOf(inst).length > 1) return `${B7_FRONTEND_FILTER.issue}：构造基线只支持同构单库输入，当前为 ${depotsOf(inst).length} 个车库`;
  return null;
}

export function filterRecommendation(rec: Recommendation, inst: FleetInstance): Recommendation {
  const ranking = rec.ranking.map((item) => {
    const reason = planningBlockReason(inst, item.algorithm_id);
    if (!reason) return item;
    return {
      ...item,
      applicable: false,
      suitability: '不适用',
      reasons: [...item.reasons, `${reason}。前端临时过滤；${B7_FRONTEND_FILTER.removeWhen}`],
    };
  });
  const recommended = rec.recommended && !planningBlockReason(inst, rec.recommended)
    ? rec.recommended
    : ranking.find((item) => item.applicable)?.algorithm_id ?? null;
  const originalCompare = (rec as Recommendation & { compare?: string[] }).compare;
  const compare = (originalCompare ?? [])
    .filter((id) => !planningBlockReason(inst, id) && ranking.find((item) => item.algorithm_id === id)?.applicable);
  return { ...rec, ranking, recommended, ...(originalCompare ? { compare } : {}) } as Recommendation;
}
