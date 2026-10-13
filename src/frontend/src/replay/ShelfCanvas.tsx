import { useEffect, useMemo, useRef } from 'react';
import type { RunRecord } from '../data/types';
import { ShelfModel } from './shelfModel';
import { useElementSize } from '../lib/useElementSize';
import { fmt } from '../lib/format';
import s from './ShelfCanvas.module.css';

/**
 * Skyline of all opened bins (index order), each a column whose height is its
 * current load. The bitmap is sized to the bins opened SO FAR (it grows with
 * the processed state, never to the final count), and lives in a fixed-height
 * scroll viewport that auto-follows the active bin — so no opened bin is ever
 * clipped, and the initial layout reveals nothing about the future result.
 */
export function ShelfCanvas({
  run,
  t,
  colorHex,
  label,
  boundary,
}: {
  run: RunRecord;
  t: number;
  colorHex: string;
  label: string;
  boundary: number;
}) {
  const [wrapRef, { width }] = useElementSize<HTMLDivElement>();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const model = useMemo(() => new ShelfModel(run), [run]);

  const geom = useMemo(() => {
    const binW = 4;
    const rowH = 20;
    const w = Math.max(240, Math.floor(width || 240));
    const binsPerRow = Math.max(20, Math.floor((w - 2) / binW));
    return { binW, rowH, binsPerRow, w };
  }, [width]);

  // Header counts are read from the validated record at the current t, so they
  // never lag the canvas (which draws in an effect after render).
  const usedBins = t > 0 ? run.used_bins_after[t - 1] : 0;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    model.seek(t);

    const { binW, rowH, binsPerRow, w } = geom;
    const openedRows = Math.max(1, Math.ceil((model.maxBin + 1) / binsPerRow));
    const cssH = openedRows * rowH + 6;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    if (canvas.width !== Math.floor(w * dpr) || canvas.height !== Math.floor(cssH * dpr)) {
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(cssH * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${cssH}px`;
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, cssH);

    const barMax = rowH - 5;
    const activeBin = t > 0 ? model.binAt(t - 1) : -1;

    for (let bin = 0; bin <= model.maxBin; bin += 1) {
      if (model.counts[bin] === 0) continue; // only draw actually-opened bins
      const col = bin % binsPerRow;
      const row = Math.floor(bin / binsPerRow);
      const x = col * binW;
      const baseY = row * rowH + rowH - 3;
      const barH = Math.max(1, (model.loads[bin] / model.capacity) * barMax);
      ctx.fillStyle = bin === activeBin ? colorHex : hexWithAlpha(colorHex, 0.5);
      ctx.fillRect(x, baseY - barH, Math.max(1, binW - 1), barH);
    }

    if (activeBin >= 0) {
      const col = activeBin % binsPerRow;
      const row = Math.floor(activeBin / binsPerRow);
      const x = col * binW + (binW - 1) / 2;
      const yTop = row * rowH;
      ctx.fillStyle = '#1b2126';
      ctx.beginPath();
      ctx.moveTo(x, yTop + 1);
      ctx.lineTo(x - 3, yTop - 3);
      ctx.lineTo(x + 3, yTop - 3);
      ctx.closePath();
      ctx.fill();
      // Keep the active bin's row in view within the fixed-height scroller.
      const wrap = wrapRef.current;
      if (wrap) {
        const rowTop = row * rowH;
        const rowBottom = rowTop + rowH + 6;
        if (rowTop < wrap.scrollTop) wrap.scrollTop = Math.max(0, rowTop - rowH);
        else if (rowBottom > wrap.scrollTop + wrap.clientHeight) wrap.scrollTop = rowBottom - wrap.clientHeight;
      }
    }
    void boundary;
  }, [model, t, geom, colorHex, boundary, wrapRef]);

  return (
    <div className={s.shelf}>
      <div className={s.shelfHead}>
        <span className={s.shelfLabel} style={{ color: colorHex }}>
          <span className={s.swatch} style={{ background: colorHex }} aria-hidden />
          {label}
        </span>
        <span className={`${s.shelfCount} num`}>
          已用 {fmt(usedBins, 0)} 箱 · 已处理 {fmt(t, 0)} / {fmt(run.items.length, 0)} 项
        </span>
      </div>
      <div className={s.canvasWrap} ref={wrapRef}>
        <canvas
          ref={canvasRef}
          className={s.canvas}
          role="img"
          aria-label={`${label}装箱概览：已处理 ${fmt(t, 0)} 项，已开 ${fmt(usedBins, 0)} 个箱。每根竖条是一个已开箱，高度表示装入体积；可滚动查看全部箱。`}
        />
      </div>
    </div>
  );
}

function hexWithAlpha(hex: string, alpha: number): string {
  const a = Math.round(alpha * 255).toString(16).padStart(2, '0');
  return `${hex}${a}`;
}
