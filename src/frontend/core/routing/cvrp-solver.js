/* Ports of the saved deterministic construction baselines; no LLM or search service. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./cvrp-problem.js'));
  else root.CVRPSolver = factory(root.CVRPProblem);
}(typeof globalThis !== 'undefined' ? globalThis : this, function (Problem) {
  'use strict';

  function distanceMatrix(instance) {
    return instance.coordinates.map(a => instance.coordinates.map(b =>
      Math.hypot(a[0] - b[0], a[1] - b[1])));
  }

  function nearestNeighbor(instance, matrix) {
    const remaining = new Set(instance.coordinates.slice(1).map((_, i) => i + 1));
    const routes = [];
    let operations = 0;
    while (remaining.size) {
      const route = [];
      let load = 0, last = 0;
      while (remaining.size) {
        let best = null;
        for (const node of remaining) {
          operations++;
          const fits = load + instance.demands[node] <= instance.capacity;
          const nearer = best === null || matrix[last][node] < matrix[last][best];
          const earlierTie = best !== null && matrix[last][node] === matrix[last][best] && node < best;
          if (fits && (nearer || earlierTie)) best = node;
        }
        if (best === null) break;
        route.push(best);
        load += instance.demands[best];
        last = best;
        remaining.delete(best);
      }
      routes.push(route);
    }
    return {routes, operations, workKind: '候选可行性检查'};
  }

  function parallelSavings(instance, matrix) {
    const active = new Map(), owner = new Map(), loads = new Map(), candidates = [];
    const n = instance.coordinates.length - 1;
    for (let a = 1; a <= n; a++) {
      active.set(a, [a]);
      owner.set(a, a);
      loads.set(a, instance.demands[a]);
      for (let b = a + 1; b <= n; b++) {
        candidates.push([matrix[0][a] + matrix[0][b] - matrix[a][b], a, b]);
      }
    }
    candidates.sort((a, b) => b[0] - a[0] || a[1] - b[1] || a[2] - b[2]);
    for (const [saving, a, b] of candidates) {
      if (saving <= 0) continue;
      const leftId = owner.get(a), rightId = owner.get(b);
      if (leftId === rightId || loads.get(leftId) + loads.get(rightId) > instance.capacity) continue;
      let left = active.get(leftId), right = active.get(rightId);
      if (![left[0], left.at(-1)].includes(a) || ![right[0], right.at(-1)].includes(b)) continue;
      if (left.at(-1) !== a) left = left.slice().reverse();
      if (right[0] !== b) right = right.slice().reverse();
      const merged = left.concat(right);
      active.set(leftId, merged);
      active.delete(rightId);
      loads.set(leftId, loads.get(leftId) + loads.get(rightId));
      loads.delete(rightId);
      for (const node of merged) owner.set(node, leftId);
    }
    return {
      routes: [...active.keys()].sort((a, b) => a - b).map(key => active.get(key)),
      operations: candidates.length,
      workKind: '节省值合并候选检查'
    };
  }

  function solve(instance, algorithm) {
    Problem.validate(instance);
    const matrix = distanceMatrix(instance);
    let result;
    if (algorithm === 'nearest_neighbor') result = nearestNeighbor(instance, matrix);
    else if (algorithm === 'parallel_savings') result = parallelSavings(instance, matrix);
    else throw Error('未知构造基线');
    const routes = result.routes.map(route => [0, ...route, 0]);
    let cost = 0;
    for (const route of routes) {
      for (let j = 1; j < route.length; j++) cost += matrix[route[j - 1]][route[j]];
    }
    return {
      algorithm, routes, reported_cost: cost,
      work: {kind: result.workKind, count: result.operations},
      assumptions: {fleet: 'unlimited_identical_vehicles', distance: 'unrounded_euclidean', split_delivery: false, obstacles: false}
    };
  }

  function choose(results) {
    const valid = results.filter(result => result.check?.accepted);
    if (!valid.length) return {selected: null, fallback: false, reason: '没有通过独立检查的方案'};
    valid.sort((a, b) => a.check.recomputed_cost - b.check.recomputed_cost || a.algorithm.localeCompare(b.algorithm));
    const preferred = results.find(result => result.algorithm === 'parallel_savings');
    const fallback = !!preferred && !preferred.check?.accepted;
    return {
      selected: valid[0].algorithm, fallback,
      reason: fallback ? 'Savings 未通过检查，回退到已通过的基线' :
        '运行两个基线后，按检查器复算距离选择；不是预先预测或 LLM 推荐'
    };
  }
  return {solve, choose};
}));
