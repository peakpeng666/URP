import { lazy, Suspense, useEffect, useRef } from 'react';
import { ChartColumn, ShieldCheck, Split, Table2, Waypoints } from 'lucide-react';
import { lastViewHref, useRoute, type Route, type ViewName } from './router';
import { loadMeta, useAsync } from '../data/api';
import { ProvenanceDrawer } from '../components/ProvenanceDrawer';
import { StatusMark } from '../components/Status';
import { ForkMark } from '../components/ForkMark';
import { Overview } from '../views/Overview';
import s from './App.module.css';

const Samples = lazy(() => import('../views/Samples').then((m) => ({ default: m.Samples })));
const ReplayView = lazy(() => import('../views/ReplayView').then((m) => ({ default: m.ReplayView })));
const RiskView = lazy(() => import('../views/RiskView').then((m) => ({ default: m.RiskView })));
const EvidenceView = lazy(() => import('../views/EvidenceView').then((m) => ({ default: m.EvidenceView })));

const NAV: { view: Exclude<ViewName, 'notfound'>; label: string; href: string; icon: typeof ChartColumn }[] = [
  { view: 'overview', label: '结果', href: '#/', icon: ChartColumn },
  { view: 'samples', label: '样本', href: '#/samples', icon: Table2 },
  { view: 'replay', label: '回放', href: '#/replay', icon: Waypoints },
  { view: 'risk', label: '同前缀风险', href: '#/risk', icon: Split },
  { view: 'evidence', label: '证据', href: '#/evidence', icon: ShieldCheck },
];

const TITLES: Record<ViewName, string> = {
  overview: '结果总览',
  samples: '样本',
  replay: '回放',
  risk: '同前缀风险',
  evidence: '证据',
  notfound: '页面不存在',
};

function ValidationChip() {
  const meta = useAsync('meta', () => loadMeta());
  if (meta.status !== 'ready') {
    return (
      <a className={s.statusChip} href="#/evidence">
        <StatusMark status="pending" />
        <span>{meta.status === 'error' ? '数据未载入' : '读取核验状态'}</span>
      </a>
    );
  }
  const v = meta.data.project_validation;
  const status = v?.status === 'PASS' ? 'pass' : v?.status === 'FAIL' ? 'fail' : 'pending';
  const text = status === 'pass' ? '本项目数据核验通过' : status === 'fail' ? '本项目数据核验失败' : '本项目数据核验未完成';
  return (
    <a className={s.statusChip} href="#/evidence" title="查看核验范围与证据">
      <StatusMark status={status} />
      <span>{text}</span>
    </a>
  );
}

function NavLinks({ route, variant }: { route: Route; variant: 'top' | 'bottom' }) {
  return (
    <>
      {NAV.map((item) => {
        const active = route.view === item.view;
        const href = item.view === 'replay' || item.view === 'samples'
          ? active ? route.hash : lastViewHref(item.view)
          : item.href;
        const Icon = item.icon;
        return (
          <a
            key={item.view}
            href={href}
            className={variant === 'top' ? s.navLink : s.bottomLink}
            aria-current={active ? 'page' : undefined}
          >
            <Icon aria-hidden size={variant === 'top' ? 16 : 20} strokeWidth={1.75} />
            <span>{item.label}</span>
          </a>
        );
      })}
    </>
  );
}

export function App() {
  const route = useRoute();
  const mainRef = useRef<HTMLElement>(null);

  useEffect(() => {
    document.title = `${TITLES[route.view]} · BPP 前缀选择科研工作台`;
  }, [route.view]);

  useEffect(() => {
    if ((route.view === 'replay' && route.id) || route.view === 'samples') {
      try {
        sessionStorage.setItem(route.view === 'replay' ? 'bpp:lastReplay' : 'bpp:lastSamples', route.hash);
      } catch {
        /* storage unavailable: ignore */
      }
    }
  }, [route.view, route.id, route.hash]);

  // Move focus to the page heading region on view change (not on param changes).
  const lastView = useRef(route.view);
  useEffect(() => {
    if (lastView.current !== route.view) {
      lastView.current = route.view;
      window.scrollTo({ top: 0 });
      mainRef.current?.focus({ preventScroll: true });
    }
  }, [route.view]);

  return (
    <div className={s.app}>
      <button
        type="button"
        className="skip-link"
        onClick={() => mainRef.current?.focus()}
      >
        跳到主要内容
      </button>
      <header className={s.topbar}>
        <a className={s.brand} href="#/" aria-label="BPP 前缀选择科研工作台，返回结果总览">
          <ForkMark size={22} />
          <span className={s.brandName}>BPP 前缀选择</span>
          <span className={s.brandSub}>科研工作台</span>
        </a>
        <nav className={s.topNav} aria-label="主要视图">
          <NavLinks route={route} variant="top" />
        </nav>
        <ValidationChip />
      </header>
      <main ref={mainRef} className={s.main} tabIndex={-1} aria-label={TITLES[route.view]}>
        <Suspense fallback={<div className={s.viewLoading}>正在载入视图…</div>}>
          {route.view === 'overview' && <Overview />}
          {route.view === 'samples' && <Samples route={route} />}
          {route.view === 'replay' && <ReplayView route={route} />}
          {route.view === 'risk' && <RiskView route={route} />}
          {route.view === 'evidence' && <EvidenceView route={route} />}
          {route.view === 'notfound' && (
            <div className={s.notFound}>
              <h1>没有这个页面</h1>
              <p>
                地址 <code className="mono">{route.hash}</code> 不对应任何视图。<a href="#/">回到结果总览</a>
              </p>
            </div>
          )}
        </Suspense>
      </main>
      <nav className={s.bottomNav} aria-label="主要视图">
        <NavLinks route={route} variant="bottom" />
      </nav>
      <ProvenanceDrawer />
    </div>
  );
}
