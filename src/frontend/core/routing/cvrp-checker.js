/* Requires a validated problem. No solver helpers or solver distance matrix are used. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.CVRPChecker = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function check(instance, output) {
    const errors = [], counts = Array(instance.coordinates.length).fill(0), loads = [], distances = [];
    let cost = 0;
    if (!output || !Array.isArray(output.routes) || output.routes.length > instance.coordinates.length - 1) {
      return {accepted: false, errors: ['路线集合无效'], recomputed_cost: null, loads, distances};
    }
    for (const [routeIndex, route] of output.routes.entries()) {
      if (!Array.isArray(route) || route.length < 3 || route.some(node =>
        !Number.isInteger(node) || node < 0 || node >= instance.coordinates.length)) {
        errors.push('车辆 ' + (routeIndex + 1) + ' 路线含未知节点或形状错误');
        continue;
      }
      if (route[0] !== 0 || route.at(-1) !== 0 || route.slice(1, -1).includes(0)) {
        errors.push('车辆 ' + (routeIndex + 1) + ' 须从仓库出发并回仓，中途不能回仓');
      }
      let load = 0, distance = 0;
      for (const node of route.slice(1, -1)) {
        if (node !== 0) {
          counts[node]++;
          load += instance.demands[node];
        }
      }
      if (load > instance.capacity) errors.push('车辆 ' + (routeIndex + 1) + ' 超载');
      for (let j = 1; j < route.length; j++) {
        const a = instance.coordinates[route[j - 1]], b = instance.coordinates[route[j]];
        const dx = a[0] - b[0], dy = a[1] - b[1];
        distance += Math.sqrt(dx * dx + dy * dy);
      }
      loads.push(load);
      distances.push(distance);
      cost += distance;
    }
    for (let node = 1; node < counts.length; node++) {
      if (counts[node] !== 1) errors.push('任务 ' + node + ' 访问 ' + counts[node] + ' 次，应恰好 1 次');
    }
    if (!Number.isFinite(output.reported_cost) || output.reported_cost < 0 || !Number.isFinite(cost) ||
      Math.abs(cost - output.reported_cost) > 1e-9 * Math.max(1, cost)) {
      errors.push('声明距离与独立几何复算不一致');
    }
    if (instance.fleet !== 'unlimited_identical_vehicles') errors.push('有限车队约束不受支持');
    return {
      accepted: errors.length === 0, errors,
      recomputed_cost: errors.length ? null : cost,
      loads, distances, route_count: output.routes.length,
      visited: counts.slice(1).filter(count => count === 1).length
    };
  }
  return {check};
}));
