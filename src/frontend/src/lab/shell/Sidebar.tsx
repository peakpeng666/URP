import { useEffect, useRef, useState } from 'react';
import { Menu, Sprout, X } from 'lucide-react';
import type { Route } from '../../app/router';
import { lab, useGatewayConnected, useLabResource } from '../api';
import { StatusDot } from '../ui';
import type { SimState } from '../types';
import { NAV_SECTIONS, VIEW_TITLES, navHref, sectionOf } from './nav';
import { simPhaseLabel, simPhaseTone } from './labels';
import { fallbackPoll, useReconnectReload } from './hooks';
import s from './Shell.module.css';

function NavList({ route, onNavigate }: { route: Route; onNavigate?: () => void }) {
  return (
    <>
      {NAV_SECTIONS.map((section) => (
        <div key={section.id} className={s.navSection} role="group" aria-labelledby={`nav-${section.id}`}>
          <h2 id={`nav-${section.id}`} className={s.navSectionTitle}>
            {section.title}
          </h2>
          <ul className={s.navItems}>
            {section.items.map((item) => {
              const Icon = item.icon;
              const active = route.view === item.view;
              return (
                <li key={item.view}>
                  <a
                    href={navHref(item, route)}
                    className={s.navItem}
                    aria-current={active ? 'page' : undefined}
                    onClick={onNavigate}
                  >
                    <Icon size={16} strokeWidth={1.8} aria-hidden />
                    <span>{item.label}</span>
                  </a>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </>
  );
}

function StatusFooter({ connected, sim }: { connected: boolean; sim: SimState | null }) {
  const phase = connected || sim ? sim?.phase ?? null : null;
  return (
    <div className={s.footer}>
      <div className={s.footRow} title={connected ? '事件流已连接 127.0.0.1:4100' : '事件流未连接；页面每 5 秒重试读取'}>
        <StatusDot tone={connected ? 'ok' : 'error'} />
        <span>{connected ? '网关已连接' : '网关未连接'}</span>
        <span className={s.footMeta}>4100</span>
      </div>
      <a className={s.footRow} href="#/sim" title="仿真会话阶段">
        <StatusDot tone={connected ? simPhaseTone(phase) : 'idle'} />
        <span>仿真 · {connected ? simPhaseLabel(phase) : '状态未知'}</span>
        {connected && sim?.world && <span className={s.footMeta}>{sim.world}</span>}
      </a>
    </div>
  );
}

function Brand() {
  return (
    <a className={s.brand} href="#/" aria-label="URP 科研面板，返回概览">
      <span className={s.appIcon} aria-hidden>
        <Sprout size={17} strokeWidth={2} />
      </span>
      <span className={s.brandText}>
        <span className={s.brandName}>URP 科研面板</span>
        <span className={s.brandSub}>农业机器人路径规划</span>
      </span>
    </a>
  );
}

/**
 * macOS source-list sidebar (translucent, inset). Below 900 px it collapses
 * into a top bar whose menu shows the same sections.
 */
export function Sidebar({ route }: { route: Route }) {
  const connected = useGatewayConnected();
  const sim = useLabResource<SimState>('shell:sim', () => lab.simState(), {
    event: 'sim_state',
    pollMs: fallbackPoll(connected),
  });
  useReconnectReload(connected, sim.reload);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => setMenuOpen(false), [route.hash]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMenuOpen(false);
        menuButton.current?.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    menuRef.current?.querySelector<HTMLElement>('a[aria-current="page"], a')?.focus();
    return () => document.removeEventListener('keydown', onKey);
  }, [menuOpen]);

  const simData = sim.error && !connected ? null : sim.data;
  const section = sectionOf(route.view);

  return (
    <>
      <aside className={s.sidebar} aria-label="侧边栏">
        <div className={s.sidebarPanel}>
          <Brand />
          <nav className={s.nav} aria-label="主要视图">
            <NavList route={route} />
          </nav>
          <StatusFooter connected={connected} sim={simData} />
        </div>
      </aside>

      <header className={s.mobileBar}>
        <button
          ref={menuButton}
          type="button"
          className={s.menuButton}
          aria-expanded={menuOpen}
          aria-controls="lab-nav-menu"
          aria-label={menuOpen ? '关闭导航菜单' : '打开导航菜单'}
          onClick={() => setMenuOpen((v) => !v)}
        >
          {menuOpen ? <X size={18} aria-hidden /> : <Menu size={18} aria-hidden />}
        </button>
        <div className={s.mobileTitle}>
          <span className={s.mobileSection}>{section?.title ?? 'URP 科研面板'}</span>
          <span className={s.mobileView}>{VIEW_TITLES[route.view]}</span>
        </div>
        <span className={s.mobileStatus} title={connected ? '网关已连接' : '网关未连接'}>
          <StatusDot tone={connected ? 'ok' : 'error'} />
          <span>{connected ? '已连接' : '未连接'}</span>
        </span>
      </header>
      {menuOpen && (
        <div className={s.menuScrim} role="presentation" onClick={() => setMenuOpen(false)}>
          <div
            ref={menuRef}
            id="lab-nav-menu"
            className={s.menuPanel}
            onClick={(e) => e.stopPropagation()}
          >
            <nav aria-label="主要视图">
              <NavList route={route} onNavigate={() => setMenuOpen(false)} />
            </nav>
            <StatusFooter connected={connected} sim={simData} />
          </div>
        </div>
      )}
    </>
  );
}
