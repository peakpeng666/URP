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
// getRandomValues also works on the existing LAN HTTP deployment (randomUUID does not).
function uniqueScenarioSuffix(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6]! & 0x0f) | 0x40;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

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
  return { ...built, id: `agri-${pattern.id.slice(0, 20)}-${uniqueScenarioSuffix()}`, provenance: { ...built.provenance, params: { ...values, pattern_id: pattern.id, builder_version: 'urp.agri.builder/3' } } };
}
const importsInFlight = new Map<string, ReturnType<typeof studio.importScenario>>();
export async function importPattern(pattern: AgriTaskPattern, values: Record<string, unknown>, seed: number) {
  const built = buildPattern(pattern, values, seed);
  const key = JSON.stringify([pattern.id, seed, pattern.runnable!.params.map((p) => [p.key, values[p.key]])]);
  const existing = importsInFlight.get(key);
  if (existing) return existing;
  // Share a still-pending identical submission even if the panel was closed and reopened.
  const request = studio.importScenario(built).then((scenario) => {
    if (!scenario || typeof scenario.id !== 'string' || !/^[a-z0-9][a-z0-9_.-]{1,63}$/.test(scenario.id)
      || typeof scenario.title !== 'string') throw new Error('保存响应缺少有效场景标识，请先在已有场景中核对保存结果');
    return scenario;
  });
  importsInFlight.set(key, request);
  try { return await request; }
  finally { if (importsInFlight.get(key) === request) importsInFlight.delete(key); }
}

/** One request per mounted card; navigation is invalidated even after an away/back round trip. */
export function createImportGuard() {
  let pending = false;
  let epoch = 0;
  return {
    begin(): number | null { if (pending) return null; pending = true; return epoch; },
    invalidateNavigation() { epoch += 1; },
    canNavigate(ticket: number) { return pending && ticket === epoch; },
    finish() { pending = false; },
  };
}
