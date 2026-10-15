import type { Service, SimState } from '../types';

/** SSE 'services' carries the full list, either bare or as {services}. */
export function selectServices(payload: unknown): { services: Service[] } | null {
  if (Array.isArray(payload)) return { services: payload as Service[] };
  const list = (payload as { services?: unknown } | null)?.services;
  return Array.isArray(list) ? { services: list as Service[] } : null;
}

export interface KnownIssue {
  source: string;
  text: string;
}

/** Fixed scope statements shown with the live known issues. */
export const SCOPE_NOTES: KnownIssue[] = [
  {
    source: '历史数据',
    text: '历史实验数据（data/、experiments/）不随源码恢复；未恢复时 BPP 历史结果各页显示"无历史数据"，不展示任何旧结论。',
  },
  {
    source: '机器人替身',
    text: '仿真使用官方 TurtleBot4 与官方 warehouse/depot/maze 世界作为农业机器人的替身；作物行、田头由地图通道代理，不代表真实农机动力学或田间环境。',
  },
  {
    source: '规划来源',
    text: 'URP 规划（项目算法或第三方求解器给出的任务顺序与路线）与 Nav2 自身规划分开记录：FollowPath 模式由 Nav2 控制器跟踪 URP 路径；Nav2 航点模式中 URP 只给顺序，路径由 Nav2 NavFn 规划；从当前位置到路线起点的接驳段始终由 Nav2 规划。',
  },
  {
    source: '坐标系',
    text: '基准算例坐标无物理单位，不能送入仿真；只有地图坐标（米，与 Gazebo 世界对齐）的结果可以执行。',
  },
];

/** Live known issues from services and the simulation session, de-duplicated by text. */
export function collectKnownIssues(services: Service[] | null | undefined, sim: SimState | null | undefined): KnownIssue[] {
  const seen = new Set<string>();
  const out: KnownIssue[] = [];
  const add = (source: string, text: string) => {
    const t = text.trim();
    if (!t || seen.has(t)) return;
    seen.add(t);
    out.push({ source, text: t });
  };
  for (const s of services ?? []) for (const issue of s.known_issues ?? []) add(s.name || s.id, issue);
  for (const issue of sim?.known_issues ?? []) add('仿真会话', issue);
  return out;
}

/** Order services the way a researcher reads them: core, solvers, ROS stack, GUIs. */
const ORDER = ['gateway', 'archive', 'solver', 'fields2cover', 'ros', 'sim', 'rviz', 'gazebo_gui'];

export function sortServices(services: Service[]): Service[] {
  const rank = (id: string) => {
    const i = ORDER.indexOf(id);
    return i === -1 ? ORDER.length : i;
  };
  return [...services].sort((a, b) => rank(a.id) - rank(b.id));
}

export const pendingKey = (id: string, action: string) => `${id}:${action}`;
