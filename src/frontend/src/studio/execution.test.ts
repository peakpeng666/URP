import { describe, expect, it } from 'vitest';
import { LabApiError } from '../lab/api';
import { executionErrorMessage, unacceptedPlanReason } from './execution';
import type { FleetInstance } from './types';

describe('execution admission recovery', () => {
  it('keeps 422 codes visible and offers an explicit recovery path', () => {
    for (const code of ['heterogeneous_fleet_execution', 'curvature_constrained_execution', 'unsupported_vehicle_asset']) {
      const message = executionErrorMessage(new LabApiError('后端拒绝', code, 422));
      expect(message).toContain('422');
      expect(message).toContain(code);
      expect(message).toContain('恢复');
    }
  });

  it('explains 409 asset conflicts without rewriting the historical snapshot', () => {
    const message = executionErrorMessage(new LabApiError('哈希不一致', 'asset_version_conflict', 409));
    expect(message).toContain('409');
    expect(message).toContain('显式重新绑定');
    expect(message).toContain('历史方案');
  });

  it('retains blocked resupply input while withholding execution promotion', () => {
    const instance = { unload_points: [[4, 5]] } as FleetInstance;
    expect(unacceptedPlanReason(instance)).toContain('B1/B2');
    expect(instance.unload_points).toEqual([[4, 5]]);
  });
});
