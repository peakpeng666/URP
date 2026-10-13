import { useMemo } from 'react';
import { fmt } from '../lib/format';
import s from './NearBins.module.css';

interface BinItem {
  index: number;
  itemNumber: number;
  size: number;
}
interface BinView {
  bin: number;
  count: number;
  remaining: number;
  load: number;
  items?: BinItem[];
}

/**
 * Close-up of the bins around the active one, each a 0–100 column with its
 * actual item segments stacked in placement order. The item just placed is
 * marked; the bin shows pre→post remaining. Reads the kernel's getBin output.
 */
export function NearBins({
  binOf,
  activeBin,
  currentIndex,
  currentSize,
  capacity,
  colorHex,
  slotCount,
  span = 4,
}: {
  binOf: (bin: number) => BinView | null;
  activeBin: number | null;
  currentIndex: number;
  currentSize: number | null;
  capacity: number;
  colorHex: string;
  slotCount: number;
  span?: number;
}) {
  const bins = useMemo(() => {
    if (activeBin === null) return [];
    const start = Math.max(0, activeBin - span);
    // Clamp to the slot count: the kernel's getBin throws past the last slot.
    const end = Math.min(slotCount - 1, activeBin + span);
    const out: BinView[] = [];
    for (let b = start; b <= end; b += 1) {
      const view = binOf(b);
      if (view) out.push(view);
    }
    return out;
  }, [binOf, activeBin, span, currentIndex, slotCount]);

  if (activeBin === null) {
    return <p className={s.idle}>到达第 1 项后，这里显示当前箱附近的装填细节。</p>;
  }

  const colH = 150;
  const colW = 46;
  const gap = 10;
  const width = bins.length * (colW + gap);

  return (
    <div className={s.wrap}>
      <svg className={s.svg} viewBox={`0 0 ${Math.max(width, 1)} ${colH + 44}`} role="img" aria-label="当前箱附近的装填细节">
        {bins.map((bin, i) => {
          const x = i * (colW + gap);
          const isActive = bin.bin === activeBin;
          const items = bin.items ?? [];
          let acc = 0;
          return (
            <g key={bin.bin} transform={`translate(${x}, 8)`}>
              <rect
                x={0}
                y={0}
                width={colW}
                height={colH}
                rx={3}
                className={isActive ? s.binBoxActive : s.binBox}
              />
              {items.map((item) => {
                const segH = (item.size / capacity) * colH;
                const y = colH - acc - segH;
                acc += segH;
                const justPlaced = item.index === currentIndex;
                return (
                  <g key={item.index}>
                    <rect
                      x={2}
                      y={y}
                      width={colW - 4}
                      height={Math.max(1, segH - 1.5)}
                      rx={1.5}
                      fill={justPlaced ? colorHex : hexA(colorHex, 0.4)}
                      stroke={justPlaced ? '#1b2126' : 'transparent'}
                      strokeWidth={justPlaced ? 1.4 : 0}
                    />
                    {segH > 14 && (
                      <text x={colW / 2} y={y + segH / 2 + 4} className={s.segLabel} textAnchor="middle">
                        {item.size}
                      </text>
                    )}
                  </g>
                );
              })}
              <text x={colW / 2} y={colH + 16} className={isActive ? s.binIdActive : s.binId} textAnchor="middle">
                #{bin.bin}
              </text>
              <text x={colW / 2} y={colH + 30} className={s.binRem} textAnchor="middle">
                余 {fmt(bin.remaining, 0)}
              </text>
            </g>
          );
        })}
      </svg>
      {currentSize !== null && activeBin !== null && (
        <p className={s.caption}>
          第 <span className="num">{fmt(currentIndex + 1, 0)}</span> 项（尺寸{' '}
          <span className="num">{fmt(currentSize, 0)}</span>）放入箱 <span className="num">#{activeBin}</span>。
        </p>
      )}
    </div>
  );
}

function hexA(hex: string, alpha: number): string {
  const a = Math.round(alpha * 255).toString(16).padStart(2, '0');
  return `${hex}${a}`;
}
