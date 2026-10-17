import type { Recommendation } from '../lab/types';
import { depotsOf } from './fleet';
import type { FleetInstance } from './types';

// UI preflight mirrors the backend contract; server validation remains authoritative.
const CONSTRUCTIVE_BASELINES = new Set(['panel.cluster_first', 'panel.savings_fleet', 'panel.sweep']);

export function planningBlockReason(inst: FleetInstance, algorithmId: string): string | null {
  if (!CONSTRUCTIVE_BASELINES.has(algorithmId)) return null;
  if ((inst.vehicles.fleet?.length ?? 0) > 1) return `构造基线只支持同构单库输入，当前为 ${inst.vehicles.fleet!.length} 类车队`;
  if (depotsOf(inst).length > 1) return `构造基线只支持同构单库输入，当前为 ${depotsOf(inst).length} 个车库`;
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
      reasons: [...item.reasons, `${reason}`],
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
