/**
 * Brand glyph: one track (BF prefix) reaching a switch point, then forking into
 * two continuations. It is the structural motif of the whole experiment.
 */
export function ForkMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden role="img">
      <path d="M2 12h9" stroke="var(--ink)" strokeWidth="2" strokeLinecap="round" />
      <path d="M11 12c4 0 5-5 9-5" stroke="var(--bf)" strokeWidth="2" strokeLinecap="round" />
      <path d="M11 12c4 0 5 5 9 5" stroke="var(--eoh)" strokeWidth="2" strokeLinecap="round" />
      <circle cx="11" cy="12" r="2.4" fill="var(--panel)" stroke="var(--ink)" strokeWidth="1.6" />
    </svg>
  );
}
