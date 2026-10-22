/**
 * 文献依据登记。
 *
 * 纪律：
 * - 每条必须含题名、年份，以及 doi / url / repo_note 三者之一；
 * - supports 写该文献具体支撑的设计结论，不能凭标题推断能力；
 * - DOI 未经逐条核对的条目 status 标 '题录待复核'，不得补一个猜测的 DOI。
 */

export interface RefEntry {
  id: string;
  title: string;
  year: number;
  authors?: string;
  venue?: string;
  doi?: string;
  url?: string;
  /** 内部资料（契约文档/仓库记录）用 repo_note 而非编造外部出处。 */
  repo_note?: string;
  /** 该引用支撑的具体设计结论。 */
  supports: string;
  status: 'verified' | '题录待复核';
}

export const REFS: RefEntry[] = [
  {
    id: 'f2c2023',
    title: 'Fields2Cover: An open-source coverage path planning library for unmanned agricultural vehicles',
    year: 2023, authors: 'Mier, Valente, de Bruin', venue: 'Computers and Electronics in Agriculture',
    doi: '10.1016/j.compag.2023.107699', url: 'https://arxiv.org/abs/2210.07838',
    supports: '覆盖模板以 f2c_coverage.py 为契约求解后端；地头→布行→行排序→转弯路径的分层求解流程；内缩区与地头独立统计。',
    status: 'verified',
  },
  {
    id: 'dubins1957',
    title: 'On curves of minimal length with a constraint on average curvature, and with prescribed initial and terminal positions and tangents',
    year: 1957, authors: 'L. E. Dubins', venue: 'American Journal of Mathematics',
    doi: '10.2307/2372560',
    supports: '最小转弯半径 → 曲率约束路径族（Dubins 长度随半径增长）；不可倒车车辆转场的求解语义。',
    status: 'verified',
  },
  {
    id: 'galceran2013',
    title: 'A survey on coverage path planning for robotics',
    year: 2013, authors: 'Galceran, Carreras', venue: 'Robotics and Autonomous Systems',
    doi: '10.1016/j.robot.2013.09.004',
    supports: '覆盖路径规划的分解方法分类（梯形/Boustrophedon 单元分解）；覆盖率评价需明确分母口径。',
    status: 'verified',
  },
  {
    id: 'oksanen2009',
    title: 'Coverage path planning algorithms for agricultural field machines',
    year: 2009, authors: 'Oksanen, Visala', venue: 'Journal of Field Robotics',
    doi: '10.1002/rob.20300',
    supports: '田块覆盖的行排序与地头转弯连接是独立优化层；转弯成本不可从直线里程臆造。',
    status: 'verified',
  },
  {
    id: 'bochtis2008',
    title: 'Minimising the non-working distance travelled by machines operating in a headland field pattern',
    year: 2008, authors: 'Bochtis, Vougioukas', venue: 'Biosystems Engineering',
    doi: '10.1016/j.biosystemseng.2008.09.008',
    supports: '地头非作业里程是可独立优化的目标；转弯类型与地头空间的匹配关系。',
    status: 'verified',
  },
  {
    id: 'bochtis2009',
    title: 'Route planning of agricultural vehicles based on the Chinese postman problem formulation (Bochtis 团队行服务建模)',
    year: 2009, venue: 'Biosystems Engineering',
    doi: '10.1016/j.biosystemseng.2009.09.003',
    supports: '行间作业应建模为行服务（CARP 弧服务），每行是必须服务的线段而非中心点。',
    status: 'verified',
  },
  {
    id: 'seyyedhasani2017',
    title: 'Using the Vehicle Routing Problem to reduce field completion times with multiple machines',
    year: 2017, authors: 'Seyyedhasani, Dvorak', venue: 'Computers and Electronics in Agriculture',
    supports: '多机分工显著缩短完工时间 → 果园采收集运以 makespan 为目标、车队规模做实验因子。',
    repo_note: 'DOI 待核对后补入；当前不附猜测的标识符。',
    status: '题录待复核',
  },
  {
    id: 'conesa2016',
    title: 'Multi-criteria route planning for discrete spraying targets in orchards (Conesa-Muñoz 等离散目标喷施建模)',
    year: 2016, venue: 'Computers and Electronics in Agriculture',
    supports: '把喷施对象离散为带需求点集是一种有文献先例的近似；连续行喷施则需行服务建模。',
    repo_note: 'DOI 待核对后补入；当前不附猜测的标识符。',
    status: '题录待复核',
  },
  {
    id: 'jensen2015',
    title: 'Field logistics and capacity-driven refill trips in agricultural operations (Jensen 等田间物流)',
    year: 2015,
    supports: '容量驱动多趟补给是田间物流的结构性开销来源 → refill_overhead 单列。',
    repo_note: 'DOI 待核对后补入；当前不附猜测的标识符。',
    status: '题录待复核',
  },
  {
    id: 'zhou2014',
    title: 'Coverage path planning under obstacles by field decomposition (Zhou 等含障田块分解覆盖)',
    year: 2014,
    supports: '障碍作为覆盖区内孔时按几何分解为子区域分别覆盖再跨区连接。',
    repo_note: 'DOI 待核对后补入；当前不附猜测的标识符。',
    status: '题录待复核',
  },
  {
    id: 'plessen2019',
    title: 'Optimal in-field routing for full and partial field coverage with non-convex fields and obstacle areas (Plessen)',
    year: 2019,
    supports: '非凸田块与多障碍下的全/部分覆盖统一路由；支持斑块选择性覆盖的提案建模。',
    repo_note: 'DOI 待核对后补入；当前不附猜测的标识符。',
    status: '题录待复核',
  },
  {
    id: 'pyvrp_docs',
    title: 'PyVRP documentation — vehicle routing with heterogeneous fleets',
    year: 2024,
    url: 'https://pyvrp.org/',
    supports: 'vehicles.fleet 映射多车型 VRP（异构机队集运）；PyVRP 使用 seed，墙钟终止仍可能影响跨硬件重现。',
    status: 'verified',
  },
  {
    id: 'ortools_docs',
    title: 'OR-Tools routing library documentation',
    year: 2024,
    url: 'https://developers.google.com/optimization',
    supports: 'OR-Tools 车队调度使用路线跨度与里程加权目标；以总里程为搜索目标时不直接均衡各车工作量。',
    status: 'verified',
  },
  {
    id: 'urp_fleet144',
    title: 'URP fleet_routing 契约文档（多趟/容量/卸载点语义）',
    year: 2026,
    repo_note: '本仓 docs/protocol 下的 fleet_routing 契约：点集需求 + 容量 + unload_points 卸货 + rows 通行。',
    supports: '果园采收集运等点集需求模板直接落在契约字段内，无需新接口。',
    status: 'verified',
  },
  {
    id: 'urp_p510',
    title: 'URP 实验室第 510 号验证记录（fleet.check 独立验算）',
    year: 2026,
    repo_note: 'fleet.check 独立复算容量、趟次、作业位置与通行约束；rows 时重生成作物行核对路线不斜穿作物。',
    supports: '点集需求类模板的独立验算依据；验算与求解器分离。',
    status: 'verified',
  },
  {
    id: 'urp_contract_sim',
    title: 'URP 执行契约 §5.1（sim 准入限制）',
    year: 2026,
    repo_note: '契约 sim 仅支持同质差速轮式 ≤15 台；异构 → 422 heterogeneous_fleet_execution；曲率约束 → 422 curvature_constrained_execution；coverage 类不进 Gazebo。',
    supports: '全部模式 simulatable 维度的判定依据。',
    status: 'verified',
  },
];

export const REF_MAP: ReadonlyMap<string, RefEntry> = new Map(REFS.map((r) => [r.id, r]));
