/** Asset preview: 2D for maps (with coordinate confirmation and image calibration), 3D for vehicles and facilities. */
import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Crosshair, Eye, EyeOff, Layers, Ruler, Trash2 } from 'lucide-react';
import { Button, EmptyState, Input, Notice, Segmented, Select, Spinner } from '../../lab/ui';
import type { XY } from '../../lab/types';
import { useStudio } from '../store';
import {
  applyAffine, assetsApi, assetUrl, invertAffine, svgMatrix, type Affine, type Asset, type AssetVersion, type Calibration, type MapFrame,
  type PlanningGeometry,
} from './api';
import { MapView2D } from './MapView2D';
import { ModelViewer, type Layers as ModelLayers, type Measured, type ModelSource } from './ModelViewer';
import { useAssets } from './store';
import s from './assets.module.css';

const ROLE_STYLE: Record<string, { fill: string; stroke: string; label: string }> = {
  boundary: { fill: 'rgba(140,115,84,0.18)', stroke: '#6d5a40', label: '边界' }, plot: { fill: 'rgba(98,160,72,0.28)', stroke: '#3f6b2a', label: '地块' },
  obstacle: { fill: 'rgba(90,110,150,0.45)', stroke: '#3c4a66', label: '障碍' }, nogo: { fill: 'rgba(255,69,58,0.25)', stroke: '#c0392b', label: '禁行区' },
  road: { fill: 'rgba(160,160,160,0.35)', stroke: '#7d7d7d', label: '道路' }, headland: { fill: 'rgba(200,170,110,0.3)', stroke: '#9a7b3c', label: '地头' },
  task: { fill: '#0a84ff', stroke: '#0a84ff', label: '任务点' }, depot: { fill: '#ff9f0a', stroke: '#b36b00', label: '车库' },
  unload: { fill: '#bf5af2', stroke: '#8e3cb8', label: '卸货 / 补给' }, row: { fill: 'none', stroke: '#3f6b2a', label: '作物行' },
  unknown: { fill: 'rgba(120,120,120,0.2)', stroke: '#888', label: '未识别' },
};

export function AssetPreview() {
  const { asset, version } = useAssets();
  if (!asset) return <EmptyState icon={Layers} title="选择一个资产" detail="地图在这里确认坐标、原点和单位（图片做标定）；车辆与设施在三维里核对外观、规划足迹和碰撞几何。" />;
  const ver = asset.versions.find((v) => v.v === (version ?? asset.current)) ?? asset.versions[asset.versions.length - 1];
  if (asset.kind === 'map') {
    if (asset.subtype === 'ros_grid') return <RosGridPreview key={`${asset.id}@${ver.v}`} asset={asset} ver={ver} />;
    if (asset.subtype === 'vector') return <VectorPreview key={`${asset.id}@${ver.v}`} asset={asset} ver={ver} />;
    if (asset.subtype === 'image') return <ImagePreview key={`${asset.id}@${ver.v}`} asset={asset} ver={ver} />;
    return <WorldFacts ver={ver} />;
  }
  if (asset.kind === 'vehicle' || asset.kind === 'facility') return <ModelPreview key={`${asset.id}@${ver.v}`} asset={asset} ver={ver} />;
  return <ScenarioFacts ver={ver} />;
}

/* ------------------------------------------------------------ ROS grid -- */
function frameFrom(f: MapFrame, patch: { resolution?: number; origin?: [number, number, number] }): MapFrame {
  const res = patch.resolution ?? f.resolution;
  const [ox, oy, yaw] = patch.origin ?? f.origin;
  const c = Math.cos(yaw), sn = Math.sin(yaw), h = f.height_px, w = f.width_px;
  const affine: Affine = [[c * res, sn * res, ox - sn * h * res], [sn * res, -c * res, oy + c * h * res]];
  const pts = [[0, 0], [w, 0], [0, h], [w, h]].map(([u, v]) => applyAffine(affine, u, v));
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  return { ...f, resolution: res, origin: [ox, oy, yaw], width_m: w * res, height_m: h * res, affine, bounds: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] };
}

function useApplyMeta(asset: Asset) {
  const st = useAssets();
  const notify = useStudio((x) => x.notify);
  return async (meta: Record<string, unknown>, okText: string) => {
    try {
      const a = await assetsApi.meta(asset.id, st.version ?? asset.current, meta);
      st.apply(a);
      notify('ok', a.current !== (st.version ?? asset.current) ? `${okText}（原版本已锁定，生成 v${a.current}）` : okText);
    } catch (e) {
      notify('error', (e as Error).message);
    }
  };
}

function RosGridPreview({ asset, ver }: { asset: Asset; ver: AssetVersion }) {
  const meta = ver.meta;
  const frame = meta.frame!;
  const save = useApplyMeta(asset);
  const [edit, setEdit] = useState({ resolution: String(frame.resolution), ox: String(frame.origin[0]), oy: String(frame.origin[1]), yaw: String(frame.origin[2]) });
  const [geom, setGeom] = useState<PlanningGeometry | null>(null);
  const [geomBusy, setGeomBusy] = useState(false);
  const [unknownAs, setUnknownAs] = useState<'obstacle' | 'free'>('obstacle');
  const draft = useMemo(() => frameFrom(frame, { resolution: Number(edit.resolution) || frame.resolution, origin: [Number(edit.ox) || 0, Number(edit.oy) || 0, Number(edit.yaw) || 0] }), [frame, edit]);
  const changed = draft.resolution !== frame.resolution || draft.origin.some((v, i) => v !== frame.origin[i]);
  const confirmed = !!meta.confirmed?.frame;
  const loadGeom = async () => {
    setGeomBusy(true);
    try {
      setGeom(await assetsApi.geometry(asset.id, ver.v, { unknown_as: unknownAs }));
    } catch (e) {
      useStudio.getState().notify('error', (e as Error).message);
    } finally {
      setGeomBusy(false);
    }
  };
  const inv = useMemo(() => invertAffine(draft.affine), [draft]);
  return (
    <MapView2D bounds={draft.bounds} fitKey={`${asset.id}@${ver.v}`}
      cursorExtra={(p) => { const [u, v] = applyAffine(inv, p[0], p[1]); return `像素 (${Math.floor(u)}, ${Math.floor(v)})`; }}
      overlay={(
        <>
          <div className={s.glass} style={{ maxWidth: 520 }}>
            <div className={s.row}>
              <b>ROS 栅格地图</b>
              <span className={s.chip} data-tone={confirmed ? 'green' : 'orange'}>{confirmed ? '坐标已确认' : '坐标待确认'}</span>
              {ver.locked && <span className={s.chip}>v{ver.v} 已锁定</span>}
            </div>
            <div className={s.row} style={{ marginTop: 6 }}>
              <label className={s.hint}>分辨率</label><Input style={{ width: 70 }} value={edit.resolution} onChange={(e) => setEdit({ ...edit, resolution: e.target.value })} />
              <label className={s.hint}>原点 x</label><Input style={{ width: 70 }} value={edit.ox} onChange={(e) => setEdit({ ...edit, ox: e.target.value })} />
              <label className={s.hint}>y</label><Input style={{ width: 70 }} value={edit.oy} onChange={(e) => setEdit({ ...edit, oy: e.target.value })} />
              <label className={s.hint}>yaw</label><Input style={{ width: 60 }} value={edit.yaw} onChange={(e) => setEdit({ ...edit, yaw: e.target.value })} />
            </div>
            <p className={s.hint} style={{ marginTop: 4 }}>
              m/像素 · 原点是左下角像素在 map 坐标系里的位置（米）· 单位米 · 坐标系 map（x 向右、y 向上，与 Nav2 / 规划一致）。
              图 {draft.width_px}×{draft.height_px} 像素 = {draft.width_m.toFixed(2)}×{draft.height_m.toFixed(2)} m。
            </p>
            <div className={s.row}>
              {changed && <Button size="sm" onClick={() => void save({ frame: draft, confirmed: { frame: false } }, '已更新分辨率 / 原点')}>应用修改</Button>}
              {!confirmed && !changed && <Button size="sm" variant="primary" icon={CheckCircle2} onClick={() => void save({ confirmed: { frame: true } }, '坐标、原点与单位已确认')}>确认坐标与单位</Button>}
              <span className={s.grow} />
              <Select aria-label="未知区" value={unknownAs} onChange={(e) => setUnknownAs(e.target.value as 'obstacle' | 'free')}>
                <option value="obstacle">未知区按障碍</option><option value="free">未知区按可通行</option>
              </Select>
              <Button size="sm" icon={Eye} disabled={geomBusy} onClick={() => void loadGeom()}>{geomBusy ? '提取中…' : '预览规划几何'}</Button>
              {geom && <Button size="sm" variant="plain" icon={EyeOff} onClick={() => setGeom(null)} />}
            </div>
          </div>
          {geom && <div className={s.glass}>{geom.notes.join('；')}</div>}
          <div className={`${s.glass} ${s.legend}`}><span><i style={{ background: '#f6f6f4', boxShadow: 'inset 0 0 0 1px #ccc' }} />空闲</span><span><i style={{ background: '#2c2e34' }} />占据</span><span><i style={{ background: '#c4c9d2' }} />未知</span>{geom && <><span><i style={{ background: '#30b158' }} />规划边界</span><span><i style={{ background: '#ff453a' }} />规划障碍</span></>}</div>
        </>
      )}>
      {() => (
        <>
          <image href={assetUrl(asset.id, ver.v, 'derived/preview.png') ?? ''} width={draft.width_px} height={draft.height_px}
            transform={svgMatrix(draft.affine)} style={{ imageRendering: 'pixelated' }} preserveAspectRatio="none" />
          {geom?.boundary && <polygon points={geom.boundary.map((p) => p.join(',')).join(' ')} fill="none" stroke="#30b158" strokeWidth={2} vectorEffect="non-scaling-stroke" />}
          {geom?.obstacles.map((o) => <polygon key={o.id} points={o.polygon.map((p) => p.join(',')).join(' ')} fill="rgba(255,69,58,0.35)" stroke="#ff453a" strokeWidth={1} vectorEffect="non-scaling-stroke" />)}
        </>
      )}
    </MapView2D>
  );
}

/* -------------------------------------------------------------- vector -- */
type Feature = { id: string | number; geometry: { type: string; coordinates: any }; properties: Record<string, any> }; // eslint-disable-line @typescript-eslint/no-explicit-any

function pathOf(rings: XY[][]) {
  return rings.map((r) => `M${r.map((p) => p.join(',')).join('L')}Z`).join('');
}

function FeatureShape({ f }: { f: Feature }) {
  const role = f.properties.role ?? 'unknown';
  const st = ROLE_STYLE[role] ?? ROLE_STYLE.unknown;
  const g = f.geometry;
  const common = { stroke: st.stroke, strokeWidth: 1.5, vectorEffect: 'non-scaling-stroke' as const };
  if (g.type === 'Polygon') return <path d={pathOf(g.coordinates)} fill={st.fill} fillRule="evenodd" {...common} />;
  if (g.type === 'MultiPolygon') return <>{g.coordinates.map((p: XY[][], i: number) => <path key={i} d={pathOf(p)} fill={st.fill} fillRule="evenodd" {...common} />)}</>;
  if (g.type === 'LineString') return <polyline points={g.coordinates.map((p: XY) => p.join(',')).join(' ')} fill="none" {...common} strokeWidth={2} />;
  if (g.type === 'MultiLineString') return <>{g.coordinates.map((l: XY[], i: number) => <polyline key={i} points={l.map((p) => p.join(',')).join(' ')} fill="none" {...common} />)}</>;
  if (g.type === 'Point') return <circle cx={g.coordinates[0]} cy={g.coordinates[1]} r={1.2} fill={st.fill} stroke="#fff" strokeWidth={1} vectorEffect="non-scaling-stroke" />;
  return null;
}

function VectorPreview({ asset, ver }: { asset: Asset; ver: AssetVersion }) {
  const [feats, setFeats] = useState<Feature[] | null>(null);
  const save = useApplyMeta(asset);
  useEffect(() => {
    fetch(assetUrl(asset.id, ver.v, ver.meta.features ?? 'derived/features_local.json') ?? '').then((r) => r.json()).then((d) => setFeats(d.features)).catch(() => setFeats([]));
  }, [asset.id, ver.v, ver.meta.features]);
  const tf = ver.meta.transform ?? {};
  const sum = ver.meta.summary ?? {};
  const confirmed = !!ver.meta.confirmed?.frame;
  const roles = Object.keys(sum.roles ?? {});
  if (!feats) return <div style={{ padding: 14 }}><Spinner /></div>;
  return (
    <MapView2D bounds={sum.bounds ?? null} fitKey={`${asset.id}@${ver.v}`}
      overlay={(
        <>
          <div className={s.glass} style={{ maxWidth: 560 }}>
            <div className={s.row}><b>矢量田块 / 道路</b><span className={s.chip} data-tone={confirmed ? 'green' : 'orange'}>{confirmed ? '坐标已确认' : '坐标待确认'}</span></div>
            <p className={s.hint} style={{ marginTop: 4 }}>
              源坐标 {tf.source_crs}（{ver.meta.crs?.source}）→ {tf.method === 'utm' ? `UTM 投影 ${tf.projected_crs}` : tf.projected_crs}，
              局部原点 = 投影坐标 ({tf.origin_projected?.map((v: number) => v.toFixed(2)).join(', ')})，x 向东、y 向北，单位米{tf.assumed ? '（用户确认坐标已是米）' : ''}。
              范围 {sum.size_m?.[0]} × {sum.size_m?.[1]} m，孔洞 {sum.holes} 个。
            </p>
            {!confirmed && <Button size="sm" variant="primary" icon={CheckCircle2} onClick={() => void save({ confirmed: { frame: true } }, '坐标换算已确认')}>确认坐标换算</Button>}
          </div>
          <div className={`${s.glass} ${s.legend}`}>{roles.map((r) => <span key={r}><i style={{ background: (ROLE_STYLE[r] ?? ROLE_STYLE.unknown).stroke }} />{(ROLE_STYLE[r] ?? ROLE_STYLE.unknown).label} {sum.roles[r]}</span>)}</div>
        </>
      )}>
      {() => feats.map((f) => <FeatureShape key={String(f.id)} f={f} />)}
    </MapView2D>
  );
}

/* --------------------------------------------------------------- image -- */
function ImagePreview({ asset, ver }: { asset: Asset; ver: AssetVersion }) {
  const meta = ver.meta;
  const [w, h] = meta.size_px ?? [1000, 1000];
  const save = useApplyMeta(asset);
  const notify = useStudio((x) => x.notify);
  const existing = meta.calibration as Calibration | null;
  const [mode, setMode] = useState<'points' | 'distance'>('distance');
  const [points, setPoints] = useState<{ px: XY; world: [string, string] }[]>(existing?.control?.map((c) => ({ px: c.px, world: [String(c.world[0]), String(c.world[1])] as [string, string] })) ?? []);
  const [dist, setDist] = useState<{ p1?: XY; p2?: XY; meters: string; origin?: XY; rot: string }>({ meters: '', rot: '0' });
  const [result, setResult] = useState<Calibration | null>(existing ?? null);
  const pixelFrame: Affine = [[1, 0, 0], [0, -1, h]];  // before calibration: 1 unit = 1 pixel, image upright
  const shown = result?.matrix ?? pixelFrame;
  const inv = useMemo(() => invertAffine(shown), [shown]);
  const corners = [[0, 0], [w, 0], [0, h], [w, h]].map(([u, v]) => applyAffine(shown, u, v));
  const bounds: [number, number, number, number] = [Math.min(...corners.map((p) => p[0])), Math.min(...corners.map((p) => p[1])), Math.max(...corners.map((p) => p[0])), Math.max(...corners.map((p) => p[1]))];
  const pick = (p: XY) => {
    const [u, v] = applyAffine(inv, p[0], p[1]);
    if (u < 0 || v < 0 || u > w || v > h) return;
    const px: XY = [Math.round(u * 10) / 10, Math.round(v * 10) / 10];
    if (mode === 'points') setPoints((pts) => [...pts, { px, world: ['', ''] }]);
    else if (!dist.p1) setDist({ ...dist, p1: px, origin: dist.origin ?? px });
    else if (!dist.p2) setDist({ ...dist, p2: px });
    else setDist({ ...dist, origin: px });
  };
  const solve = async () => {
    try {
      let r: Calibration;
      if (mode === 'distance') {
        if (!dist.p1 || !dist.p2 || !(Number(dist.meters) > 0)) throw new Error('先在图上点两点，并填写它们之间的真实距离（米）');
        r = await assetsApi.calibrate({ known_distance: { p1: dist.p1, p2: dist.p2, distance_m: Number(dist.meters), origin_px: dist.origin, rotation_deg: Number(dist.rot) || 0 } });
      } else {
        const pts = points.filter((p) => p.world[0] !== '' && p.world[1] !== '').map((p) => ({ px: p.px, world: [Number(p.world[0]), Number(p.world[1])] as XY }));
        r = await assetsApi.calibrate({ points: pts, model: pts.length >= 4 ? 'affine' : 'similarity' });
        r.control = pts;
      }
      setResult(r);
    } catch (e) {
      notify('error', (e as Error).message);
    }
  };
  const toWorldPx = (px: XY) => applyAffine(shown, px[0], px[1]);
  return (
    <MapView2D bounds={bounds} fitKey={`${asset.id}@${ver.v}:${result ? 'cal' : 'px'}`} onClick={pick}
      cursorExtra={(p) => { const [u, v] = applyAffine(inv, p[0], p[1]); return `像素 (${u.toFixed(0)}, ${v.toFixed(0)})`; }}
      overlay={(
        <div className={s.glass} style={{ maxWidth: 560 }}>
          <div className={s.row}>
            <b>图片标定</b>
            <span className={s.chip} data-tone={meta.confirmed?.calibration ? 'green' : 'orange'}>{meta.confirmed?.calibration ? '已标定' : '未标定'}</span>
            <span className={s.chip} data-tone="red">只作背景，不可直接通行</span>
            <span className={s.grow} />
            <Segmented value={mode} onChange={setMode} options={[{ value: 'distance', label: '已知距离' }, { value: 'points', label: '控制点' }]} />
          </div>
          {mode === 'distance' ? (
            <>
              <p className={s.hint} style={{ marginTop: 4 }}>在图上点两点（如比例尺两端、已知长度的田埂），填它们的真实距离；第三次点击设原点（默认第一点）。图片上方按 +y（北），可加旋转。</p>
              <div className={s.row}>
                <span className={s.mono}>A {dist.p1 ? dist.p1.join(',') : '—'} · B {dist.p2 ? dist.p2.join(',') : '—'} · 原点 {dist.origin ? dist.origin.join(',') : '—'}</span>
                <Input style={{ width: 80 }} placeholder="距离 m" value={dist.meters} onChange={(e) => setDist({ ...dist, meters: e.target.value })} />
                <Input style={{ width: 64 }} placeholder="旋转°" value={dist.rot} onChange={(e) => setDist({ ...dist, rot: e.target.value })} />
                <Button size="sm" variant="plain" icon={Trash2} onClick={() => setDist({ meters: dist.meters, rot: dist.rot })} />
              </div>
            </>
          ) : (
            <>
              <p className={s.hint} style={{ marginTop: 4 }}>点击图上的控制点，再填它们在局部坐标里的位置（米）。2–3 点用相似变换，≥ 4 点用最小二乘仿射并给出每点残差。</p>
              {points.map((p, i) => (
                <div key={i} className={s.cpRow}>
                  <span>#{i + 1}</span><span className={s.mono}>{p.px.join(', ')}</span>
                  <Input placeholder="x m" value={p.world[0]} onChange={(e) => setPoints(points.map((q, j) => (j === i ? { ...q, world: [e.target.value, q.world[1]] } : q)))} />
                  <Input placeholder="y m" value={p.world[1]} onChange={(e) => setPoints(points.map((q, j) => (j === i ? { ...q, world: [q.world[0], e.target.value] } : q)))} />
                  <span className={s.mono}>{result?.residuals_m?.[i] != null ? `${result.residuals_m[i].toFixed(3)} m` : ''}</span>
                  <Button size="sm" variant="plain" icon={Trash2} onClick={() => setPoints(points.filter((_, j) => j !== i))} />
                </div>
              ))}
            </>
          )}
          <div className={s.row} style={{ marginTop: 6 }}>
            <Button size="sm" icon={Ruler} onClick={() => void solve()}>计算标定</Button>
            {result && <span className={s.hint}>{result.model === 'known_distance' ? '已知距离' : result.model === 'affine' ? '仿射' : '相似变换'} · {(result.scale_m_per_px * 100).toFixed(2)} cm/像素 · 旋转 {result.rotation_deg}°{result.rmse_m != null ? ` · RMSE ${result.rmse_m} m` : ''}</span>}
            <span className={s.grow} />
            {result && <Button size="sm" variant="primary" icon={CheckCircle2} onClick={() => void save({ calibration: result, confirmed: { calibration: true } }, '标定已保存')}>保存标定</Button>}
          </div>
          {result?.warnings?.map((wn) => <p key={wn} className={s.hint}>{wn}</p>)}
        </div>
      )}>
      {() => (
        <>
          <image href={assetUrl(asset.id, ver.v, meta.image ?? meta.primary) ?? ''} width={w} height={h} transform={svgMatrix(shown)} preserveAspectRatio="none" />
          {(mode === 'points' ? points.map((p) => p.px) : [dist.p1, dist.p2].filter(Boolean) as XY[]).map((px, i) => {
            const [x, y] = toWorldPx(px);
            return <g key={i}><circle cx={x} cy={y} r={4} vectorEffect="non-scaling-stroke" fill="#ff453a" stroke="#fff" strokeWidth={1.5} transform={`translate(${x} ${y}) scale(${result ? 0.25 : 1}) translate(${-x} ${-y})`} /></g>;
          })}
          {dist.p1 && dist.p2 && mode === 'distance' && (() => { const a = toWorldPx(dist.p1), b = toWorldPx(dist.p2); return <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke="#ff453a" strokeWidth={2} vectorEffect="non-scaling-stroke" />; })()}
        </>
      )}
    </MapView2D>
  );
}

/* ------------------------------------------------------------- models -- */
function ModelPreview({ asset, ver }: { asset: Asset; ver: AssetVersion }) {
  const disp = ver.meta.display ?? {};
  const save = useApplyMeta(asset);
  const [layers, setLayers] = useState<ModelLayers>({ appearance: true, footprint: true, collision: false, axes: true });
  const [forward, setForward] = useState(disp.forward ?? '+z');
  const [up, setUp] = useState(disp.up ?? '+y');
  const [scale, setScale] = useState(String(disp.scale ?? 1));
  const [measured, setMeasured] = useState<Measured | null>(null);
  const source: ModelSource | null = useMemo(() => {
    const base = `/lab/api/assets/${asset.id}/v/${ver.v}/file/`;
    if (disp.builtin === 'turtlebot4') return { type: 'urdf', url: '/lab/api/ros/robots/turtlebot4.urdf', resolve: (pkg: string) => `/lab/api/ros/package/${pkg}` };
    if (disp.builtin) return { type: 'builtin', builtin: disp.builtin };
    if (disp.urdf) {
      // same rule as the backend check: package://pkg/… inside the bundle first, else the installed ROS share
      const inBundle = (pkg: string) => ver.files.some((f) => f.path.startsWith(`files/${pkg}/`));
      return { type: 'urdf', url: base + disp.urdf, resolve: (pkg: string) => (inBundle(pkg) ? `${base}files/${pkg}` : `/lab/api/assets/local/file/ros/${pkg}`) };
    }
    // an SDF model is previewed through its first visual mesh inside the bundle (poses of further links are not composed)
    const sdfMesh = disp.sdf ? (ver.meta.inspection?.meshes as { use: string; status: string; path: string | null }[] | undefined)
      ?.find((m) => m.use === 'visual' && m.status === 'bundle' && m.path) : undefined;
    const file = disp.model ?? (sdfMesh ? `files/${sdfMesh.path}` : null);
    if (!file) return null;
    const ext = file.split('.').pop()!.toLowerCase();
    return { type: ext === 'glb' || ext === 'gltf' ? 'gltf' : 'mesh', url: base + file.split('/').map(encodeURIComponent).join('/'), ext };
  }, [asset.id, ver.v, ver.files, ver.meta.inspection, disp.builtin, disp.urdf, disp.model, disp.sdf]);
  const orientable = source?.type === 'gltf' || source?.type === 'mesh';
  const axes = ['+x', '-x', '+y', '-y', '+z', '-z'];
  const confirm = () => void save({
    display: { forward, up, scale: Number(scale) || 1, size_m: measured, confirmed: true },
    ...(asset.kind === 'vehicle' && measured && !ver.meta.planning?.footprint ? { planning: { footprint: { type: 'rect', length_m: measured.length_m, width_m: measured.width_m }, footprint_source: '模型尺寸（已确认）' } } : {}),
  }, '模型朝向与尺寸已确认');
  return (
    <div style={{ position: 'relative', height: '100%' }}>
      <ModelViewer source={source} forward={forward} up={up} scale={Number(scale) || 1} planning={ver.meta.planning ?? null} layers={layers} onMeasured={setMeasured} />
      <div className={s.overlay}>
        <div className={s.glass}>
          <div className={s.row}>
            {(['appearance', 'footprint', 'collision', 'axes'] as const).map((k) => (
              <button key={k} type="button" className={s.chip} data-tone={layers[k] ? 'blue' : undefined} onClick={() => setLayers({ ...layers, [k]: !layers[k] })}>
                {layers[k] ? <Eye size={11} /> : <EyeOff size={11} />}{{ appearance: '外观模型', footprint: '规划足迹', collision: '碰撞几何', axes: '坐标轴' }[k]}
              </button>
            ))}
          </div>
          {orientable && (
            <div className={s.row} style={{ marginTop: 6 }}>
              <label className={s.hint}>模型前方</label>
              <Select value={forward} onChange={(e) => setForward(e.target.value)}>{axes.map((a) => <option key={a}>{a}</option>)}</Select>
              <label className={s.hint}>向上</label>
              <Select value={up} onChange={(e) => setUp(e.target.value)}>{axes.map((a) => <option key={a}>{a}</option>)}</Select>
              <label className={s.hint}>缩放</label>
              <Select value={scale} onChange={(e) => setScale(e.target.value)}>{['1', '0.01', '0.001', '0.1', '10', '2', '0.5'].map((a) => <option key={a} value={a}>{a === '0.001' ? '0.001（毫米→米）' : a === '0.01' ? '0.01（厘米→米）' : a}</option>)}</Select>
            </div>
          )}
          <div className={s.row} style={{ marginTop: 6 }}>
            <span className={s.hint}>{disp.confirmed ? `已确认：前方 ${disp.forward}，向上 ${disp.up}，缩放 ${disp.scale}` : '红轴是车辆前进方向（ROS x），绿轴向左（y），蓝轴向上（z）。核对后确认。'}</span>
            <span className={s.grow} />
            {!disp.builtin && <Button size="sm" variant="primary" icon={Crosshair} disabled={!measured} onClick={confirm}>确认朝向与尺寸</Button>}
          </div>
        </div>
      </div>
    </div>
  );
}

function WorldFacts({ ver }: { ver: AssetVersion }) {
  const w = (ver.meta.world ?? ver.meta.inspection) as Record<string, any> | undefined; // eslint-disable-line @typescript-eslint/no-explicit-any
  return (
    <div style={{ padding: 16 }}>
      <Notice tone="info">Gazebo 世界作为仿真参考导入：其中的模型和网格不会自动变成规划几何。规划请在任务地图里画边界与障碍，或导入 ROS 栅格 / GeoJSON。</Notice>
      <div className={s.kv} style={{ marginTop: 10 }}>
        <span>世界</span><span>{w?.world}</span>
        <span>SDF 版本</span><span>{w?.sdf_version}</span>
        <span>直接模型</span><span>{(w?.models ?? []).join(', ') || '—'}</span>
        <span>引用模型</span><span>{(w?.includes ?? []).map((i: { uri: string }) => i.uri).join(', ') || '—'}</span>
        <span>系统插件</span><span className={s.mono}>{(w?.plugins ?? []).join(', ') || '—'}</span>
      </div>
    </div>
  );
}

function ScenarioFacts({ ver }: { ver: AssetVersion }) {
  const sc = ver.meta.scenario;
  return (
    <div style={{ padding: 16 }}>
      <div className={s.kv}>
        <span>场景</span><span>{sc?.title}</span>
        <span>类型</span><span>{sc?.problem_class}</span>
        <span>来源</span><span>{String(ver.meta.from_scenario ?? '')}</span>
        <span>绑定资产</span><span>{(ver.meta.asset_refs ?? []).map((r) => `${r.role}:${r.id}@v${r.version}`).join('，') || '无'}</span>
      </div>
    </div>
  );
}
