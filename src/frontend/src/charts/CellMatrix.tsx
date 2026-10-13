import { useId, useMemo, useState } from 'react';
import type { Cell } from '../data/types';
import { FAMILY_LABEL, FAMILY_ORDER, ORDER_LABEL, ORDER_ORDER } from '../data/labels';
import { fmtSigned, deltaWord } from '../lib/format';
import { useTooltip, TooltipLayer } from '../components/Tooltip';
import s from './charts.module.css';

/**
 * 18 confirmation cells (6 families × 3 orders), colored by selector−SBS mean
 * (diverging: green saves, red harms, neutral zero). Every cell shows its
 * number, so color is a secondary channel. Keyboard navigable grid.
 */
export function CellMatrix({ cells, onSelect }: { cells: Cell[]; onSelect?: (cell: Cell) => void }) {
  const titleId = useId();
  const { pos, show, hide } = useTooltip();
  const [active, setActive] = useState<string | null>(null);

  const grid = useMemo(() => {
    const byKey = new Map(cells.map((c) => [`${c.family}|${c.order}`, c]));
    return FAMILY_ORDER.map((family) => ORDER_ORDER.map((order) => byKey.get(`${family}|${order}`) ?? null));
  }, [cells]);

  const maxAbs = useMemo(
    () => Math.max(1, ...cells.map((c) => Math.abs(c.selector_minus_SBS))),
    [cells],
  );

  const color = (delta: number) => {
    if (delta === 0) return 'var(--mid)';
    const t = Math.min(1, Math.abs(delta) / maxAbs);
    const alpha = 0.12 + t * 0.6;
    return delta < 0
      ? `color-mix(in srgb, var(--save) ${Math.round(alpha * 100)}%, var(--panel))`
      : `color-mix(in srgb, var(--harm) ${Math.round(alpha * 100)}%, var(--panel))`;
  };

  return (
    <figure className={s.figure} aria-labelledby={titleId}>
      <figcaption id={titleId} className={s.matrixCaption}>
        18 个确认单元（6 尺寸族 × 3 到达顺序），格值为该单元 6 流的选择器 − SBS 平均箱数；负数（绿）表示节省。
      </figcaption>
      <div className={s.scrollX}>
        <table className={s.matrix} role="grid">
          <thead>
            <tr>
              <th scope="col" className={s.matrixCorner}>
                尺寸族 ＼ 顺序
              </th>
              {ORDER_ORDER.map((o) => (
                <th key={o} scope="col" className={s.matrixColHead}>
                  {ORDER_LABEL[o]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {FAMILY_ORDER.map((family, i) => (
              <tr key={family}>
                <th scope="row" className={s.matrixRowHead}>
                  {FAMILY_LABEL[family]}
                </th>
                {grid[i].map((cell, j) => {
                  if (!cell) return <td key={j} className={s.matrixCell} />;
                  const key = `${family}|${ORDER_ORDER[j]}`;
                  const delta = cell.selector_minus_SBS;
                  return (
                    <td key={j} className={s.matrixTd}>
                      <button
                        type="button"
                        className={`${s.cellBtn} num`}
                        style={{ background: color(delta) }}
                        data-active={active === key || undefined}
                        aria-label={`${FAMILY_LABEL[family]} ${ORDER_LABEL[ORDER_ORDER[j]]}：${deltaWord(delta)}；选择 BF ${cell.BF_selections} 次、切 EoH ${cell.EoH_selections} 次`}
                        onClick={(e) => {
                          onSelect?.(cell);
                          const rect = e.currentTarget.getBoundingClientRect();
                          setActive(key);
                          show(rect.left + rect.width / 2, rect.top, <CellTip cell={cell} />);
                        }}
                        onMouseMove={(e) => show(e.clientX, e.clientY, <CellTip cell={cell} />)}
                        onMouseLeave={hide}
                        onFocus={(e) => {
                          const rect = e.currentTarget.getBoundingClientRect();
                          show(rect.left + rect.width / 2, rect.top, <CellTip cell={cell} />);
                        }}
                        onBlur={hide}
                      >
                        {fmtSigned(delta, delta === 0 || Number.isInteger(delta) ? 0 : 2)}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <TooltipLayer pos={pos} />
    </figure>
  );
}

function CellTip({ cell }: { cell: Cell }) {
  return (
    <div>
      <div>
        <span className="v">{fmtSigned(cell.selector_minus_SBS, 2)}</span> 箱均值（{deltaWord(cell.selector_minus_SBS)}）
      </div>
      <div className="k">
        {FAMILY_LABEL[cell.family]} · {ORDER_LABEL[cell.order]} · {cell.n} 流
      </div>
      <div className="k">
        选择：继续 BF {cell.BF_selections} 次，切 EoH {cell.EoH_selections} 次 · 胜/平/负 {cell.wins}/{cell.ties}/{cell.losses}
      </div>
    </div>
  );
}
