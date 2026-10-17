import { describe, expect, it } from 'vitest';
import type { Recommendation } from '../lab/types';
import { filterRecommendation, planningBlockReason } from './capabilities';
import type { FleetInstance } from './types';

const instance: FleetInstance = {
  boundary: [[0, 0], [10, 0], [10, 10]],
  plots: [],
  obstacles: [],
  depot: [0, 0],
  tasks: [],
  vehicles: { count: 2, capacity: 4, speed_mps: 1, trips: 'multi', travel: 'free' },
  objective: 'total_distance',
  robot_radius: 0.5,
  units: 'm',
};

function recommendation(): Recommendation {
  const item = (algorithm_id: string): Recommendation['ranking'][number] => ({
    algorithm_id,
    rank: 1,
    applicable: true,
    suitability: '可用',
    reasons: [],
    suggested_params: {},
  });
  return {
    problem_class: 'fleet_routing',
    policy: 'test',
    features: [],
    learned_selector: { id: '', status: 'not_applicable', reason: null, required: [], prediction: null },
    ranking: [item('pyvrp.fleet'), item('panel.cluster_first'), item('panel.savings_fleet'), item('panel.sweep')],
    recommended: 'panel.cluster_first',
    explanation: '',
    compare: ['pyvrp.fleet', 'panel.cluster_first'],
  } as Recommendation & { compare: string[] };
}

describe('fleet capability preflight', () => {
  it('removes constructive baselines from defaults and admission for heterogeneous fleets', () => {
    const hetero = structuredClone(instance);
    hetero.vehicles = { travel: 'free', fleet: [{ count: 1, capacity: 4, payload: 'load' }, { count: 1, capacity: 8, payload: 'load' }] };
    const filtered = filterRecommendation(recommendation(), hetero) as Recommendation & { compare: string[] };
    expect(filtered.compare).toEqual(['pyvrp.fleet']);
    expect(filtered.recommended).toBe('pyvrp.fleet');
    expect(filtered.ranking.find((item) => item.algorithm_id === 'panel.sweep')?.applicable).toBe(false);
    expect(planningBlockReason(hetero, 'panel.sweep')).toContain('只支持同构单库');
    expect(planningBlockReason(hetero, 'pyvrp.fleet')).toBeNull();
  });

  it('blocks multi-depot constructive baselines but keeps homogeneous single-depot inputs available', () => {
    const multi = structuredClone(instance);
    multi.depots = [[0, 0], [5, 5]];
    expect(planningBlockReason(multi, 'panel.cluster_first')).toContain('只支持同构单库');
    expect(planningBlockReason(instance, 'panel.cluster_first')).toBeNull();
  });
});
