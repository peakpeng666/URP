/** Shared axis helpers for the Observable Plot charts in the studio. */

/** Seconds as "500 ms" / "2 s" / "1.5 min". */
export function formatSeconds(t: number): string {
  if (t < 1) return `${+(t * 1000).toPrecision(3)} ms`;
  if (t < 120) return `${+t.toPrecision(3)} s`;
  return `${+(t / 60).toPrecision(3)} min`;
}

/** Log-scale time axis labelled only at powers of ten, so minor ticks stay quiet. */
export function logTimeAxis(values: number[], label = '时间') {
  const finite = values.filter((v) => Number.isFinite(v) && v > 0);
  const lo = Math.floor(Math.log10(Math.min(...finite, 1)));
  const hi = Math.ceil(Math.log10(Math.max(...finite, 1)));
  const ticks: number[] = [];
  for (let k = lo; k <= hi; k++) ticks.push(10 ** k);
  return { type: 'log' as const, label, ticks, tickFormat: formatSeconds, grid: true };
}

/** Axis suffix for an objective unit; benchmark units have no physical suffix. */
export function unitSuffix(unit: string | null | undefined): string {
  return unit === 'm' ? ' (m)' : unit === 's' ? ' (s)' : '';
}
