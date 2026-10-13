/* Narrow workbench input profile. Historical Python CVRP contracts are unchanged. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.CVRPProblem = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const PROFILE = {
    id: 'cvrp-workbench-input-v1',
    min_tasks: 1,
    max_tasks: 100,
    customer_demands: 'positive safe integers',
    fleet: 'unlimited_identical_vehicles',
    objective: 'sum_unrounded_euclidean_distance',
    note: 'A narrower interactive profile than the saved Python instance contract'
  };

  function validate(instance) {
    if (!instance || !Array.isArray(instance.coordinates) || !Array.isArray(instance.demands)) {
      throw Error('需要坐标数组和需求数组');
    }
    const count = instance.coordinates.length;
    if (count !== instance.demands.length || count < 2 || count > 101) {
      throw Error('需要 1–100 个任务点，坐标与需求数量须一致');
    }
    if (instance.fleet !== PROFILE.fleet) {
      throw Error('当前基线只支持不限数量的同型车辆，不能保证有限车队可行');
    }
    if (instance.objective !== PROFILE.objective) {
      throw Error('当前工作台只支持未取整欧氏总距离目标');
    }
    if (!Number.isSafeInteger(instance.capacity) || instance.capacity < 1 || instance.capacity > 100000) {
      throw Error('容量须为 1–100000 的整数');
    }
    if (instance.depot !== 0 || instance.demands[0] !== 0) {
      throw Error('第 0 点必须是仓库，需求为 0');
    }
    instance.coordinates.forEach((point, index) => {
      if (!Array.isArray(point) || point.length !== 2 || point.some(value =>
        typeof value !== 'number' || !Number.isFinite(value) || Math.abs(value) > 10000)) {
        throw Error('点 ' + index + ' 的坐标须为 ±10000 内有限数');
      }
      const demand = instance.demands[index];
      if (!Number.isSafeInteger(demand) || demand < 0 || (index > 0 && demand < 1)) {
        throw Error('交互页任务需求须为正整数');
      }
      if (demand > instance.capacity) {
        throw Error('任务 ' + index + ' 的需求 ' + demand + ' 大于单车容量 ' +
          instance.capacity + '；不允许拆分交付，当前约束不可行');
      }
    });
    return instance;
  }
  return {PROFILE, validate};
}));
