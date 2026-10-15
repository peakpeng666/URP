import { Component, type ErrorInfo, type ReactNode } from 'react';
import { RotateCcw } from 'lucide-react';
import { Button, Notice, Toolbar } from '../ui';
import s from './Shell.module.css';

/** A view inside the window: unified (sticky, translucent) toolbar over inset content. */
export function Page({
  title,
  subtitle,
  actions,
  children,
  bodyClassName,
  flush = false,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  bodyClassName?: string;
  /** Body without padding, for views that lay out their own page. */
  flush?: boolean;
}) {
  return (
    <div className={s.page}>
      <div className={s.toolbarBar}>
        <Toolbar title={title} subtitle={subtitle}>
          {actions && <div className={s.toolbarActions}>{actions}</div>}
        </Toolbar>
      </div>
      <div className={[flush ? s.pageFlush : s.pageBody, bodyClassName].filter(Boolean).join(' ')}>{children}</div>
    </div>
  );
}

/** Keeps one failing view from taking down the whole window. */
export class ViewErrorBoundary extends Component<{ children: ReactNode; name: string }, { error: Error | null }> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`视图 ${this.props.name} 渲染失败`, error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <Page title={this.props.name} subtitle="视图渲染出错">
        <Notice tone="error">
          <strong>此视图渲染失败：</strong>
          <span className="mono">{this.state.error.message}</span>
          <div style={{ marginTop: 8 }}>
            <Button size="sm" icon={RotateCcw} onClick={() => this.setState({ error: null })}>
              重试
            </Button>
          </div>
        </Notice>
      </Page>
    );
  }
}
