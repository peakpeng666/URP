import { FileSearch } from 'lucide-react';
import { openProvenance, type Provenance } from '../app/store';
import s from './EvidenceButton.module.css';

/** Small inline trigger that opens the provenance drawer for a value. */
export function EvidenceButton({ provenance, label }: { provenance: Provenance; label?: string }) {
  return (
    <button
      type="button"
      className={s.btn}
      onClick={(e) => openProvenance(provenance, e.currentTarget)}
      aria-label={label ?? `查看“${provenance.title}”的出处与核验范围`}
      title="出处与核验"
    >
      <FileSearch size={14} aria-hidden strokeWidth={1.75} />
    </button>
  );
}
