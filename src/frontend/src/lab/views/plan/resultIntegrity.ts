import type { Solution } from '../../types';

// Match the gateway's diagnostic-only allowlist. Unknown future metrics fail
// closed; raw records and logs remain available in the audit details.
const DIAGNOSTIC_METRICS = new Set(['process_wall_s', 'wall_s', 'cpu_s', 'length_unit']);

export function withoutInvalidatedResults(run: Solution | null): Solution | null {
  if (!run || run.process?.source_identity_verified !== false) return run;
  const metrics = { ...run.metrics };
  for (const key of Object.keys(metrics)) {
    if (!DIAGNOSTIC_METRICS.has(key)) metrics[key] = null;
  }
  return {
    ...run,
    status: null, routes: [], check: null, map_check: null,
    objective: { value: null, unit: run.objective.unit, lower_bound: null },
    metrics,
  };
}

export function coveragePercent(run: Solution): number | null {
  const fraction = run.metrics.coverage_fraction;
  if (run.state !== 'done' || run.process?.source_identity_verified === false ||
      typeof fraction !== 'number' || !Number.isFinite(fraction)) return null;
  return fraction * 100;
}
