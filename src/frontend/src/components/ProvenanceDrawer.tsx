import { useEffect, useRef } from 'react';
import { ExternalLink, X } from 'lucide-react';
import { closeProvenance, provenanceStore, useStore, type CheckScope } from '../app/store';
import { fmtBytes, shortHash } from '../lib/format';
import { StatusMark } from './Status';
import s from './ProvenanceDrawer.module.css';

const SCOPE_LABEL: Record<CheckScope, string> = {
  historical: '包内历史审计',
  project: '本项目核验',
  browser: '此浏览器复算',
};

/**
 * Evidence drawer: value → meaning → derivation → source files → verification
 * scope. Every number elsewhere can open one of these. Checks are grouped by
 * who performed them so "historical PASS" is never mistaken for project PASS.
 */
export function ProvenanceDrawer() {
  const open = useStore(provenanceStore, (st) => st.open);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeProvenance();
    };
    document.addEventListener('keydown', onKey);
    const first = panelRef.current?.querySelector<HTMLElement>('button, a, [tabindex]');
    first?.focus();
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  // Simple focus trap so keyboard users stay inside the drawer.
  useEffect(() => {
    if (!open) return undefined;
    const onFocus = (e: FocusEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        panelRef.current.querySelector<HTMLElement>('button, a, [tabindex]')?.focus();
      }
    };
    document.addEventListener('focusin', onFocus);
    return () => document.removeEventListener('focusin', onFocus);
  }, [open]);

  if (!open) return null;

  return (
    <div className={s.scrim} onClick={closeProvenance} role="presentation">
      <aside
        ref={panelRef}
        className={s.panel}
        role="dialog"
        aria-modal="true"
        aria-label={`出处：${open.title}`}
        onClick={(e) => e.stopPropagation()}
      >
        <header className={s.head}>
          <div>
            <p className={s.eyebrow}>出处与核验</p>
            <h2 className={s.title}>{open.title}</h2>
          </div>
          <button type="button" className={s.close} onClick={closeProvenance} aria-label="关闭出处面板">
            <X size={18} aria-hidden />
          </button>
        </header>

        <div className={s.body}>
          {open.value !== undefined && (
            <p className={s.value}>
              <span className="num">{open.value}</span>
            </p>
          )}
          {open.meaning && (
            <section className={s.section}>
              <h3 className={s.h3}>含义</h3>
              <p className={s.text}>{open.meaning}</p>
            </section>
          )}
          {open.derivation && (
            <section className={s.section}>
              <h3 className={s.h3}>如何得到</h3>
              <p className={s.text}>{open.derivation}</p>
            </section>
          )}

          {open.checks && open.checks.length > 0 && (
            <section className={s.section}>
              <h3 className={s.h3}>核验范围</h3>
              <ul className={s.checks}>
                {open.checks.map((c, i) => (
                  <li key={i} className={s.check}>
                    <StatusMark status={c.status} />
                    <div>
                      <span className={s.checkScope}>{SCOPE_LABEL[c.scope]}</span>
                      <span className={s.checkLabel}>{c.label}</span>
                      {c.detail && <span className={s.checkDetail}>{c.detail}</span>}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className={s.section}>
            <h3 className={s.h3}>来源文件</h3>
            <ul className={s.sources}>
              {open.sources.map((src, i) => (
                <li key={i} className={s.source}>
                  <div className={s.sourceTop}>
                    <code className={`mono ${s.path}`}>{src.ref.path}</code>
                    <a
                      className={s.openLink}
                      href={`#/evidence?file=${encodeURIComponent(src.ref.path)}`}
                      onClick={closeProvenance}
                    >
                      查看 <ExternalLink size={12} aria-hidden />
                    </a>
                  </div>
                  {src.field && <p className={s.field}>字段：{src.field}</p>}
                  {src.note && <p className={s.note}>{src.note}</p>}
                  <dl className={s.meta}>
                    <div>
                      <dt>SHA-256</dt>
                      <dd className="mono" title={src.ref.sha256}>
                        {shortHash(src.ref.sha256, 16)}
                      </dd>
                    </div>
                    <div>
                      <dt>大小</dt>
                      <dd className="num">{fmtBytes(src.ref.bytes)}</dd>
                    </div>
                  </dl>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </aside>
    </div>
  );
}
