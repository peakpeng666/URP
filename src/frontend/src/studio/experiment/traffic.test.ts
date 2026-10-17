import { describe, expect, it } from 'vitest';
import { trafficStatus, type TrafficEvidence } from './traffic';

const passed: TrafficEvidence = {
  state: 'succeeded',
  traffic: { policy: 'exclusive_mission_v1', robot_collisions: true, scope: '整段任务互斥预约' },
  check: { valid: true, errors: [], traffic: { valid: true, method: '同步分段线性插值', pairs: [] } },
  contact_observation: { status: 'observed', count_unit: 'unique simulation timestamp + collision-body pair' },
  row_collision_shapes: 35,
  row_collisions: 0,
  robot_contact_events: 0,
};

describe('traffic evidence presentation', () => {
  it('describes the serial baseline without claiming parallel collision avoidance', () => {
    const status = trafficStatus(passed);
    expect(status.value).toBe('串行交通检查通过');
    expect(status.tone).toBe('good');
    expect(status.note).toContain('不是并行多车避碰验证');
    expect(status.note).toContain('作物行几何 35 个');
    expect(status.note).toContain('作物行接触消息 0');
  });

  it('treats missing observations and null counts as unknown, never as zero collisions', () => {
    const missing = structuredClone(passed);
    delete missing.contact_observation;
    delete missing.row_collisions;
    const status = trafficStatus(missing);
    expect(status.value).toBe('交通证据未知');
    expect(status.note).toContain('不能按零碰撞处理');
    expect(status.note).toContain('作物行接触消息 未知');
  });

  it('distinguishes failed checks and cancellation', () => {
    const failed = structuredClone(passed);
    failed.state = 'failed';
    failed.check!.valid = false;
    failed.check!.errors = ['contact observed'];
    expect(trafficStatus(failed)).toMatchObject({ value: '执行 / 检查失败', tone: 'bad' });
    expect(trafficStatus({ ...passed, state: 'canceled' })).toMatchObject({ value: '执行已取消', tone: 'warn' });
  });

  it('does not turn an observed stream without an independent traffic check into a pass', () => {
    const unchecked = structuredClone(passed);
    delete unchecked.check!.traffic;
    expect(trafficStatus(unchecked)).toMatchObject({ value: '交通检查未知', tone: 'warn' });
  });
});
