import type { SimPhase } from '../types';
import type { Tone } from '../ui';

export const SIM_PHASE_LABEL: Record<SimPhase, string> = {
  stopped: '未运行',
  starting: '启动中',
  undocking: '出坞中',
  localizing: '定位中',
  nav2_starting: 'Nav2 启动中',
  ready: '就绪',
  executing: '执行中',
  stopping: '停止中',
  failed: '失败',
};

export function simPhaseTone(phase: SimPhase | string | null | undefined): Tone {
  switch (phase) {
    case 'ready':
      return 'ok';
    case 'executing':
    case 'starting':
    case 'undocking':
    case 'localizing':
    case 'nav2_starting':
    case 'stopping':
      return 'busy';
    case 'failed':
      return 'error';
    default:
      return 'idle';
  }
}

export const simPhaseLabel = (phase: string | null | undefined) =>
  phase ? (SIM_PHASE_LABEL as Record<string, string>)[phase] ?? phase : '未知';

/** Phases where a session process exists and can be stopped. */
export const simSessionActive = (phase: string | null | undefined) =>
  !!phase && phase !== 'stopped' && phase !== 'failed';

export const SIM_WORLDS = ['warehouse', 'depot', 'maze'] as const;
export type SimWorld = (typeof SIM_WORLDS)[number];

export const WORLD_LABEL: Record<string, string> = {
  warehouse: '仓库 warehouse',
  depot: '车场 depot',
  maze: '迷宫 maze',
};

export const COMPONENT_LABEL: Record<string, string> = {
  sim: 'Gazebo 仿真',
  gui: 'Gazebo 窗口',
  rviz: 'RViz2',
  localization: '定位 AMCL',
  nav2: 'Nav2',
  bridge: 'ros_gz 桥接',
};

export const COMPONENT_STATE_LABEL: Record<string, string> = {
  running: '运行中',
  active: '活动',
  inactive: '未激活',
  off: '关闭',
  starting: '启动中',
  stopping: '停止中',
  failed: '失败',
  unavailable: '不可用',
};

export function componentTone(state: string): Tone {
  if (state === 'running' || state === 'active') return 'ok';
  if (state === 'starting' || state === 'stopping') return 'busy';
  if (state === 'failed') return 'error';
  if (state === 'inactive') return 'warn';
  return 'idle';
}
