import { LabApiError } from '../lab/api';
import type { FleetInstance } from './types';

export function researchAcceptanceIssues(instance: FleetInstance | undefined): string[] {
  const issues: string[] = [];
  if (instance?.unload_points?.length) issues.push('B1/B2：补给路线提取和 rows 节点映射尚未修复；结果只用于无损复核，不称已验收可执行。');
  if (instance?.vehicles.fleet?.some((item) => (item.min_turn_radius_m ?? 0) > 0)) issues.push('B3：曲率反向漏检尚未修复；check.valid 不排除该漏检，Gazebo 执行仍会返回 422。');
  return issues;
}

export function unacceptedPlanReason(instance: FleetInstance | undefined): string | null {
  if (instance?.unload_points?.length) {
    return 'B1/B2：补给路线提取和 rows 节点映射尚未修复。输入与历史结果仍可保存、求解和查看，但本轮不从此入口推广为已验收 Gazebo 方案';
  }
  return null;
}

export function executionErrorMessage(error: unknown): string {
  const e = error instanceof Error ? error : new Error(String(error));
  const code = error instanceof LabApiError ? error.code : '';
  const status = error instanceof LabApiError ? error.status : 0;
  if (code === 'heterogeneous_fleet_execution') return `${e.message}（422 heterogeneous_fleet_execution）。恢复：保留该方案用于规划研究；如需执行，请在副本中改为同构内置车型并重新求解、验算`;
  if (code === 'curvature_constrained_execution') return `${e.message}（422 curvature_constrained_execution，B3 尚未修复）。恢复：保留曲率输入和结果；如需执行，请新建最小转弯半径为 0 的同构差速方案，不由界面静默改写`;
  if (code === 'unsupported_vehicle_asset') return `${e.message}（422 unsupported_vehicle_asset）。恢复：在检查器选择当前内置田间差速车型并重新求解；不会替换成其他车体`;
  if (status === 409) return `${e.message}（409 资产版本 / 哈希冲突）。恢复：核对资产当前版本，显式重新绑定并求解；历史方案仍按原快照保存`;
  if (code === 'timeout') return `${e.message}。启动请求可能已到达后端：先刷新当前会话状态，确认 idle 后再重试，避免重复启动`;
  if (code === 'network') return `${e.message}。未把窗口打开或请求发出当作实验成功；服务恢复后先刷新会话状态`;
  return e.message;
}
