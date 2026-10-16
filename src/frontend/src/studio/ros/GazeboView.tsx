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
}

export function GazeboView() {
  const live = useLive();
  const gz = live.web.gazebo;
  const id = `gz-${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  const box = useRef<HTMLDivElement>(null);
  const manager = useRef<SceneManager | null>(null);
  const [status, setStatus] = useState('disconnected');
  const [follow, setFollow] = useState<string | null>(null);
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
    // gzweb looks its element up by id, so it can only start once the dock has attached this panel.
    const create = () => {
      if (!alive || manager.current || !Manager || !el.isConnected || el.clientWidth === 0) return;
      manager.current = new Manager({ elementId: id, websocketUrl: gz.url, websocketKey: gz.key });
    };
    void import('gzweb').then((m) => {
      Manager = m.SceneManager as unknown as new (c: object) => SceneManager;
      create();
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
      const st = manager.current?.getConnectionStatus() ?? 'disconnected';
      setStatus(st);
      if (st === 'ready' && framed < 6 && overview()) framed++;
    }, 600);
    return () => {
      alive = false;
      ro.disconnect();
      window.clearInterval(t);
      manager.current?.destroy();
      manager.current = null;
      el.replaceChildren();
    };
  }, [gz?.url, gz?.key, id]); // eslint-disable-line react-hooks/exhaustive-deps

  const vehicles = live.kind === 'field' ? live.field?.vehicles ?? [] : [];
  const robots = live.kind === 'robot' ? [{ name: 'turtlebot4', label: 'TurtleBot4', color: '#1d1d1f' }] : vehicles;
  const toggleFollow = (name: string) => {
    const next = follow === name ? null : name;
    setFollow(next);
    if (next) manager.current?.thirdPersonFollow(next);
    else overview();
  };

  if (!gz?.url) {
    return (
      <div className={s.empty}>
        <EmptyState icon={Box} title="Gazebo 未运行" detail="田间多车仿真或 TurtleBot4 仿真启动后，这里直接显示 Gazebo Fortress 的实时场景（gzweb）。原生 Gazebo 窗口仍可在仿真面板单独打开。" />
      </div>
    );
  }
  return (
    <div className={s.view}>
      <div id={id} ref={box} className={s.gz} />
      <div className={s.hud}>
        <div className={s.hudRow}>
          <span className={s.dot} data-s={status === 'ready' ? 'connected' : status === 'error' ? 'closed' : 'connecting'} />
          <span className={s.hudTitle}>Gazebo · {gz.world}</span>
          <span className={s.hudMeta}>gzweb · {status === 'ready' ? '已连接' : status === 'error' ? '连接失败' : '连接中'}</span>
        </div>
        <div className={s.chips}>
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
