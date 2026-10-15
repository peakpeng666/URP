/** Treat the view as "following the tail" while it is within `slack` px of the bottom. */
export function isNearBottom(scrollTop: number, clientHeight: number, scrollHeight: number, slack = 24): boolean {
  return scrollHeight - (scrollTop + clientHeight) <= slack;
}

/** Index of the element that should receive focus when Tab wraps inside a modal. */
export function wrapFocus(current: number, count: number, backwards: boolean): number {
  if (count <= 0) return -1;
  if (current < 0) return backwards ? count - 1 : 0;
  return backwards ? (current - 1 + count) % count : (current + 1) % count;
}

export const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export const LOG_TAIL = 600;
export const LOG_REFRESH_MS = 1000;

/** Log list entries in display order; a requested log is kept even before the list arrives. */
export function mergeLogNames(listed: { log: string }[] | null | undefined, wanted: string | null | undefined): string[] {
  const names = (listed ?? []).map((l) => l.log);
  if (wanted && !names.includes(wanted)) names.unshift(wanted);
  return names;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || !Number.isFinite(bytes)) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
