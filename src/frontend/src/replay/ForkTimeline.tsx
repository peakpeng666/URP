import { useCallback, useId, useRef } from 'react';
import { Pause, Play, RotateCcw, SkipBack, SkipForward, StepBack, StepForward } from 'lucide-react';
import { fmt } from '../lib/format';
import s from './ForkTimeline.module.css';

const JUMPS = [
  { t: 0, label: '0' },
  { t: 499, label: '499' },
  { t: 500, label: '500' },
  { t: 501, label: '501' },
];

export function ForkTimeline({
  t,
  total,
  boundary,
  playing,
  speed,
  speeds,
  onSeek,
  onStep,
  onTogglePlay,
  onReset,
  onSpeed,
}: {
  t: number;
  total: number;
  boundary: number;
  playing: boolean;
  speed: number;
  speeds: readonly number[];
  onSeek: (t: number) => void;
  onStep: (delta: number) => void;
  onTogglePlay: () => void;
  onReset: () => void;
  onSpeed: (speed: number) => void;
}) {
  const trackRef = useRef<HTMLDivElement>(null);
  const sliderId = useId();
  const dragging = useRef(false);

  const posFromEvent = useCallback(
    (clientX: number) => {
      const el = trackRef.current;
      if (!el) return t;
      const rect = el.getBoundingClientRect();
      const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
      return Math.round(ratio * total);
    },
    [t, total],
  );

  const onPointerDown = (e: React.PointerEvent) => {
    dragging.current = true;
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    onSeek(posFromEvent(e.clientX));
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (dragging.current) onSeek(posFromEvent(e.clientX));
  };
  const onPointerUp = (e: React.PointerEvent) => {
    dragging.current = false;
    (e.target as HTMLElement).releasePointerCapture?.(e.pointerId);
  };

  const pct = (v: number) => `${(v / total) * 100}%`;
  const phase = t < boundary ? 'prefix' : t === boundary ? 'decision' : 'continuation';

  return (
    <div className={s.timeline}>
      <div className={s.controls}>
        <div className={s.transport}>
          <IconBtn label="回到开始（0）" onClick={() => onSeek(0)}>
            <SkipBack size={17} />
          </IconBtn>
          <IconBtn label="后退 10 项" onClick={() => onStep(-10)}>
            <StepBack size={17} />
          </IconBtn>
          <button type="button" className={s.playBtn} onClick={onTogglePlay} aria-label={playing ? '暂停' : '播放'}>
            {playing ? <Pause size={19} /> : <Play size={19} />}
          </button>
          <IconBtn label="前进 10 项" onClick={() => onStep(10)}>
            <StepForward size={17} />
          </IconBtn>
          <IconBtn label="跳到结束（5000）" onClick={() => onSeek(total)}>
            <SkipForward size={17} />
          </IconBtn>
          <IconBtn label="重置到开始" onClick={onReset}>
            <RotateCcw size={16} />
          </IconBtn>
        </div>

        <div className={s.readout}>
          <span className={s.phaseTag} data-phase={phase}>
            {phase === 'prefix' ? '前 500 项' : phase === 'decision' ? '决策点' : '续行'}
          </span>
          <label className={s.posLabel} htmlFor={`${sliderId}-num`}>
            已处理
          </label>
          <input
            id={`${sliderId}-num`}
            className={`${s.posInput} num`}
            type="number"
            min={0}
            max={total}
            value={t}
            onChange={(e) => {
              const v = Number(e.target.value);
              if (Number.isFinite(v)) onSeek(Math.min(total, Math.max(0, Math.round(v))));
            }}
          />
          <span className={s.posTotal}>/ {fmt(total, 0)} 项</span>
        </div>

        <div className={s.speed} role="group" aria-label="播放倍速">
          <span className={s.speedLabel}>倍速</span>
          {speeds.map((sp) => (
            <button
              key={sp}
              type="button"
              className={s.speedBtn}
              data-active={sp === speed || undefined}
              onClick={() => onSpeed(sp)}
            >
              {sp}×
            </button>
          ))}
        </div>
      </div>

      <div className={s.trackRow}>
        <div
          ref={trackRef}
          className={s.track}
          role="slider"
          tabIndex={0}
          aria-label="回放进度（已处理项数）"
          aria-valuemin={0}
          aria-valuemax={total}
          aria-valuenow={t}
          aria-valuetext={`已处理 ${fmt(t, 0)} 项，共 ${fmt(total, 0)} 项`}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onKeyDown={(e) => {
            const map: Record<string, number> = {
              ArrowLeft: -1,
              ArrowRight: 1,
              PageDown: -100,
              PageUp: 100,
            };
            if (e.key in map) {
              e.preventDefault();
              onStep(e.shiftKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight') ? map[e.key] * 10 : map[e.key]);
            } else if (e.key === 'Home') {
              e.preventDefault();
              onSeek(0);
            } else if (e.key === 'End') {
              e.preventDefault();
              onSeek(total);
            }
          }}
        >
          <div className={s.trackBase} />
          <div className={s.trackPrefix} style={{ width: pct(boundary) }} />
          <div className={s.trackFill} style={{ width: pct(t) }} />
          <div className={s.boundaryMark} style={{ left: pct(boundary) }} aria-hidden>
            <span className={s.boundaryFlag}>第 {boundary} 项 · 道岔</span>
          </div>
          <div className={s.handle} style={{ left: pct(t) }} aria-hidden />
        </div>
      </div>

      <div className={s.jumps}>
        <span className={s.jumpsLabel}>直达</span>
        {JUMPS.map((j) => (
          <button
            key={j.t}
            type="button"
            className={s.jumpBtn}
            data-active={t === j.t || undefined}
            onClick={() => onSeek(j.t)}
          >
            {j.label}
          </button>
        ))}
        <button type="button" className={s.jumpBtn} data-active={t === total || undefined} onClick={() => onSeek(total)}>
          {fmt(total, 0)}
        </button>
      </div>
    </div>
  );
}

function IconBtn({ label, onClick, children }: { label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" className={s.iconBtn} onClick={onClick} aria-label={label} title={label}>
      {children}
    </button>
  );
}
