import { CircleCheck, CircleDashed, CircleX, Circle } from 'lucide-react';
import type { CheckStatus } from '../app/store';
import s from './Status.module.css';

const MAP: Record<CheckStatus, { Icon: typeof CircleCheck; label: string; cls: string }> = {
  pass: { Icon: CircleCheck, label: '通过', cls: s.pass },
  pending: { Icon: CircleDashed, label: '待核验', cls: s.pending },
  fail: { Icon: CircleX, label: '失败', cls: s.fail },
  none: { Icon: Circle, label: '未覆盖', cls: s.none },
};

/** Status is always icon + text; color never carries meaning alone. */
export function StatusMark({ status, size = 15 }: { status: CheckStatus; size?: number }) {
  const { Icon, label, cls } = MAP[status];
  return (
    <span className={`${s.mark} ${cls}`} role="img" aria-label={label}>
      <Icon size={size} strokeWidth={2} aria-hidden />
    </span>
  );
}

export function StatusTag({ status, children }: { status: CheckStatus; children: React.ReactNode }) {
  const { Icon, label, cls } = MAP[status];
  return (
    <span className={`${s.tag} ${cls}`}>
      <Icon size={14} strokeWidth={2} aria-hidden />
      <span>{children ?? label}</span>
    </span>
  );
}
