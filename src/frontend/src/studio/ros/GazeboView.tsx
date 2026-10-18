/**
 * The running Gazebo Fortress world in the browser: gzweb (Open Robotics' web renderer) connects
 * to the session's ign-launch WebSocket server and streams the scene, models and poses.
 */
import { useEffect, useId, useRef, useState } from 'react';
import { Box, Camera, Crosshair, Maximize2 } from 'lucide-react';
import { Button, EmptyState } from '../../lab/ui';
import { useLive } from './live';
import s from './ros.module.css';

interface GzScene {
  camera: { position: { set(x: number, y: number, z: number): void }; lookAt(x: number, y: number, z: number): void };
  controls?: { target: { set(x: number, y: number, z: number): void } };
}
interface SceneManager {
  scene?: GzScene;
  resize(): void;
  destroy(): void;
  resetView(): void;
  follow(name: string): void;
  thirdPersonFollow(name: string): void;
  snapshot(): void;
  getConnectionStatus(): string;
  getConnectionError(): string | null;
  getResourceStatus(): { total: number; ready: number; failed: string[] };
}

export function GazeboView() {
  const live = useLive();
  const gz = live.web.gazebo;
  const id = `gz-${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  const box = useRef<HTMLDivElement>(null);
  const manager = useRef<SceneManager | null>(null);
  const [status, setStatus] = useState('disconnected');
  const [error, setError] = useState<string | null>(null);
  const [follow, setFollow] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [resources, setResources] = useState<{ total: number; ready: number; failed: string[] }>({ total: 0, ready: 0, failed: [] });
  const bounds = gz?.bounds;

  /** Look at the whole field (gzweb's own reset view sits at the world origin). */
  const overview = () => {
    const sc = manager.current?.scene;
    if (!sc?.controls) return false;
    if (!bounds) {
      manager.current?.resetView();
      return true;
    }
    const [x0, y0, x1, y1] = bounds;
    const cx = (x0 + x1) / 2;
    const cy = (y0 + y1) / 2;
    const span = Math.max(x1 - x0, y1 - y0, 10);
    sc.camera.position.set(cx, cy - span * 0.85, span * 0.7);
    sc.controls.target.set(cx, cy, 0);
    sc.camera.lookAt(cx, cy, 0); // gzweb's z-up orbit controls do not re-aim the camera on update()
    return true;
  };

  useEffect(() => {
    if (!gz?.url || !box.current) return;
    let alive = true;
    const el = box.current;
    let Manager: (new (c: object) => SceneManager) | null = null;
    setStatus('connecting');
    setError(null);
    setFollow(null);
    setResources({ total: 0, ready: 0, failed: [] });
    // gzweb looks its element up by id, so it can only start once the dock has attached this panel.
    const create = () => {
      if (!alive || manager.current || !Manager || !el.isConnected || el.clientWidth === 0) return;
      try {
        manager.current = new Manager({ elementId: id, websocketUrl: gz.url, websocketKey: gz.key });
        setError(null);
      } catch (cause) {
        setStatus('error');
        setError(`初始化失败：${(cause as Error).message}`);
      }
    };
    void import('gzweb').then((m) => {
      Manager = m.SceneManager as unknown as new (c: object) => SceneManager;
      create();
    }).catch((cause: Error) => {
      if (!alive) return;
      setStatus('error');
      setError(`模块加载失败：${cause.message}`);
    });
    const ro = new ResizeObserver(() => {
      create();
      try {
        if (el.querySelector('canvas')) manager.current?.resize();
      } catch {
        /* scene not set up yet */
      }
    });
    ro.observe(el);
    let framed = 0; // re-frame a few times: gzweb resets its camera while the scene streams in
    const t = window.setInterval(() => {
      try {
        const st = manager.current?.getConnectionStatus() ?? 'disconnected';
        setStatus(st);
        const assets = manager.current?.getResourceStatus();
        if (assets) setResources(assets);
        if (st === 'error') setError(manager.current?.getConnectionError() ?? 'Gazebo 通信失败');
        if (st === 'ready' && framed < 6 && overview()) framed++;
      } catch (cause) {
        setStatus('error');
        setError(`连接状态读取失败：${(cause as Error).message}`);
      }
    }, 600);
    return () => {
      alive = false;
      ro.disconnect();
      window.clearInterval(t);
      const owned = manager.current;
      manager.current = null;
      try { owned?.destroy(); } finally { el.replaceChildren(); }
    };
  }, [gz?.url, gz?.key, id, retry]); // eslint-disable-line react-hooks/exhaustive-deps

  const vehicles = live.kind === 'field' ? live.field?.vehicles ?? [] : [];
  const robots = live.kind === 'robot' ? [{ name: 'turtlebot4', label: 'TurtleBot4', color: '#1d1d1f' }] : vehicles;
  const toggleFollow = (name: string) => {
    const next = follow === name ? null : name;
    setFollow(next);
    if (next) manager.current?.thirdPersonFollow(next);
    else overview();
  };

  if (!gz?.url) {
    const fieldRunning = live.kind === 'field' && !!live.field?.running;
    const fieldErrors = live.kind === 'field' ? live.field?.errors ?? [] : [];
    return (
      <div className={s.empty}>
        <EmptyState icon={Box}
          title={fieldRunning ? (fieldErrors.length ? 'Gazebo 会话失联' : 'Gazebo 网页桥不可用') : 'Gazebo 未运行'}
          detail={fieldRunning
            ? `田间会话仍在运行或未能确认结束，但当前没有可用的 gzweb 地址。${fieldErrors.join('；') || '请检查会话错误与网页桥状态，不要把此状态当作正常停止。'}`
            : '田间多车仿真或 TurtleBot4 仿真启动后，这里直接显示 Gazebo Fortress 的实时场景（gzweb）。原生 Gazebo 窗口仍可在仿真面板单独打开。'} />
      </div>
    );
  }
  const statusText = error
    ? `连接失败：${error}`
    : ({ ready: '已连接', connecting: '连接中', disconnected: '已断开', error: '连接失败' } as Record<string, string>)[status] ?? `未知状态（${status}）`;
  return (
    <div className={s.view}>
      <div id={id} ref={box} className={s.gz} />
      <div className={s.hud}>
        <div className={s.hudRow}>
          <span className={s.dot} data-s={status === 'ready' && !error && !resources.failed.length ? 'connected' : status === 'error' || status === 'disconnected' || error || resources.failed.length ? 'closed' : 'connecting'} />
          <span className={s.hudTitle}>Gazebo · {gz.world}</span>
          <span className={s.hudMeta}>gzweb · {statusText}</span>
          {resources.total > 0 && <span className={s.hudMeta} role={resources.failed.length ? 'alert' : undefined}
            title={resources.failed.join('\n')}>资源 {resources.ready}/{resources.total}{resources.failed.length ? ` · ${resources.failed.length} 项失败或超时，场景不完整` : resources.ready < resources.total ? ' · 加载中' : ''}</span>}
        </div>
        <div className={s.chips}>
          {(status === 'error' || status === 'disconnected' || resources.failed.length > 0) && <Button size="sm" onClick={() => setRetry(n => n + 1)}>重新连接</Button>}
          <Button size="sm" icon={Maximize2} onClick={() => { setFollow(null); overview(); }}>全景</Button>
          <Button size="sm" icon={Camera} onClick={() => manager.current?.snapshot()}>截图</Button>
          {robots.map((v) => (
            <button key={v.name} type="button" className={s.chip} data-on={follow === v.name || undefined} onClick={() => toggleFollow(v.name)}>
              {'color' in v && <i className={s.swatch} style={{ background: v.color }} />}
              <Crosshair size={11} />跟随 {v.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
