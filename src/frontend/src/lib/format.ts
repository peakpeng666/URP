const MINUS = '−';

/** Fixed decimals with a real minus sign and thousands grouping. */
export function fmt(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const s = Math.abs(value).toLocaleString('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
  return value < 0 && Number(s.replace(/,/g, '')) !== 0 ? `${MINUS}${s}` : s;
}

/** Signed value: +3, −21.45, 0. */
export function fmtSigned(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const body = fmt(Math.abs(value), digits);
  if (Number(body.replace(/,/g, '')) === 0) return fmt(0, digits);
  return value > 0 ? `+${body}` : `${MINUS}${body}`;
}

export function fmtPct(fraction: number | null | undefined, digits = 2): string {
  if (fraction === null || fraction === undefined || Number.isNaN(fraction)) return '—';
  return `${fmt(fraction * 100, digits)}%`;
}

/** Plain-language outcome of a bin difference where negative is favourable. */
export function deltaWord(delta: number | null | undefined): string {
  if (delta === null || delta === undefined) return '无记录';
  if (delta < 0) return `少用 ${fmt(-delta, Number.isInteger(delta) ? 0 : 2)} 箱`;
  if (delta > 0) return `多用 ${fmt(delta, Number.isInteger(delta) ? 0 : 2)} 箱`;
  return '箱数相同';
}

export function shortHash(hash: string | null | undefined, n = 10): string {
  if (!hash) return '—';
  return `${hash.slice(0, n)}…`;
}

export function fmtBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

export function fmtExp(value: number): string {
  if (value === 0) return '0';
  const e = value.toExponential(1).replace('e-', 'e−');
  return e;
}
