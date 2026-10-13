import type { Policy } from '../../data/types';
import { POLICY_LABEL } from '../../data/labels';
import s from './PolicyPicker.module.css';

const OPTIONS_A: { value: string; label: string }[] = [
  { value: 'SELECTOR', label: POLICY_LABEL.SELECTOR },
  { value: 'SBS', label: '训练 SBS' },
  { value: 'BF', label: POLICY_LABEL.BF },
  { value: 'BF_then_EoH', label: POLICY_LABEL.BF_then_EoH },
  { value: 'published_EoH', label: POLICY_LABEL.published_EoH },
];

const OPTIONS_B = [{ value: '', label: '不比较' }, ...OPTIONS_A];

/** Choose which run(s) to replay. A is required; B optional for comparison. */
export function PolicyPicker({
  policyA,
  policyB,
  available,
  sbs,
  onChange,
}: {
  policyA: Policy;
  policyB: Policy | null;
  available: Policy[];
  sbs: Policy;
  onChange: (a: string, b: string | null) => void;
}) {
  const aValue = policyA;
  const bValue = policyB ?? '';
  // SBS is an alias for the training-SBS branch, available whenever that branch ran.
  const has = (value: string) => value === '' || available.includes(value === 'SBS' ? sbs : (value as Policy));
  const suffix = (value: string) => (value === 'SBS' ? `（${POLICY_LABEL[sbs]}）` : has(value) ? '' : '（本集合未运行）');

  return (
    <div className={s.picker}>
      <label className={s.field}>
        <span className={s.label}>A</span>
        <select className={s.select} value={aValue} onChange={(e) => onChange(e.target.value, policyB)} aria-label="主运行策略">
          {OPTIONS_A.map((o) => (
            <option key={o.value} value={o.value} disabled={!has(o.value)}>
              {o.label}
              {suffix(o.value)}
            </option>
          ))}
        </select>
      </label>
      <span className={s.vs}>对比</span>
      <label className={s.field}>
        <span className={s.label}>B</span>
        <select className={s.select} value={bValue} onChange={(e) => onChange(policyA, e.target.value || null)} aria-label="对比运行策略">
          {OPTIONS_B.map((o) => (
            <option key={o.value} value={o.value} disabled={!has(o.value)}>
              {o.label}
              {suffix(o.value)}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
