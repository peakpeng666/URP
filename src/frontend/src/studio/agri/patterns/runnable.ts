/**
 * 可运行模式（14 个）：契约内可直接提交求解的农业任务模板。
 *
 * 建模纪律：
 * - 点集需求是真实的带需求点集（容量/卸载/趟数），不以轨迹点数代替工作量；
 * - 覆盖模板按作业幅宽计算覆盖面积，覆盖率分母写明（内缩作业区，地头单列）；
 * - 构建器放置规则镜像后端 validate.py（含 fleet 类别半径取 max），
 *   builders.test.ts 用镜像校验器守住这条对齐；
 * - 试验记录（EXP）只写真实发生的运行，数值来自后端返回。
 */
import type { AgriCapabilities, AgriTaskPattern, BuilderParam, BuiltScenario } from '../taxonomy';
import { disc, placeable, rng, round2, type Ring, type XY } from '../geometry';

const num = (v: Record<string, unknown>, k: string) => Number(v[k]);
const str = (v: Record<string, unknown>, k: string) => String(v[k]);

/** 参数表公共片段。 */
export const P = {
  size: (w: number, h: number): BuilderParam[] => [
    { key: 'field_w', label: '田块宽度', unit: 'm', type: 'number', default: w, min: 40, max: 600 },
    { key: 'field_h', label: '田块高度', unit: 'm', type: 'number', default: h, min: 40, max: 600 },
  ],
  rows: (deg: number): BuilderParam[] => [
    { key: 'row_angle', label: '行向角', unit: '°', type: 'number', default: deg, min: 0, max: 179 },
  ],
  tasks: (n: number, demand: number): BuilderParam[] => [
    { key: 'task_count', label: '任务点数', type: 'number', default: n, min: 4, max: 200 },
    { key: 'demand_per_task', label: '单点需求', type: 'number', default: demand, min: 1, max: 500 },
  ],
  fleet: (count: number, capacity: number, speed: number): BuilderParam[] => [
    { key: 'vehicles', label: '车辆数', type: 'number', default: count, min: 1, max: 15 },
    { key: 'capacity', label: '单车容量', type: 'number', default: capacity, min: 1, max: 5000 },
    { key: 'speed', label: '行驶速度', unit: 'm/s', type: 'number', default: speed, min: 0.3, max: 3 },
  ],
  robot: (r: number): BuilderParam[] => [
    { key: 'robot_radius', label: '机器人半径', unit: 'm', type: 'number', default: r, min: 0.3, max: 2 },
  ],
  depot: (at: 'sw' | 'n' | 'e'): BuilderParam[] => [
    {
      key: 'depot_at', label: '车库位置', type: 'select', default: at,
      options: [
        { value: 'sw', label: '西南角' }, { value: 'n', label: '北侧机耕路' }, { value: 'e', label: '东侧机耕路' },
      ],
    },
  ],
  objective: (o: 'makespan' | 'total_distance'): BuilderParam[] => [
    {
      key: 'objective', label: '优化目标', type: 'select', default: o,
      options: [
        { value: 'makespan', label: '均衡完成时间' }, { value: 'total_distance', label: '总里程' },
      ],
    },
  ],
  refill: (on: boolean): BuilderParam[] => [
    { key: 'refill_point', label: '田头补给/卸载点', type: 'boolean', default: on },
  ],
  obstacles: (n: number, r: number): BuilderParam[] => [
    { key: 'obstacle_count', label: '内部障碍数', type: 'number', default: n, min: 0, max: 6 },
    { key: 'obstacle_r', label: '障碍半径', unit: 'm', type: 'number', default: r, min: 0, max: 40 },
  ],
};

interface FleetSpec {
  word: string;
  crop: string;
  distribution: 'rows' | 'uniform';
  travel: 'rows' | 'free';
  plots: { cols: number; rows: number; margin: number } | null;
  unload?: 0 | 1;
  /** 后端按 max(类别半径) 校验任务/车库位置（validate.py 约 316–322 行）。 */
  placeRadius?: number;
}

interface FleetVehicles {
  count?: number;
  capacity?: number;
  speed_mps?: number;
  trips?: 'multi' | 'single';
  travel?: 'rows' | 'free';
  fleet?: {
    name: string; count: number; capacity: number; speed_mps: number;
    robot_radius?: number; payload?: string; min_turn_radius_m?: number;
  }[];
}

interface FleetInstance {
  boundary: Ring;
  plots: Ring[];
  obstacles: Ring[];
  rows?: [XY, XY][];
  depot: XY;
  depots?: XY[];
  unload_points?: XY[];
  tasks: { id: string; x: number; y: number; demand: number }[];
  vehicles: FleetVehicles;
  objective: 'total_distance' | 'makespan';
  robot_radius: number;
  units: 'm';
  meta: { task_word: string; margin_m: number; road_m: number };
}

/** 构建点集需求实例；放置校验镜像后端（半径取 max(基础半径, fleet 类别半径)）。 */
export function buildFleetInstance(
  v: Record<string, unknown>, seed: number, spec: FleetSpec,
): FleetInstance {
  const rand = rng(seed);
  const W = num(v, 'field_w');
  const H = num(v, 'field_h');
  const boundary: Ring = [[0, 0], [W, 0], [W, H], [0, H]];
  const r = Math.max(num(v, 'robot_radius'), spec.placeRadius ?? 0);

  // 地块划分
  const margin = spec.plots?.margin ?? 0;
  const plots: Ring[] = [];
  if (spec.plots) {
    const { cols, rows: prow } = spec.plots;
    const cw = (W - 2 * margin) / cols;
    const ch = (H - 2 * margin) / prow;
    for (let i = 0; i < cols; i++) {
      for (let j = 0; j < prow; j++) {
        plots.push([
          [round2(margin + i * cw), round2(margin + j * ch)],
          [round2(margin + (i + 1) * cw), round2(margin + j * ch)],
          [round2(margin + (i + 1) * cw), round2(margin + (j + 1) * ch)],
          [round2(margin + i * cw), round2(margin + (j + 1) * ch)],
        ]);
      }
    }
  }

  // 内部障碍（池塘等）：随机位置但保证自身可放置
  const obstacles: Ring[] = [];
  const obN = Math.round(num(v, 'obstacle_count') || 0);
  const obR = num(v, 'obstacle_r') || 0;
  for (let i = 0; i < obN && obR > 0; i++) {
    for (let t = 0; t < 40; t++) {
      const cx = W * (0.3 + 0.5 * rand());
      const cy = H * (0.3 + 0.5 * rand());
      const ob = disc(round2(cx), round2(cy), obR, 14);
      const cornersOK = ob.every((p) => placeable(p, boundary, [], 0.5));
      if (cornersOK) { obstacles.push(ob); break; }
    }
  }

  // rows 模式下：作物行在地块内；车库/补给点的 noGo = plots ∪ obstacles
  const rowLines: [XY, XY][] = [];
  const noGoForStation = spec.travel === 'rows' ? [...plots, ...obstacles] : obstacles;
  if (spec.distribution === 'rows') {
    const src = plots.length ? plots : [boundary];
    for (const pl of src) {
      const xs = pl.map((p) => p[0]);
      const ys = pl.map((p) => p[1]);
      const x0 = Math.min(...xs); const x1 = Math.max(...xs);
      const y0 = Math.min(...ys); const y1 = Math.max(...ys);
      const spacing = 6;
      for (let x = x0 + spacing / 2; x < x1; x += spacing) {
        rowLines.push([[round2(x), round2(y0 + 1)], [round2(x), round2(y1 - 1)]]);
      }
    }
  }

  // 任务点：rows 时落在作物行上，否则均匀散布；均以半径 r 做可放置校验
  const demand = Math.round(num(v, 'demand_per_task'));
  const want = Math.round(num(v, 'task_count'));
  const tasks: FleetInstance['tasks'] = [];
  let guard = 0;
  while (tasks.length < want && guard++ < want * 200) {
    let p: XY;
    if (spec.distribution === 'rows' && rowLines.length) {
      const ln = rowLines[Math.floor(rand() * rowLines.length)];
      const t = 0.08 + 0.84 * rand();
      p = [round2(ln[0][0] + (ln[1][0] - ln[0][0]) * t), round2(ln[0][1] + (ln[1][1] - ln[0][1]) * t)];
    } else {
      p = [round2(margin + (W - 2 * margin) * rand()), round2(margin + (H - 2 * margin) * rand())];
    }
    if (placeable(p, boundary, obstacles, r)) {
      tasks.push({ id: `${spec.word}${tasks.length + 1}`, x: p[0], y: p[1], demand });
    }
  }

  // 车库：按方位选基点，再以 r+0.5 在 noGo 外做环形搜索
  const base: XY = str(v, 'depot_at') === 'n' ? [round2(W / 2), round2(H - margin / 2)]
    : str(v, 'depot_at') === 'e' ? [round2(W - margin / 2), round2(H / 2)]
      : [round2(Math.max(margin / 2, 4)), round2(Math.max(margin / 2, 4))];
  let depot: XY = base;
  if (!placeable(base, boundary, noGoForStation, r + 0.5)) {
    for (let rad = 2; rad <= 40; rad += 2) {
      let placed: XY | null = null;
      for (let k = 0; k < 16; k++) {
        const a = (2 * Math.PI * k) / 16;
        const cand: XY = [round2(base[0] + rad * Math.cos(a)), round2(base[1] + rad * Math.sin(a))];
        if (placeable(cand, boundary, noGoForStation, r + 0.5)) { placed = cand; break; }
      }
      if (placed) { depot = placed; break; }
    }
  }

  // 田头补给/卸载点：同理
  const unload: XY[] = [];
  if ((spec.unload ?? 1) === 1 && v.refill_point !== false) {
    const ub: XY = [round2(Math.min(W - 6, depot[0] + 12)), round2(depot[1])];
    let placed: XY | null = null;
    if (placeable(ub, boundary, noGoForStation, r + 0.5)) placed = ub;
    if (!placed) {
      for (let rad = 2; rad <= 40 && !placed; rad += 2) {
        for (let k = 0; k < 16; k++) {
          const a = (2 * Math.PI * k) / 16;
          const cand: XY = [round2(ub[0] + rad * Math.cos(a)), round2(ub[1] + rad * Math.sin(a))];
          if (placeable(cand, boundary, noGoForStation, r + 0.5)) placed = cand;
        }
      }
    }
    unload.push(placed ?? [round2(ub[0] + 5), round2(ub[1] + 5)]);
  }

  const capacity = Math.max(Math.round(num(v, 'capacity')), demand);
  return {
    boundary, plots, obstacles,
    rows: rowLines.length ? rowLines : undefined,
    depot,
    unload_points: unload.length ? unload : undefined,
    tasks,
    vehicles: {
      count: Math.round(num(v, 'vehicles')), capacity,
      speed_mps: num(v, 'speed'), trips: 'multi', travel: spec.travel,
    },
    objective: str(v, 'objective') as 'total_distance' | 'makespan',
    robot_radius: r, units: 'm',
    meta: { task_word: spec.word, margin_m: margin, road_m: margin },
  };
}

function wrapFleet(
  id: string, title: string, summary: string, seed: number,
  inst: FleetInstance, v: Record<string, unknown>, note: string,
  params: BuilderParam[],
): BuiltScenario {
  return {
    id: `agri-${id}-${Date.now().toString(36)}-${seed}`,
    title, summary,
    problem_class: 'fleet_routing',
    frame: { kind: 'field', units: 'm', crs: 'local' },
    cost_unit: inst.objective === 'makespan' ? 's' : 'm',
    provenance: { generator: 'urp.studio.agri', seed, pattern: id, note },
    sim: { supported: false, world: null, spawn: null, reason: '实地田块坐标，尺度与仿真世界不同' },
    instance: inst as unknown as Record<string, unknown>,
    editable: { params, values: { ...v } },
    layers: {
      boundary: inst.boundary,
      plots: inst.plots,
      obstacles: inst.obstacles,
      rows: inst.rows ?? [],
      depot: inst.depot,
      unload_points: inst.unload_points ?? [],
    },
  };
}

function wrapCoverage(
  id: string, title: string, summary: string, seed: number,
  inst: Record<string, unknown>, v: Record<string, unknown>, note: string,
  params: BuilderParam[],
): BuiltScenario {
  return {
    id: `agri-${id}-${Date.now().toString(36)}-${seed}`,
    title, summary,
    problem_class: 'coverage',
    frame: { kind: 'field', units: 'm', crs: 'local' },
    cost_unit: 'm',
    provenance: { generator: 'urp.studio.agri', seed, pattern: id, note },
    sim: { supported: false, world: null, spawn: null, reason: 'coverage 问题类不在田间仿真准入范围' },
    instance: inst,
    editable: { params, values: { ...v } },
    layers: {
      boundary: inst.field,
      obstacles: inst.obstacles ?? [],
    },
  };
}

const cap = (
  defined: string, editable: string, solvable: [AgriCapabilities['solvable']['level'], string],
  checkable: string, sim: [AgriCapabilities['simulatable']['level'], string],
  experimented: [AgriCapabilities['experimented']['level'], string],
): AgriCapabilities => ({
  defined: { level: 'yes', note: defined },
  editable: { level: 'yes', note: editable },
  solvable: { level: solvable[0], note: solvable[1] },
  checkable: { level: 'yes', note: checkable },
  simulatable: { level: sim[0], note: sim[1] },
  experimented: { level: experimented[0], note: experimented[1] },
});

const SIM_DIFF_NOTE = '同构差速、无曲率约束、≤15 台时可申请进入生成的田间 Gazebo 世界（串行预约执行）；其余组合执行入口按契约返回 422。';
const FLEET_CHECK = 'fleet.check 独立复算容量、趟次、作业位置与通行约束（rows 时重生成作物行核对路线不斜穿作物）。';

// 2026-10-21/22 真实运行批次：种子 42，网关 0.1.0，独立验算均为后端真实返回；详见 docs/agriculture/复现与失败案例.md。
// （沙箱回收后于 10-22 重建代码；数值为当时后端真实返回，重建后以同种子复测核对。）
const EXP: Record<string, [AgriCapabilities['experimented']['level'], string]> = {
  orchard_harvest: ['yes', '实测对比（种子 42，预算 5 s）：ortools.fleet 1461.23 s < panel.cluster_first 1674.55 s，均 feasible 且独立验算通过；另经 UI 导入→求解→验算→刷新恢复全链验证。'],
  orchard_spray: ['yes', '实测对比（种子 42，预算 5 s）：ortools.fleet 1787.79 s < panel.cluster_first 2057.16 s，均 feasible 且独立验算通过。'],
  spot_spray: ['yes', '实测对比（种子 42，预算 2 s）：ortools.fleet 与 pyvrp.fleet 均 680.62 m 持平，均 feasible 且独立验算通过。'],
  field_sampling: ['yes', '实测对比（种子 42，预算 5 s）：pyvrp.fleet 791.02 m < ortools.fleet 813.95 m，均 feasible 且独立验算通过。'],
  grain_cart: ['yes', '实测对比（种子 42，预算 2 s）：ortools.fleet 551.27 s < pyvrp.fleet 846.56 s，均 feasible 且独立验算通过。'],
  mixed_fleet: ['yes', '实测对比（种子 42，预算 5 s）：ortools.fleet 835.79 s < pyvrp.fleet 1318.14 s，均 feasible 且独立验算通过；首次提交曾因 fleet 类别半径大于基础半径被后端 400 拒绝，构建器修复后通过（见失败案例文档）。'],
  tea_leaf: ['yes', '实测对比（种子 42，预算 2 s）：pyvrp.fleet 680.80 s < ortools.fleet 688.18 s，均 feasible 且独立验算通过；另经 UI 提交 3 算法对比（含 savings 基线）并验证刷新恢复。'],
  dubins: ['yes', '实测对比（种子 42，预算 5 s）：ortools.fleet 与 pyvrp.fleet 均 636.73 m，feasible 且曲率验算通过；首次运行因网关环境缺 ompl 记 state=error，装依赖并重启网关后复算成功，两次记录均保留。'],
  cov_tillage: ['partial', '单算法基线（种子 42，预算 3 s）：panel.boustrophedon 8210.0 m，feasible，独立扫掠验算通过（分母=内缩作业区，阈值 90%）；本环境 f2c 不可用，无横向对比。'],
  cov_obstacle: ['partial', '单算法基线（种子 42，预算 3 s）：panel.boustrophedon 返回 no_solution，独立验算判 invalid——连接段/足迹越界或穿障，内缩区覆盖率 0.8153 < 0.9；作为诚实失败基线保留，未粉饰为通过。'],
  greenhouse: ['yes', '实测对比（种子 42，预算 5 s）：pyvrp.fleet 743.07 s < ortools.fleet 836.59 s，均 feasible 且独立验算通过。'],
  multi_field: ['yes', '实测对比（种子 42，预算 5 s）：ortools.fleet 645.47 s < pyvrp.fleet 653.84 s，均 feasible 且独立验算通过。'],
  pasture: ['yes', '实测对比（种子 42，预算 5 s）：ortools.fleet 与 pyvrp.fleet 均 1141.42 m 持平，均 feasible 且独立验算通过。'],
  bale: ['yes', '实测对比（种子 42，预算 5 s）：ortools.fleet 1875.11 s < pyvrp.fleet 2012.67 s，均 feasible 且独立验算通过。'],
};

export const RUNNABLE_PATTERNS: AgriTaskPattern[] = [
  {
    id: 'orchard-harvest-transport', name: '果园采收集运',
    environments: ['orchard'], operation: 'picking', serviceObject: 'point_set',
    vehicleClasses: ['diff_drive'], planningProblem: 'cvrp',
    summary: '采摘点（树位/行间集中点）带载果需求，车辆沿行间通道收集并卸至田头装车点，多趟往返。',
    modeling: '采摘点是真实的带需求点集（点集 + 容量 + 卸载），不是行服务的近似；行间通行用 travel=rows 的真实通道图，地头/机耕路为开阔区。',
    refs: ['seyyedhasani2017', 'urp_fleet144', 'urp_p510'],
    capabilities: cap(
      '任务、容量、卸载点、行间通行均有契约字段。',
      '任务点、车库、容量、需求在既有地图编辑器全部可改。',
      ['yes', 'fleet_routing 原生语义：点集需求 + 容量 + unload_points 卸货 + rows 通行。'],
      FLEET_CHECK,
      ['partial', SIM_DIFF_NOTE], EXP.orchard_harvest,
    ),
    metrics: ['service_completion', 'trips', 'capacity_utilization', 'makespan', 'deadhead_distance', 'refill_overhead'],
    runnable: {
      problem_class: 'fleet_routing',
      params: [
        ...P.size(180, 120), ...P.rows(0),
        ...P.tasks(36, 200), ...P.fleet(3, 1200, 0.8), ...P.robot(0.75),
        ...P.depot('sw'), ...P.objective('makespan'), ...P.refill(true), ...P.obstacles(1, 12),
      ],
      build: (v, seed) => {
        const inst = buildFleetInstance(v, seed, {
          word: '采摘点', crop: '苹果', distribution: 'rows', travel: 'rows',
          plots: { cols: 1, rows: 1, margin: 8 }, unload: v.refill_point === false ? 0 : 1,
        });
        return wrapFleet('orchard-harvest-transport', '果园采收集运',
          `${inst.vehicles.count} 台车 · ${inst.tasks.length} 个采摘点 · ${num(v, 'field_w')}×${num(v, 'field_h')} m 果园 · 行间通行`,
          seed, inst, v, '采摘点沿作物行布置；空车沿通道进园，满载后回车库或田头装车点卸载。',
          RUNNABLE_PATTERNS[0].runnable!.params);
      },
    },
    experimentFactors: [
      { name: '车队规模', range: '1–6 台', basis: 'seyyedhasani2017：多机分工显著缩短完工时间' },
      { name: '容量/需求比', range: '3–10', basis: '决定趟数与补给开销占比' },
      { name: '行向与场形', range: '0–179° × 3 种形状', basis: '通道图随几何变化' },
    ],
  },
  {
    id: 'orchard-spray-points', name: '果园植保（离散喷施点近似）',
    environments: ['orchard'], operation: 'spraying_spot', serviceObject: 'point_set',
    vehicleClasses: ['diff_drive'], planningProblem: 'multi_trip_refill',
    summary: '把果树行上的喷药对象离散为带药量需求的点，药箱容量驱动多趟补给。',
    modeling: '近似：真实喷施是连续行服务（雾滴沿行沉积），此处按 CONESA 式离散目标集合建模；连续行服务见提案「行服务 CARP」。',
    refs: ['conesa2016', 'jensen2015', 'urp_p510'],
    capabilities: cap(
      '点需求 + 药箱容量 + 补给点语义完整。',
      '全部参数与几何可编辑。',
      ['partial', '求解本身真实可行；但“整行连续喷施”被离散为点集，漏喷/重喷与沉积不在验算范围。'],
      FLEET_CHECK,
      ['partial', SIM_DIFF_NOTE], EXP.orchard_spray,
    ),
    approximation: '行服务 → 点集：每棵树/每个喷施位一个点；不能表达“沿整行必须连续开启喷头”的约束。',
    metrics: ['service_completion', 'trips', 'refill_overhead', 'capacity_utilization', 'makespan'],
    runnable: {
      problem_class: 'fleet_routing',
      params: [
        ...P.size(180, 120), ...P.rows(0),
        ...P.tasks(48, 25), ...P.fleet(2, 600, 0.8), ...P.robot(0.75),
        ...P.depot('sw'), ...P.objective('makespan'), ...P.refill(true), ...P.obstacles(1, 12),
      ],
      build: (v, seed) => {
        const inst = buildFleetInstance(v, seed, {
          word: '喷施点', crop: '苹果', distribution: 'rows', travel: 'rows',
          plots: { cols: 1, rows: 1, margin: 8 }, unload: v.refill_point === false ? 0 : 1,
        });
        return wrapFleet('orchard-spray-points', '果园植保（离散喷施点）',
          `${inst.vehicles.count} 台车 · ${inst.tasks.length} 个喷施点 · 药箱容量驱动多趟`,
          seed, inst, v, '喷施点沿作物行布置；药尽回补给点。',
          RUNNABLE_PATTERNS[1].runnable!.params);
      },
    },
  },
  {
    id: 'field-grain-cart', name: '大田接粮运输（固定装载点）',
    environments: ['open_field'], operation: 'grain_cart', serviceObject: 'point_set',
    vehicleClasses: ['diff_drive'], planningProblem: 'pickup_delivery',
    summary: '接粮车在固定装载点接粮并运往粮库卸载；收割机—接粮车动态汇合见提案。',
    modeling: '装载点是真实带需求点，粮库是卸载点；多趟往返由容量驱动。动态汇合（跟机接粮）超出点集语义，另列提案。',
    refs: ['jensen2015', 'urp_fleet144', 'urp_p510'],
    capabilities: cap(
      '装载点需求 + 容量 + 卸载点完整。',
      '全部可编辑。',
      ['yes', 'fleet_routing 原生语义。'],
      FLEET_CHECK,
      ['partial', SIM_DIFF_NOTE], EXP.grain_cart,
    ),
    metrics: ['service_completion', 'trips', 'capacity_utilization', 'makespan', 'deadhead_distance'],
    runnable: {
      problem_class: 'fleet_routing',
      params: [
        ...P.size(240, 160),
        ...P.tasks(24, 300), ...P.fleet(2, 1500, 1.0), ...P.robot(0.8),
        ...P.depot('n'), ...P.objective('makespan'), ...P.refill(true), ...P.obstacles(0, 0),
      ],
      build: (v, seed) => {
        const inst = buildFleetInstance(v, seed, {
          word: '装载点', crop: '小麦', distribution: 'uniform', travel: 'free',
          plots: null, unload: v.refill_point === false ? 0 : 1,
        });
        return wrapFleet('field-grain-cart', '大田接粮运输',
          `${inst.vehicles.count} 台接粮车 · ${inst.tasks.length} 个装载点`,
          seed, inst, v, '装载点均匀散布；固定装载点语义，收割机位置不随时间变化。',
          RUNNABLE_PATTERNS[2].runnable!.params);
      },
    },
    experimentFactors: [
      { name: '车队规模', range: '1–6 台', basis: '接粮车数量决定收割机等待' },
    ],
  },
  {
    id: 'field-sampling', name: '土壤与作物采样',
    environments: ['open_field', 'paddy'], operation: 'sampling', serviceObject: 'point_set',
    vehicleClasses: ['diff_drive'], planningProblem: 'multi_visit',
    summary: '网格/随机布点采样，车辆依次访问采样点；无容量约束的多点访问。',
    modeling: '采样点是无需求点集（多点访问）；水田样本同样点可复用但下陷风险另列提案。',
    refs: ['urp_p510'],
    capabilities: cap(
      '点集完整。',
      '全部可编辑。',
      ['yes', 'fleet_routing 无容量即多点访问。'],
      FLEET_CHECK,
      ['partial', SIM_DIFF_NOTE], EXP.field_sampling,
    ),
    metrics: ['service_completion', 'total_distance', 'makespan'],
    runnable: {
      problem_class: 'fleet_routing',
      params: [
        ...P.size(200, 140),
        ...P.tasks(40, 1), ...P.fleet(2, 400, 0.8), ...P.robot(0.6),
        ...P.depot('sw'), ...P.objective('total_distance'), ...P.obstacles(0, 0),
      ],
      build: (v, seed) => {
        const inst = buildFleetInstance(v, seed, {
          word: '采样点', crop: '土壤', distribution: 'uniform', travel: 'free', plots: null,
        });
        return wrapFleet('field-sampling', '土壤与作物采样',
          `${inst.vehicles.count} 台车 · ${inst.tasks.length} 个采样点`,
          seed, inst, v, '采样点均匀散布；无补给语义。',
          RUNNABLE_PATTERNS[3].runnable!.params);
      },
    },
  },
  {
    id: 'spot-spray-weeding', name: '定点变量除草',
    environments: ['open_field'], operation: 'spraying_spot', serviceObject: 'point_set',
    vehicleClasses: ['diff_drive'], planningProblem: 'cvrp',
    summary: '杂草斑块的定点变量喷施：每点带药量需求，药箱容量驱动回站补给。',
    modeling: '点集带需求是真实语义（杂草斑块定位来自视觉识别）；机械除草（刀辊行服务）不在此模式。',
    refs: ['conesa2016', 'urp_p510'],
    capabilities: cap(
      '点需求 + 容量 + 补给完整。',
      '全部可编辑。',
      ['yes', 'fleet_routing 原生语义。'],
      FLEET_CHECK,
      ['partial', SIM_DIFF_NOTE], EXP.spot_spray,
    ),
    metrics: ['service_completion', 'refill_overhead', 'total_distance'],
    runnable: {
      problem_class: 'fleet_routing',
      params: [
        ...P.size(160, 120),
        ...P.tasks(30, 8), ...P.fleet(2, 80, 0.8), ...P.robot(0.6),
        ...P.depot('sw'), ...P.objective('total_distance'), ...P.refill(true), ...P.obstacles(0, 0),
      ],
      build: (v, seed) => {
        const inst = buildFleetInstance(v, seed, {
          word: '杂草点', crop: '玉米', distribution: 'uniform', travel: 'free',
          plots: null, unload: v.refill_point === false ? 0 : 1,
        });
        return wrapFleet('spot-spray-weeding', '定点变量除草',
          `${inst.vehicles.count} 台车 · ${inst.tasks.length} 个杂草斑块`,
          seed, inst, v, '斑块定位来自识别结果；药量需求驱动补给。',
          RUNNABLE_PATTERNS[4].runnable!.params);
      },
    },
  },
  {
    id: 'greenhouse-harvest-logistics', name: '温室采收物流',
    environments: ['greenhouse'], operation: 'picking', serviceObject: 'point_set',
    vehicleClasses: ['diff_drive'], planningProblem: 'cvrp',
    summary: '栽培床间的采收点集货，运至温室集货口；通道窄、对机器人半径敏感。',
    modeling: '点集需求 + 容量 + 卸载；通道宽度通过 robot_radius 与放置校验表达。',
    refs: ['urp_fleet144', 'urp_p510'],
    capabilities: cap(
      '点需求 + 容量 + 卸载完整。',
      '全部可编辑。',
      ['yes', 'fleet_routing 原生语义。'],
      FLEET_CHECK,
      ['no', '生成世界是露天农田，温室结构不生成；室内执行未适配。'], EXP.greenhouse,
    ),
    metrics: ['service_completion', 'trips', 'makespan'],
    runnable: {
      problem_class: 'fleet_routing',
      params: [
        ...P.size(80, 48),
        ...P.tasks(40, 20), ...P.fleet(2, 160, 0.6), ...P.robot(0.4),
        ...P.depot('e'), ...P.objective('makespan'), ...P.refill(true), ...P.obstacles(0, 0),
      ],
      build: (v, seed) => {
        const inst = buildFleetInstance(v, seed, {
          word: '采收点', crop: '番茄', distribution: 'rows', travel: 'rows',
          plots: { cols: 1, rows: 1, margin: 5 }, unload: v.refill_point === false ? 0 : 1,
        });
        return wrapFleet('greenhouse-harvest-logistics', '温室采收物流',
          `${inst.vehicles.count} 台车 · ${inst.tasks.length} 个采收点 · 窄通道`,
          seed, inst, v, '栽培床行内布点；通道窄，半径校验严格。',
          RUNNABLE_PATTERNS[5].runnable!.params);
      },
    },
  },
  {
    id: 'multi-field-fleet', name: '多田块机群作业分配',
    environments: ['multi_field'], operation: 'transfer', serviceObject: 'multi_region',
    vehicleClasses: ['diff_drive'], planningProblem: 'multi_field_alloc',
    summary: '多台车服务多个田块的任务点：田块间转场走开阔近似（真实路网见缺口说明）。',
    modeling: '多田块用多边形分区表达；田块间通行取欧氏近似，未接真实道路网。',
    refs: ['urp_fleet144', 'urp_p510'],
    capabilities: cap(
      '多区域 + 点集 + 容量齐备；路网缺失显式声明。',
      '全部可编辑。',
      ['yes', 'fleet_routing 原生语义（free 通行）。'],
      FLEET_CHECK,
      ['partial', SIM_DIFF_NOTE], EXP.multi_field,
    ),
    approximation: '田块间转场为欧氏近似；真实农场路网（机耕道宽度/限高/单行）不在契约内。',
    metrics: ['service_completion', 'makespan', 'deadhead_distance'],
    runnable: {
      problem_class: 'fleet_routing',
      params: [
        ...P.size(300, 200),
        ...P.tasks(48, 50), ...P.fleet(3, 400, 1.0), ...P.robot(0.8),
        ...P.depot('sw'), ...P.objective('makespan'), ...P.refill(true), ...P.obstacles(0, 0),
      ],
      build: (v, seed) => {
        const inst = buildFleetInstance(v, seed, {
          word: '作业点', crop: '多田块', distribution: 'uniform', travel: 'free',
          plots: { cols: 2, rows: 2, margin: 20 }, unload: v.refill_point === false ? 0 : 1,
        });
        return wrapFleet('multi-field-fleet', '多田块机群作业分配',
          `${inst.vehicles.count} 台车 · ${inst.plots.length} 个田块 · ${inst.tasks.length} 个作业点`,
          seed, inst, v, '4 田块分区；转场为欧氏近似。',
          RUNNABLE_PATTERNS[6].runnable!.params);
      },
    },
  },
];

export const RUNNABLE_PATTERNS_REST: AgriTaskPattern[] = [
  {
    id: 'pasture-monitoring', name: '牧场与草地巡检',
    environments: ['pasture'], operation: 'monitoring', serviceObject: 'point_set',
    vehicleClasses: ['diff_drive'], planningProblem: 'multi_visit',
    summary: '饮水点/围栏门/草场监测位的巡回检查，无容量约束。',
    modeling: '监测位是真实点集；牲畜活动区作为动态障碍另列提案。',
    refs: ['urp_p510'],
    capabilities: cap(
      '点集完整。',
      '全部可编辑。',
      ['yes', 'fleet_routing 无容量即多点访问。'],
      FLEET_CHECK,
      ['partial', SIM_DIFF_NOTE], EXP.pasture,
    ),
    metrics: ['service_completion', 'total_distance', 'makespan'],
    runnable: {
      problem_class: 'fleet_routing',
      params: [
        ...P.size(260, 180),
        ...P.tasks(24, 1), ...P.fleet(2, 1000, 1.0), ...P.robot(0.7),
        ...P.depot('sw'), ...P.objective('total_distance'), ...P.obstacles(2, 15),
      ],
      build: (v, seed) => {
        const inst = buildFleetInstance(v, seed, {
          word: '监测位', crop: '草场', distribution: 'uniform', travel: 'free', plots: null,
        });
        return wrapFleet('pasture-monitoring', '牧场与草地巡检',
          `${inst.vehicles.count} 台车 · ${inst.tasks.length} 个监测位`,
          seed, inst, v, '饮水点/围栏门等固定监测位巡回。',
          RUNNABLE_PATTERNS_REST[0].runnable!.params);
      },
    },
  },
  {
    id: 'tea-leaf-transport', name: '茶园鲜叶集运',
    environments: ['tea_garden'], operation: 'picking', serviceObject: 'point_set',
    vehicleClasses: ['diff_drive'], planningProblem: 'cvrp',
    summary: '条垄茶园的集叶点收集运输；坡地风险不在本模式（见提案）。',
    modeling: '集叶点是真实带需求点集；条垄按行布置。坡度/侧翻风险无模型，显式列为近似。',
    refs: ['seyyedhasani2017', 'urp_p510'],
    capabilities: cap(
      '点需求 + 容量 + 卸载完整。',
      '全部可编辑。',
      ['yes', 'fleet_routing 原生语义。'],
      FLEET_CHECK,
      ['partial', SIM_DIFF_NOTE], EXP.tea_leaf,
    ),
    approximation: '无坡度近似：茶园多在坡地，本模式平面化；坡地风险约束路径见提案。',
    metrics: ['service_completion', 'trips', 'makespan'],
    runnable: {
      problem_class: 'fleet_routing',
      params: [
        ...P.size(150, 90),
        ...P.tasks(30, 40), ...P.fleet(2, 300, 0.7), ...P.robot(0.6),
        ...P.depot('sw'), ...P.objective('makespan'), ...P.refill(true), ...P.obstacles(0, 0),
      ],
      build: (v, seed) => {
        const inst = buildFleetInstance(v, seed, {
          word: '集叶点', crop: '茶树', distribution: 'rows', travel: 'rows',
          plots: { cols: 1, rows: 1, margin: 7 }, unload: v.refill_point === false ? 0 : 1,
        });
        return wrapFleet('tea-leaf-transport', '茶园鲜叶集运',
          `${inst.vehicles.count} 台车 · ${inst.tasks.length} 个集叶点`,
          seed, inst, v, '条垄行内布点；坡度未建模。',
          RUNNABLE_PATTERNS_REST[1].runnable!.params);
      },
    },
  },
  {
    id: 'bale-collection', name: '草捆收集运输',
    environments: ['open_field', 'pasture'], operation: 'bale_collection', serviceObject: 'point_set',
    vehicleClasses: ['diff_drive'], planningProblem: 'cvrp',
    summary: '打捆后散布田间的草捆收集：每捆一个点，单车按捆数容量多趟运输。',
    modeling: '草捆是真实带需求点（1 捆 = 1 需求）；容量以捆计。',
    refs: ['urp_fleet144', 'urp_p510'],
    capabilities: cap(
      '点需求 + 容量 + 卸载完整。',
      '全部可编辑。',
      ['yes', 'fleet_routing 原生语义。'],
      FLEET_CHECK,
      ['partial', SIM_DIFF_NOTE], EXP.bale,
    ),
    metrics: ['service_completion', 'trips', 'capacity_utilization', 'makespan'],
    runnable: {
      problem_class: 'fleet_routing',
      params: [
        ...P.size(220, 150),
        ...P.tasks(36, 1), ...P.fleet(2, 10, 0.9), ...P.robot(0.8),
        ...P.depot('sw'), ...P.objective('makespan'), ...P.refill(true), ...P.obstacles(0, 0),
      ],
      build: (v, seed) => {
        const inst = buildFleetInstance(v, seed, {
          word: '草捆', crop: '牧草', distribution: 'uniform', travel: 'free',
          plots: null, unload: v.refill_point === false ? 0 : 1,
        });
        return wrapFleet('bale-collection', '草捆收集运输',
          `${inst.vehicles.count} 台车 · ${inst.tasks.length} 个草捆 · 单车 ${inst.vehicles.capacity} 捆`,
          seed, inst, v, '草捆散布；容量小导致多趟。',
          RUNNABLE_PATTERNS_REST[2].runnable!.params);
      },
    },
  },
  {
    id: 'mixed-fleet-transport', name: '异构机队集运（大小车混编）',
    environments: ['open_field'], operation: 'material_handling', serviceObject: 'point_set',
    vehicleClasses: ['diff_drive'], planningProblem: 'heterogeneous_coop',
    summary: '大车（大容量/大半径）与小车（小容量/灵活）混编集运，vehicles.fleet 多车型映射。',
    modeling: 'fleet 每类有独立容量/半径/速度；后端按 max(类别半径) 校验放置（构建器已对齐）。',
    refs: ['pyvrp_docs', 'seyyedhasani2017', 'urp_p510'],
    capabilities: cap(
      '多车型 + 点需求 + 容量 + 卸载完整。',
      '全部可编辑。',
      ['yes', 'PyVRP 异构车队原生；OR-Tools 按统一车型近似时注明。'],
      FLEET_CHECK,
      ['no', '执行侧只生成同构内置差速机器人；异构方案启动执行返回 422 heterogeneous_fleet_execution。'], EXP.mixed_fleet,
    ),
    metrics: ['service_completion', 'capacity_utilization', 'makespan'],
    runnable: {
      problem_class: 'fleet_routing',
      params: [
        ...P.size(240, 160),
        ...P.tasks(40, 60), ...P.fleet(4, 500, 0.9), ...P.robot(0.8),
        ...P.depot('sw'), ...P.objective('makespan'), ...P.refill(true), ...P.obstacles(0, 0),
      ],
      build: (v, seed) => {
        const inst = buildFleetInstance(v, seed, {
          word: '集货点', crop: '马铃薯', distribution: 'uniform', travel: 'free',
          plots: null, unload: v.refill_point === false ? 0 : 1,
          placeRadius: Math.max(1.0, num(v, 'robot_radius')),
        });
        const cap0 = Math.max(Math.round(num(v, 'capacity')), Math.round(num(v, 'demand_per_task')));
        inst.vehicles = {
          fleet: [
            { name: '大车', count: Math.max(1, Math.round(num(v, 'vehicles') / 2)), capacity: cap0, speed_mps: num(v, 'speed'), robot_radius: 1.0 },
            { name: '小车', count: Math.max(1, Math.floor(num(v, 'vehicles') / 2)), capacity: Math.max(1, Math.round(cap0 / 3)), speed_mps: num(v, 'speed') * 1.2, robot_radius: 0.5 },
          ],
          trips: 'multi', travel: 'free',
        };
        return wrapFleet('mixed-fleet-transport', '异构机队集运',
          `大车 ${inst.vehicles.fleet?.[0]?.count ?? 0} 台 + 小车 ${inst.vehicles.fleet?.[1]?.count ?? 0} 台 · ${inst.tasks.length} 个集货点`,
          seed, inst, v, '大小车混编；放置校验按最大类别半径。',
          RUNNABLE_PATTERNS_REST[3].runnable!.params);
      },
    },
  },
  {
    id: 'dubins-headland-transfer', name: '不可倒车车辆转场（Dubins 曲率约束）',
    environments: ['open_field'], operation: 'transfer', serviceObject: 'point_set',
    vehicleClasses: ['ackermann'], planningProblem: 'multi_visit',
    summary: '最小转弯半径 1.5–10 m 的不可倒车车辆访问作业点；min_turn_radius_m 触发 Dubins 实现。',
    modeling: '曲率约束进入求解（Dubins 路径族），不是先求欧氏解再事后修圆。',
    refs: ['dubins1957', 'urp_p510'],
    capabilities: cap(
      '点集 + 最小转弯半径完整。',
      '全部可编辑。',
      ['yes', 'min_turn_radius_m 为契约字段（0–10 m），求解按 Dubins 长度。'],
      '曲率验算为契约能力（Dubins 长度与半径约束独立复算）。',
      ['no', '执行侧为可原地转向差速模型；曲率约束类别启动执行返回 422 curvature_constrained_execution。'], EXP.dubins,
    ),
    metrics: ['total_distance', 'turn_count', 'nonworking_distance'],
    runnable: {
      problem_class: 'fleet_routing',
      params: [
        ...P.size(180, 120),
        ...P.tasks(20, 1), ...P.fleet(2, 1000, 1.0), ...P.robot(0.8),
        ...P.depot('sw'), ...P.objective('total_distance'), ...P.obstacles(1, 10),
        { key: 'turn_radius', label: '最小转弯半径', unit: 'm', type: 'number', default: 4.5, min: 1.5, max: 10, help: 'Dubins 曲率约束（0–10 m）。' },
      ],
      build: (v, seed) => {
        const inst = buildFleetInstance(v, seed, {
          word: '作业点', crop: '小麦', distribution: 'uniform', travel: 'free', plots: null,
        });
        const turn = Math.min(10, Math.max(1.5, num(v, 'turn_radius')));
        inst.vehicles = {
          fleet: [
            {
              name: '阿克曼作业车', count: Math.round(num(v, 'vehicles')),
              capacity: Math.max(Math.round(num(v, 'capacity')), 1), speed_mps: num(v, 'speed'),
              robot_radius: num(v, 'robot_radius'), payload: 'load', min_turn_radius_m: turn,
            },
          ],
          trips: 'multi', travel: 'free',
        };
        return wrapFleet('dubins-headland-transfer', '不可倒车车辆转场',
          `${Math.round(num(v, 'vehicles'))} 台车 · 转弯半径 ${turn} m · ${inst.tasks.length} 个作业点`,
          seed, inst, v, 'min_turn_radius_m 触发 Dubins 实现；曲率验算为契约能力。',
          RUNNABLE_PATTERNS_REST[4].runnable!.params);
      },
    },
    experimentFactors: [
      { name: '转弯半径', range: '1.5–10 m', basis: '契约范围；Dubins 长度随半径增长' },
    ],
  },
  {
    id: 'coverage-tillage', name: '大田耕整全覆盖',
    environments: ['open_field'], operation: 'tillage', serviceObject: 'area',
    vehicleClasses: ['tractor_implement'], planningProblem: 'full_coverage',
    summary: '矩形田全田覆盖：地头内缩、按作业幅宽布行、行排序与转弯连接。',
    modeling: 'coverage 原生语义：覆盖率分母 = 内缩作业区（validation_policy urp.coverage-interior90/2，≥90%），地头单列，工作/转弯/地头里程分段。',
    refs: ['f2c2023', 'bochtis2008', 'oksanen2009', 'galceran2013'],
    capabilities: {
      defined: { level: 'yes', note: '幅宽、地头宽、转弯半径、行向齐备。' },
      editable: { level: 'partial', note: 'coverage 编辑器支持既有字段；模板参数经构建表单生成。' },
      solvable: { level: 'yes', note: '契约求解器为 Fields2Cover（地头→布行→行排序→转弯路径）；本验收环境 f2c 无 wheel 未安装，实测由 panel.boustrophedon 基线承担。' },
      checkable: { level: 'yes', note: '独立覆盖率复算：分母为内缩作业区，阈值 90%，地头面积单列。' },
      simulatable: { level: 'no', note: 'coverage 问题类不在田间仿真准入范围（CONTRACT §5.1）。' },
      experimented: { level: EXP.cov_tillage[0], note: EXP.cov_tillage[1] },
    },
    metrics: ['coverage_ratio', 'overlap_ratio', 'missed_area', 'headland_area', 'turn_count', 'nonworking_distance'],
    runnable: {
      problem_class: 'coverage',
      params: [
        ...P.size(200, 140),
        { key: 'swath_width', label: '作业幅宽', unit: 'm', type: 'number', default: 3, min: 0.5, max: 12, help: '覆盖面积按 幅宽 × 作业段长度 计算，不用轨迹点数代替。' },
        { key: 'headland_width', label: '地头宽度', unit: 'm', type: 'number', default: 6, min: 0, max: 20, help: '内缩出作业区；地头面积单列统计。' },
        { key: 'turn_radius', label: '转弯半径', unit: 'm', type: 'number', default: 4.5, min: 1, max: 12, help: 'Dubins/Reeds–Shepp 转弯模型。' },
        { key: 'robot_width', label: '机具宽度', unit: 'm', type: 'number', default: 2.2, min: 0.5, max: 8, help: '机具包络。' },
        {
          key: 'route_pattern', label: '覆盖模式', type: 'select', default: 'boustrophedon',
          options: [
            { value: 'boustrophedon', label: '往复（boustrophedon）' },
            { value: 'snake', label: '蛇形' }, { value: 'spiral', label: '螺旋' },
          ],
          help: '行连接模式。',
        },
      ],
      build: (v, seed) => {
        const W = num(v, 'field_w'); const H = num(v, 'field_h');
        const inst = {
          field: [[0, 0], [W, 0], [W, H], [0, H]],
          headland_width: num(v, 'headland_width'),
          swath_width: num(v, 'swath_width'),
          turn_radius: num(v, 'turn_radius'),
          robot_width: num(v, 'robot_width'),
          start: [num(v, 'headland_width') / 2, num(v, 'headland_width') / 2],
          route_pattern: str(v, 'route_pattern'),
          angle_deg: null,
        };
        return wrapCoverage('coverage-tillage', '大田耕整全覆盖',
          `${W}×${H} m · 幅宽 ${num(v, 'swath_width')} m · 地头 ${num(v, 'headland_width')} m`,
          seed, inst, v, '覆盖率口径：分母 = 内缩作业区（interior90 政策）；地头单列。',
          RUNNABLE_PATTERNS_REST[5].runnable!.params);
      },
    },
    experimentFactors: [
      { name: '幅宽', range: '1.5–12 m', basis: '犁/耙/播机具幅宽' },
      { name: '地头宽/转弯半径比', range: '0.5–3', basis: 'bochtis2008：转弯类型与地头空间匹配' },
    ],
  },
  {
    id: 'coverage-obstacle-field', name: '含障碍田块覆盖',
    environments: ['open_field'], operation: 'spraying_blanket', serviceObject: 'area',
    vehicleClasses: ['tractor_implement', 'diff_drive'], planningProblem: 'full_coverage',
    summary: '田内有池塘等障碍：障碍作为内孔，分解后分区覆盖并跨区连接。',
    modeling: 'coverage 原生障碍语义（多边形内孔）；几何分解随障碍变化（zhou2014）。',
    refs: ['zhou2014', 'plessen2019', 'f2c2023'],
    capabilities: {
      defined: { level: 'yes', note: '障碍内孔 + 内缩 + 幅宽。' },
      editable: { level: 'partial', note: 'coverage 编辑器支持障碍多边形。' },
      solvable: { level: 'yes', note: '契约求解器为 Fields2Cover 单元分解处理内孔；本验收环境 f2c 不可用，实测由 panel.boustrophedon 基线承担（基线未通过独立验算，见实验记录）。' },
      checkable: { level: 'yes', note: 'interior90 政策：分母 = 内缩作业区（不含障碍）。' },
      simulatable: { level: 'no', note: 'coverage 不进仿真。' },
      experimented: { level: EXP.cov_obstacle[0], note: EXP.cov_obstacle[1] },
    },
    metrics: ['coverage_ratio', 'overlap_ratio', 'missed_area', 'headland_area', 'nonworking_distance'],
    runnable: {
      problem_class: 'coverage',
      params: [
        ...P.size(220, 150),
        { key: 'swath_width', label: '作业幅宽', unit: 'm', type: 'number', default: 4, min: 0.5, max: 12, help: '' },
        { key: 'headland_width', label: '地头宽度', unit: 'm', type: 'number', default: 7, min: 0, max: 20, help: '' },
        { key: 'turn_radius', label: '转弯半径', unit: 'm', type: 'number', default: 5, min: 1, max: 12, help: '' },
        { key: 'robot_width', label: '机具宽度', unit: 'm', type: 'number', default: 2.5, min: 0.5, max: 8, help: '' },
        { key: 'pond_r', label: '池塘半径', unit: 'm', type: 'number', default: 18, min: 5, max: 40, help: '内部圆形障碍。' },
      ],
      build: (v, seed) => {
        const W = num(v, 'field_w'); const H = num(v, 'field_h');
        const pond = disc(W * 0.55, H * 0.5, num(v, 'pond_r'), 14);
        const inst = {
          field: [[0, 0], [W, 0], [W, H], [0, H]],
          obstacles: [pond],
          headland_width: num(v, 'headland_width'),
          swath_width: num(v, 'swath_width'),
          turn_radius: num(v, 'turn_radius'),
          robot_width: num(v, 'robot_width'),
          start: [num(v, 'headland_width') / 2, num(v, 'headland_width') / 2],
          route_pattern: 'boustrophedon',
          angle_deg: null,
        };
        return wrapCoverage('coverage-obstacle-field', '含障碍田块覆盖',
          `${W}×${H} m · 池塘 r=${num(v, 'pond_r')} m · 幅宽 ${num(v, 'swath_width')} m`,
          seed, inst, v, '障碍为覆盖区内孔；覆盖率分母不含障碍区。',
          RUNNABLE_PATTERNS_REST[6].runnable!.params);
      },
    },
    experimentFactors: [
      { name: '障碍尺寸', range: '5–40 m', basis: 'zhou2014：障碍区拆分子区域分别覆盖' },
    ],
  },
];

RUNNABLE_PATTERNS.push(...RUNNABLE_PATTERNS_REST);
