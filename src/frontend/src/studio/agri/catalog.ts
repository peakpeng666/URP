import { studio } from '../api';
import { AGRI_PATTERNS, patternStatus, type PatternStatus } from './patterns';
import type { AgriTaskPattern } from './taxonomy';

export const STATUS_LABELS: Record<PatternStatus, string> = { runnable: '可构建模板', approx: '近似模板', proposal: '提案（不可提交）' };
export function filterPatterns(environment = '', operation = '', status = '') {
  return AGRI_PATTERNS.filter((p) => (!environment || p.environments.includes(environment))
    && (!operation || p.operation === operation) && (!status || patternStatus(p) === status));
}
export function defaultValues(pattern: AgriTaskPattern): Record<string, unknown> {
  return Object.fromEntries((pattern.runnable?.params ?? []).map((p) => [p.key, p.default]));
}
/** Validate editable values before building; the existing import endpoint validates real geometry/contracts. */
export function buildPattern(pattern: AgriTaskPattern, values: Record<string, unknown>, seed: number) {
  if (patternStatus(pattern) === 'proposal' || !pattern.runnable) throw new Error('提案尚无可执行契约，不能提交求解');
  if (!Number.isSafeInteger(seed) || seed < 0 || seed > 0xffffffff) throw new Error('随机种子须为 0–4294967295 的整数');
  for (const p of pattern.runnable.params) {
    const value = values[p.key];
    if (p.type === 'number' && (typeof value !== 'number' || !Number.isFinite(value)
      || (p.min !== undefined && value < p.min) || (p.max !== undefined && value > p.max))) {
      throw new Error(`${p.label}须为有效数值${p.min !== undefined ? `，至少 ${p.min}` : ''}${p.max !== undefined ? `，至多 ${p.max}` : ''}`);
    }
    if (p.type === 'boolean' && typeof value !== 'boolean') throw new Error(`${p.label}须为开关值`);
    if (p.type === 'select' && !p.options?.some((o) => o.value === value)) throw new Error(`${p.label}选项无效`);
  }
  const built = pattern.runnable.build(values, seed);
  return { ...built, provenance: { ...built.provenance, params: { ...values, pattern_id: pattern.id, builder_version: 'urp.agri.builder/2' } } };
}
export async function importPattern(pattern: AgriTaskPattern, values: Record<string, unknown>, seed: number) {
  // No parallel endpoint or solver: persistence and backend validation use the normal scenario import.
  return studio.importScenario(buildPattern(pattern, values, seed));
}
