import { useState } from 'react';
import type { Preview, PreviewIssue } from './preview';
import type { XY } from './geometry';

type Layer = 'plots' | 'obstacles' | 'tasks' | 'depots' | 'issues';
const LAYER_LABEL: Record<Layer, string> = { plots: '地块', obstacles: '障碍', tasks: '服务对象', depots: '库点/卸货点', issues: '问题标记' };

/** 米制坐标预览：y 轴向上（与场景坐标一致），左下角标原点，带比例尺与图例；形状和颜色同时编码类型。 */
export function PreviewMap({ preview: p, issues, title }: { preview: Preview; issues: PreviewIssue[]; title: string }) {
  const [on, setOn] = useState<Record<Layer, boolean>>({ plots: true, obstacles: true, tasks: true, depots: true, issues: true });
  const [picked, setPicked] = useState<string>('');
  const [x0, y0, x1, y1] = p.bbox;
  const pad = Math.max(x1 - x0, y1 - y0) * 0.06 || 1;
  const w = x1 - x0 + 2 * pad; const h = y1 - y0 + 2 * pad;
  const tx = (q: XY) => `${q[0] - x0 + pad},${y1 + pad - q[1]}`;
  const pts = (r: XY[]) => r.map(tx).join(' ');
  const unit = w / 80;
  const bad = new Set(issues.map((i) => i.target).filter(Boolean));
  const scale = niceScale(w / 4);
  const pickedTask = p.tasks.find((t) => `task:${t.id}` === picked);
  return <figure style={{ margin: '8px 0' }}>
    <svg role="img" aria-label={`${title} 几何预览`} viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', maxHeight: 320, background: '#fafaf7', border: '1px solid #ccc', touchAction: 'manipulation' }}>
      <polygon points={pts(p.boundary)} fill="#eef5e6" stroke={bad.has('boundary') ? '#c62828' : '#4d6b2f'} strokeWidth={unit * 0.3} strokeDasharray={bad.has('boundary') ? `${unit} ${unit / 2}` : undefined} />
      {on.plots && p.plots.map((pl) => <polygon key={pl.id} points={pts(pl.polygon)} fill="none" stroke="#7a9a4a" strokeWidth={unit * 0.15} strokeDasharray={`${unit * 0.6} ${unit * 0.3}`}><title>地块 {pl.name}</title></polygon>)}
      {on.obstacles && p.obstacles.map((o) => <polygon key={o.id} points={pts(o.polygon)} fill="url(#hatch)" stroke={bad.has(o.id) ? '#c62828' : '#555'} strokeWidth={unit * 0.2}><title>障碍 {o.id}（{o.kind}）</title></polygon>)}
      <defs><pattern id="hatch" width={unit} height={unit} patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width={unit} height={unit} fill="#ddd" /><line x1={0} y1={0} x2={0} y2={unit} stroke="#888" strokeWidth={unit * 0.3} /></pattern></defs>
      {on.tasks && p.tasks.map((t) => { const [cx, cy] = tx(t.xy).split(',').map(Number); const err = bad.has(`task:${t.id}`);
        return <g key={t.id} onClick={() => setPicked(`task:${t.id}`)} style={{ cursor: 'pointer' }}>
          <circle cx={cx} cy={cy} r={unit * (picked === `task:${t.id}` ? 1.1 : 0.7)} fill={err ? '#c62828' : '#1565c0'} stroke="#fff" strokeWidth={unit * 0.15} />
          {err && on.issues && <text x={cx + unit} y={cy - unit} fontSize={unit * 1.6} fill="#c62828">!</text>}
          <title>{t.label}{t.demand !== undefined ? `，需求 ${t.demand}` : ''}，({t.xy[0]}, {t.xy[1]}) m</title></g>; })}
      {on.depots && p.depots.map((d, i) => { const [cx, cy] = tx(d).split(',').map(Number); return <rect key={`d${i}`} x={cx - unit} y={cy - unit} width={unit * 2} height={unit * 2} fill="#6d4c41"><title>库点 {i + 1}</title></rect>; })}
      {on.depots && p.unload.map((d, i) => { const [cx, cy] = tx(d).split(',').map(Number); return <polygon key={`u${i}`} points={`${cx},${cy - unit * 1.2} ${cx + unit},${cy + unit * 0.8} ${cx - unit},${cy + unit * 0.8}`} fill="#ef6c00"><title>卸货点 {i + 1}</title></polygon>; })}
      {p.start && (() => { const [cx, cy] = tx(p.start).split(',').map(Number); return <rect x={cx - unit} y={cy - unit} width={unit * 2} height={unit * 2} fill="#6d4c41"><title>起点</title></rect>; })()}
      {(() => { const [ox, oy] = tx([0, 0]).split(',').map(Number); return <g><line x1={ox} y1={oy} x2={ox + unit * 3} y2={oy} stroke="#000" strokeWidth={unit * 0.15} /><line x1={ox} y1={oy} x2={ox} y2={oy - unit * 3} stroke="#000" strokeWidth={unit * 0.15} /><text x={ox + unit * 0.4} y={oy - unit * 0.4} fontSize={unit * 1.3}>原点 (0,0) · x→ y↑</text></g>; })()}
      <g transform={`translate(${pad * 0.4},${h - pad * 0.3})`}><line x1={0} y1={0} x2={scale} y2={0} stroke="#000" strokeWidth={unit * 0.3} /><text x={0} y={-unit * 0.5} fontSize={unit * 1.3}>{scale} m</text></g>
    </svg>
    <figcaption style={{ fontSize: 12 }}>
      {p.kind === 'coverage' ? `覆盖作业：幅宽 ${p.swathWidth ?? '未知'} m，地头 ${p.headlandWidth ?? '未知'} m。` : `${p.tasks.length} 个服务对象，${p.depots.length} 个库点，${p.unload.length} 个卸货点，车体半径 ${p.robotRadius ?? '未知'} m。`}
      {' '}范围 {(x1 - x0).toFixed(1)} × {(y1 - y0).toFixed(1)} m。图例：圆为服务对象，方块为库点或起点，三角为卸货点，斜线填充为障碍，虚线为地块，红色和感叹号为问题。
      <span role="group" aria-label="图层" style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {(Object.keys(LAYER_LABEL) as Layer[]).map((k) => <label key={k}><input type="checkbox" checked={on[k]} onChange={(e) => setOn({ ...on, [k]: e.target.checked })} />{LAYER_LABEL[k]}</label>)}
      </span>
      {pickedTask && <span role="status">已选：{pickedTask.label}，坐标 ({pickedTask.xy[0]}, {pickedTask.xy[1]}) m{pickedTask.demand !== undefined ? `，需求 ${pickedTask.demand}` : ''}</span>}
    </figcaption>
    {issues.length > 0 && <ul aria-label="预检问题" style={{ fontSize: 12 }}>{issues.map((i, k) => <li key={k} style={{ color: i.level === 'error' ? '#c62828' : '#8a6d00' }}>
      <button type="button" style={{ all: 'unset', cursor: 'pointer', textDecoration: 'underline' }} onClick={() => i.target && setPicked(i.target)}>{i.level === 'error' ? '错误' : '提醒'}：{i.message}</button></li>)}</ul>}
  </figure>;
}

function niceScale(target: number): number {
  if (!(target > 0)) return 1;
  const p = 10 ** Math.floor(Math.log10(target));
  return [1, 2, 5, 10].map((m) => m * p).reduce((best, v) => (v <= target ? v : best), p);
}
