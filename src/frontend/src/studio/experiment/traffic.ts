export interface TrafficEvidence {
  state?: 'succeeded' | 'failed' | 'canceled' | string;
  traffic?: {
    policy?: string;
    robot_collisions?: boolean;
    scope?: string;
  } | null;
  check?: {
    valid?: boolean;
    errors?: string[];
    traffic?: {
      valid?: boolean;
      method?: string;
      pairs?: { min_center_distance_m?: number; min_footprint_gap_m?: number; t_sim?: number; valid?: boolean }[];
    } | null;
    dynamics?: {
      valid?: boolean;
      scope?: string;
      thresholds?: { max_sample_gap_s?: number };
      vehicles?: {
        vehicle: string;
        truth_samples?: number;
        odom_samples?: number;
        paired_samples?: number;
        max_truth_gap_s?: number;
        odom_position_rmse_m?: number;
        odom_position_final_m?: number;
        odom_position_max_m?: number;
      }[];
    };
  } | null;
  contact_observation?: { status?: string; count_unit?: string; legacy_note?: string | null } | null;
  row_collision_shapes?: number | null;
  row_collisions?: number | null;
  robot_contact_events?: number | null;
}

export interface TrafficStatus {
  value: string;
  tone: 'good' | 'warn' | 'bad';
  note: string;
}

const count = (value: number | null | undefined) => value == null ? '未知' : String(value);

export function trafficStatus(result: TrafficEvidence): TrafficStatus {
  const policy = result.traffic?.policy;
  const exclusive = policy === 'exclusive_mission_v1';
  const observed = result.contact_observation?.status === 'observed';
  const trafficCheck = result.check?.traffic;
  const counts = `作物行几何 ${count(result.row_collision_shapes)} 个；作物行接触消息 ${count(result.row_collisions)}；车间接触消息 ${count(result.robot_contact_events)}（缺字段不等于零）`;
  const scope = exclusive ? '逐车完成并回库后才放行下一车，是串行交通基线，不是并行多车避碰验证' : (result.traffic?.scope ?? '未声明并行多车避碰能力');
  if (result.state === 'canceled') return { value: '执行已取消', tone: 'warn', note: `${scope}；${counts}` };
  if (result.state === 'failed') return { value: '执行 / 检查失败', tone: 'bad', note: `${result.check?.errors?.join('；') || scope}；${counts}` };
  if (!result.traffic || !result.contact_observation || !observed || !result.check) {
    return { value: '交通证据未知', tone: 'warn', note: `历史记录缺少 traffic、check 或有效接触观测，不能按零碰撞处理；${counts}` };
  }
  if (result.check.valid === false || trafficCheck?.valid === false) {
    return { value: '交通检查失败', tone: 'bad', note: `${result.check.errors?.join('；') || trafficCheck?.method || scope}；${counts}` };
  }
  if (!trafficCheck || trafficCheck.valid !== true) {
    return { value: '交通检查未知', tone: 'warn', note: `接触观测已记录，但缺少独立车间距检查；${scope}；${counts}` };
  }
  if (result.traffic.robot_collisions !== true || result.check.valid !== true || result.state !== 'succeeded'
      || result.row_collisions == null || result.robot_contact_events == null) {
    return { value: '交通证据不完整', tone: 'warn', note: `执行状态、物理碰撞开关、总检查或接触计数尚未完整确认；${scope}；${counts}` };
  }
  if (result.row_collisions > 0 || result.robot_contact_events > 0) {
    return { value: '存在接触事件', tone: 'bad', note: `${scope}；${counts}` };
  }
  return {
    value: exclusive ? '串行交通检查通过' : '交通检查通过',
    tone: 'good',
    note: `${scope}；车间碰撞已开启；${trafficCheck.method ?? '独立检查已记录'}；${counts}`,
  };
}
