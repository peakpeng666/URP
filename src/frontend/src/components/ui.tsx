import type { ReactNode } from 'react';
import { TriangleAlert, RotateCcw } from 'lucide-react';
import { explainLoadError, type AsyncState } from '../data/api';
import s from './ui.module.css';

export function Panel({
  title,
  subtitle,
  aside,
  children,
  id,
  as: Tag = 'section',
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  aside?: ReactNode;
  children: ReactNode;
  id?: string;
  as?: 'section' | 'div' | 'article';
}) {
  return (
    <Tag className={s.panel} id={id}>
      {(title || aside) && (
        <header className={s.panelHead}>
          <div className={s.panelHeadMain}>
            {title && <h2 className={s.panelTitle}>{title}</h2>}
            {subtitle && <p className={s.panelSub}>{subtitle}</p>}
          </div>
          {aside && <div className={s.panelAside}>{aside}</div>}
        </header>
      )}
      {children}
    </Tag>
  );
}

export function Spinner({ label = '载入中…' }: { label?: string }) {
  return (
    <div className={s.spinner} role="status">
      <span className={s.dot} />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  const { title, detail } = explainLoadError(error);
  return (
    <div className={s.error} role="alert">
      <TriangleAlert size={20} aria-hidden className={s.errorIcon} />
      <div className={s.errorBody}>
        <p className={s.errorTitle}>{title}</p>
        {detail && <p className={s.errorDetail}>{detail}</p>}
        {onRetry && (
          <button type="button" className={s.retry} onClick={onRetry}>
            <RotateCcw size={14} aria-hidden /> 重试
          </button>
        )}
      </div>
    </div>
  );
}

/** Renders loading / error / empty uniformly and holds a previous child if asked. */
export function Async<T>({
  state,
  children,
  loading,
  retry,
}: {
  state: AsyncState<T> & { retry?: () => void };
  children: (data: T) => ReactNode;
  loading?: ReactNode;
  retry?: () => void;
}) {
  if (state.status === 'error') return <ErrorState error={state.error} onRetry={retry ?? state.retry} />;
  if (state.status === 'loading') return <>{loading ?? <Spinner />}</>;
  return <>{children(state.data)}</>;
}

export function EmptyState({ title, detail }: { title: string; detail?: ReactNode }) {
  return (
    <div className={s.empty}>
      <p className={s.emptyTitle}>{title}</p>
      {detail && <p className={s.emptyDetail}>{detail}</p>}
    </div>
  );
}
