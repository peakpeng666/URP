/** Asset inspector: naming, versions, the three capability layers, planning / simulation parameters, provenance, references. */
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Archive, ArchiveRestore, CheckCircle2, CircleAlert, FileUp, GitBranch, Lock, MapPinned, PackageOpen, Play, Plus, Tractor, Trash2,
} from 'lucide-react';
import { fmt } from '../../lab/api';
import { Button, EmptyState, Input, Select } from '../../lab/ui';
import { OBSTACLE_STYLE } from '../editor/geometry';
import { isFleet, useStudio } from '../store';
import {
  assetsApi, KIND_LABEL, LEVEL_LABEL, SPDX, SUBTYPE_LABEL, type Asset, type AssetVersion, type CheckItem, type PlanningProfile,
} from './api';
import { backgroundOf, bindVehicle, footprintRadius, openTaskMap, placeFacility, setBackground } from './planBridge';
import { useAssets } from './store';
import s from './assets.module.css';

const KINEMATICS: Record<string, string> = {
  differential: '差速（原地转向）', skid_steer: '滑移转向', tracked: '履带', omni: '全向', ackermann: '阿克曼转向（有最小转弯半径）', articulated: '铰接转向（有最小转弯半径）',
};
const TURN_LIMITED = new Set(['ackermann', 'articulated']);

const say = (tone: 'ok' | 'error' | 'info', text: string) => useStudio.getState().notify(tone, text);

export function AssetInspector() {
  const st = useAssets();
  const a = st.asset;
  if (!a) return <EmptyState icon={PackageOpen} title="未选择资产" detail="在左侧资产库里选一个地图、车辆、设施或场景模板。" />;
  const ver = a.versions.find((v) => v.v === (st.version ?? a.current)) ?? a.versions[a.versions.length - 1];
  return (
    <div className={s.panel}>
      <div className={s.scroll}>
        <Header a={a} ver={ver} />
        <Actions a={a} ver={ver} />
        {ver.validation.errors.length + ver.validation.warnings.length > 0 && <Validation ver={ver} />}
        {a.kind === 'vehicle' && <VehicleLayers key={`${a.id}@${ver.v}`} a={a} ver={ver} />}
        {a.kind === 'facility' && <FacilityLayers key={`${a.id}@${ver.v}`} a={a} ver={ver} />}
        {a.kind === 'map' && <MapFacts a={a} ver={ver} />}
        <Versions a={a} />
        <Provenance key={`src-${a.id}@${ver.v}`} a={a} ver={ver} />
        <Refs />
        <Files a={a} ver={ver} />
      </div>
    </div>
  );
}

/* --------------------------------------------------------------- header -- */
function Header({ a, ver }: { a: Asset; ver: AssetVersion }) {
  const apply = useAssets((x) => x.apply);
  const [name, setName] = useState(a.name);
  const [category, setCategory] = useState(a.category);
  const [tags, setTags] = useState(a.tags.join('，'));
  const [notes, setNotes] = useState(a.notes ?? '');
  useEffect(() => { setName(a.name); setCategory(a.category); setTags(a.tags.join('，')); setNotes(a.notes ?? ''); }, [a.id, a.name, a.category, a.tags, a.notes]);
  const level = ver.capabilities.level ? LEVEL_LABEL[ver.capabilities.level] : null;
  const commit = async (patch: Parameters<typeof assetsApi.patch>[1]) => {
    try {
      apply(await assetsApi.patch(a.id, patch));
    } catch (e) {
      say('error', (e as Error).message);
    }
  };
  return (
    <div className={s.section}>
      <div className={s.row}>
        <span className={s.chip} data-tone="blue">{KIND_LABEL[a.kind]}</span>
        <span className={s.chip}>{SUBTYPE_LABEL[a.subtype] ?? a.subtype}</span>
        {level && <span className={s.chip} data-tone={level.tone}>{level.text}</span>}
        {a.builtin && <span className={s.chip}>内置</span>}
        {a.archived && <span className={s.chip} data-tone="orange">已归档</span>}
        <span className={s.grow} />
        <span className={s.hint}>{a.id}</span>
      </div>
      <div className={s.form} style={{ marginTop: 4 }}>
        <label htmlFor="asset-name">名称</label>
        <Input id="asset-name" value={name} disabled={a.builtin} onChange={(e) => setName(e.target.value)}
          onBlur={() => name.trim() && name !== a.name && void commit({ name: name.trim() })} onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()} />
        <label htmlFor="asset-cat">分类</label>
        <Input id="asset-cat" value={category} disabled={a.builtin} placeholder="如：果园、仓储、移动平台" onChange={(e) => setCategory(e.target.value)}
          onBlur={() => category !== a.category && void commit({ category: category.trim() })} />
        <label htmlFor="asset-tags">标签</label>
        <Input id="asset-tags" value={tags} disabled={a.builtin} placeholder="逗号分隔" onChange={(e) => setTags(e.target.value)}
          onBlur={() => { const next = tags.split(/[,，]/).map((x) => x.trim()).filter(Boolean); if (next.join() !== a.tags.join()) void commit({ tags: next }); }} />
        <label htmlFor="asset-notes">备注</label>
        <Input id="asset-notes" value={notes} disabled={a.builtin} placeholder="用途、注意事项" onChange={(e) => setNotes(e.target.value)}
          onBlur={() => notes !== (a.notes ?? '') && void commit({ notes })} />
      </div>
    </div>
  );
}

/* -------------------------------------------------------------- actions -- */
function Actions({ a, ver }: { a: Asset; ver: AssetVersion }) {
  const st = useAssets();
  const scenario = useStudio((x) => x.scenario);
  const fleetOpen = !!scenario && isFleet(scenario);
  const replaceInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const run = async (label: string, fn: () => Promise<void>) => {
    setBusy(label);
    try {
      await fn();
    } catch (e) {
      say('error', (e as Error).message);
    } finally {
      setBusy(null);
    }
  };
  const background = a.kind === 'map' ? backgroundOf(a, ver) : null;
  const lockable = !ver.locked && !a.builtin;
  return (
    <div className={s.section}>
      <h4>使用</h4>
      <div className={s.row}>
        {a.kind === 'map' && a.subtype !== 'gazebo_world' && (
          <Button size="sm" variant="primary" icon={MapPinned} disabled={typeof background === 'string'} title={typeof background === 'string' ? background : '用此地图的边界、障碍和语义创建多车任务地图'}
            onClick={() => st.setTaskMapFrom({ id: a.id, v: ver.v })}>用此地图新建任务地图</Button>
        )}
        {a.kind === 'map' && a.subtype === 'image' && fleetOpen && typeof background !== 'string' && (
          <Button size="sm" disabled={!!busy} title="按标定坐标叠加到当前任务地图（只作背景，不可通行）"
            onClick={() => void run('bg', async () => { const err = await setBackground(background!); say(err ? 'error' : 'ok', err ?? '已设为当前任务地图的底图'); })}>设为当前任务地图底图</Button>
        )}
        {a.kind === 'vehicle' && (
          <Button size="sm" variant="primary" icon={Tractor} disabled={!fleetOpen} title={fleetOpen ? `把 ${scenario!.title} 的车队设为这种车` : '先在「任务规划」里打开一个多车任务地图'}
            onClick={() => { const err = bindVehicle(a, ver); say(err ? 'error' : 'ok', err ?? `已把「${scenario!.title}」的车队设为 ${a.name}（车体半径、容量、车速已写入任务地图）`); }}>用于当前任务地图车队</Button>
        )}
        {a.kind === 'facility' && (
          <Button size="sm" variant="primary" icon={Plus} disabled={!fleetOpen} title={fleetOpen ? '放到场地中心，之后可在地图上拖动' : '先在「任务规划」里打开一个多车任务地图'}
            onClick={() => { const err = placeFacility(a, ver); say(err ? 'error' : 'ok', err ?? `已把 ${a.name} 作为障碍放进任务地图（场地中心，可拖动）`); }}>放进当前任务地图</Button>
        )}
        {a.kind === 'scenario' && (
          <Button size="sm" variant="primary" icon={Play} disabled={!!busy}
            onClick={() => void run('inst', async () => { const sc = await assetsApi.instantiate(a.id); say('ok', `已由模板生成「${sc.title}」`); openTaskMap(sc.id); })}>实例化为新任务地图</Button>
        )}
        {lockable && (
          <Button size="sm" icon={Lock} disabled={!!busy} title="锁定后文件与参数不可再改；之后的修改会生成新版本，实验记录引用的版本保持不变"
            onClick={() => void run('lock', async () => { st.apply(await assetsApi.lock(a.id, ver.v)); say('ok', `v${ver.v} 已锁定`); })}>锁定 v{ver.v}</Button>
        )}
      </div>
      <div className={s.row}>
        {!a.builtin && (
          <>
            <Button size="sm" variant="plain" icon={FileUp} disabled={!!busy} title="上传同类文件作为新版本（保留规划 / 仿真参数，旧版本与其引用不变）"
              onClick={() => replaceInput.current?.click()}>替换文件（新版本）</Button>
            <input ref={replaceInput} type="file" multiple hidden onChange={(e) => {
              const files = Array.from(e.target.files ?? []);
              e.target.value = '';
              if (files.length) void run('replace', async () => { const next = await assetsApi.replace(a.id, files.map((f) => ({ file: f, path: f.webkitRelativePath || f.name }))); st.apply(next); say('ok', `已生成 v${next.current}`); });
            }} />
            <Button size="sm" variant="plain" icon={a.archived ? ArchiveRestore : Archive} disabled={!!busy}
              onClick={() => void run('archive', async () => { st.apply(await assetsApi.patch(a.id, { archived: !a.archived })); await st.refresh(); })}>{a.archived ? '取消归档' : '归档'}</Button>
            <Button size="sm" variant="plain" icon={Trash2} disabled={!!busy || (st.refs?.total ?? 0) > 0}
              title={(st.refs?.total ?? 0) > 0 ? `被 ${st.refs!.total} 个场景 / 运行记录引用，不能删除（可以归档）` : '永久删除这个资产的所有版本'}
              onClick={() => {
                if (!window.confirm(`永久删除「${a.name}」的全部 ${a.versions.length} 个版本？此操作不能撤销。`)) return;
                void run('delete', async () => { await assetsApi.remove(a.id); await st.select(null); await st.refresh(); say('ok', '已删除'); });
              }}>删除</Button>
          </>
        )}
      </div>
      {a.kind === 'map' && typeof background === 'string' && a.subtype !== 'gazebo_world' && <p className={s.hint}>{background}</p>}
    </div>
  );
}

function Validation({ ver }: { ver: AssetVersion }) {
  return (
    <div className={s.section}>
      <h4><CircleAlert size={13} /> 导入检查</h4>
      <ul className={s.issues}>
        {ver.validation.errors.map((e) => <li key={e} data-tone="error">{e}</li>)}
        {ver.validation.warnings.map((w) => <li key={w} data-tone="warn">{w}</li>)}
      </ul>
    </div>
  );
}

/* ------------------------------------------------------- capability lists -- */
function Checklist({ items }: { items: CheckItem[] }) {
  return (
    <div className={s.checks}>
      {items.map((i) => (
        <div key={i.key} className={s.check} data-ok={i.ok}>
          {i.ok ? <CheckCircle2 size={14} /> : <CircleAlert size={14} />}
          <span>
            {i.label}{i.value != null && i.value !== '' ? `：${i.value}` : ''}
            {i.detail && <small>{i.detail}</small>}
          </span>
        </div>
      ))}
    </div>
  );
}

function Layer({ title, ok, children, note }: { title: string; ok?: boolean; children: React.ReactNode; note?: string }) {
  return (
    <div className={s.section}>
      <div className={s.layerTitle}>
        <h4>{title}</h4>
        <span className={s.chip} data-tone={ok ? 'green' : 'orange'}>{ok ? '满足' : '不满足'}</span>
      </div>
      {note && <p className={s.hint}>{note}</p>}
      {children}
    </div>
  );
}

const numOrNull = (v: string): number | null => (v.trim() === '' ? null : Number(v));

function VehicleLayers({ a, ver }: { a: Asset; ver: AssetVersion }) {
  const caps = ver.capabilities;
  const st = useAssets();
  const p = ver.meta.planning ?? {};
  const [fp, setFp] = useState({ type: p.footprint?.type ?? 'rect', length: String(p.footprint?.length_m ?? ''), width: String(p.footprint?.width_m ?? ''), radius: String(p.footprint?.radius_m ?? '') });
  const [form, setForm] = useState({
    capacity: String(p.capacity ?? ''), speed: String(p.speed_mps ?? ''), kinematics: p.kinematics ?? '', turn: String(p.min_turn_radius_m ?? ''), work: String(p.work_width_m ?? ''),
    noLoad: p.payload === 'none',
  });
  const readOnly = a.builtin;
  const footprint = (): PlanningProfile['footprint'] => (fp.type === 'circle'
    ? (numOrNull(fp.radius) ? { type: 'circle', radius_m: numOrNull(fp.radius) } : null)
    : (numOrNull(fp.length) && numOrNull(fp.width) ? { type: 'rect', length_m: numOrNull(fp.length), width_m: numOrNull(fp.width) } : null));
  const draftRadius = footprintRadius(footprint());
  const save = async () => {
    const old = p.footprint;
    const sameFp = !!old && fp.type === old.type && (fp.type === 'circle'
      ? numOrNull(fp.radius) === (old.radius_m ?? null)
      : numOrNull(fp.length) === (old.length_m ?? null) && numOrNull(fp.width) === (old.width_m ?? null));
    const planning: PlanningProfile = {
      footprint: footprint(), capacity: form.noLoad ? null : numOrNull(form.capacity), payload: form.noLoad ? 'none' : 'load', speed_mps: numOrNull(form.speed),
      kinematics: (form.kinematics || null) as PlanningProfile['kinematics'], min_turn_radius_m: TURN_LIMITED.has(form.kinematics) ? numOrNull(form.turn) : 0,
      work_width_m: numOrNull(form.work),
      // saving an unchanged bounding-box footprint is the user confirming it
      footprint_source: sameFp ? (p.footprint_source ?? '').replace('待确认', '已确认') || null : '用户填写',
    };
    try {
      const next = await assetsApi.meta(a.id, ver.v, { planning });
      st.apply(next);
      say('ok', next.current !== ver.v ? `已保存（v${ver.v} 已锁定，生成 v${next.current}）` : '规划参数已保存');
    } catch (e) {
      say('error', (e as Error).message);
    }
  };
  const solver = caps.planning?.solver?.fleet_routing as { robot_radius?: number | null; capacity?: number | null; speed_mps?: number | null; ignored: string[] } | undefined;
  const adapters = caps.simulation?.adapters ?? [];
  const adapter = (ver.meta.simulation?.adapter as string | null | undefined) ?? null;
  return (
    <>
      <Layer title="① 外观显示" ok={caps.display?.ok}>
        <Checklist items={caps.display?.items ?? []} />
      </Layer>
      <Layer title="② 规划参数" ok={caps.planning?.ok}
        note="足迹决定障碍膨胀半径（外接圆），容量决定每趟载量，车速换算作业时间；运动学区分能否原地转向。">
        <Checklist items={caps.planning?.items ?? []} />
        {!readOnly && (
          <div className={s.form} style={{ marginTop: 6 }}>
            <label>足迹</label>
            <div className={s.row}>
              <Select value={fp.type} onChange={(e) => setFp({ ...fp, type: e.target.value as 'rect' | 'circle' })}><option value="rect">矩形 长×宽</option><option value="circle">圆形 半径</option></Select>
              {fp.type === 'rect' ? (
                <><Input style={{ width: 64 }} placeholder="长 m" value={fp.length} onChange={(e) => setFp({ ...fp, length: e.target.value })} />×
                  <Input style={{ width: 64 }} placeholder="宽 m" value={fp.width} onChange={(e) => setFp({ ...fp, width: e.target.value })} /></>
              ) : <Input style={{ width: 70 }} placeholder="半径 m" value={fp.radius} onChange={(e) => setFp({ ...fp, radius: e.target.value })} />}
            </div>
            <label>容量</label>
            <div className={s.row}>
              <Input style={{ width: 90 }} value={form.noLoad ? '' : form.capacity} disabled={form.noLoad} placeholder="每趟载量" onChange={(e) => setForm({ ...form, capacity: e.target.value })} />
              <label className={s.hint}><input type="checkbox" checked={form.noLoad} onChange={(e) => setForm({ ...form, noLoad: e.target.checked })} /> 不载货（巡检 / 采样）</label>
            </div>
            <label>车速 m/s</label>
            <Input value={form.speed} placeholder="作业时的平均行驶速度" onChange={(e) => setForm({ ...form, speed: e.target.value })} />
            <label>运动学</label>
            <Select value={form.kinematics} onChange={(e) => setForm({ ...form, kinematics: e.target.value })}>
              <option value="">未指定</option>
              {Object.entries(KINEMATICS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </Select>
            {TURN_LIMITED.has(form.kinematics) && (
              <><label>最小转弯半径 m</label><Input value={form.turn} onChange={(e) => setForm({ ...form, turn: e.target.value })} /></>
            )}
            <label>作业幅宽 m</label>
            <Input value={form.work} placeholder="覆盖作业用；运输可留空" onChange={(e) => setForm({ ...form, work: e.target.value })} />
          </div>
        )}
        {!readOnly && (
          <div className={s.row}>
            <span className={s.hint}>{draftRadius ? `规划半径（外接圆）${draftRadius.toFixed(3)} m` : '填足迹后显示规划半径'}{p.footprint_source ? ` · 足迹来源：${p.footprint_source}` : ''}</span>
            <span className={s.grow} />
            <Button size="sm" variant="primary" onClick={() => void save()}>保存规划参数</Button>
          </div>
        )}
        {solver && (
          <div className={s.kv} style={{ marginTop: 6 }}>
            <span>多车求解读取</span><span>车体半径 {solver.robot_radius ?? '—'} m · 容量 {solver.capacity ?? '—'} · 车速 {solver.speed_mps ?? '—'} m/s</span>
            <span>未参与</span><span>{solver.ignored.length ? solver.ignored.join('；') : '无'}</span>
          </div>
        )}
      </Layer>
      <Layer title="③ Gazebo / ROS 2 仿真" ok={caps.simulation?.ok}
        note="仿真需有对应车型适配，碰撞检测使用单独的碰撞几何。">
        <Checklist items={caps.simulation?.items ?? []} />
        {adapters.length > 0 && (
          <div className={s.row} style={{ marginTop: 6 }}>
            <label className={s.hint}>仿真适配</label>
            <Select value={adapter ?? ''} disabled={readOnly} onChange={async (e) => {
              try {
                st.apply(await assetsApi.meta(a.id, ver.v, { simulation: { adapter: e.target.value || null } }));
              } catch (err) {
                say('error', (err as Error).message);
              }
            }}>
              <option value="">无（不能在工作台里执行）</option>
              {adapters.map((o) => <option key={o.id} value={o.id} disabled={!o.ok} title={o.reason}>{o.label}{o.ok ? '' : '（不兼容）'}</option>)}
            </Select>
          </div>
        )}
        {adapters.some((o) => !o.ok) && !caps.simulation?.ok && (
          <p className={s.hint}>{adapters.filter((o) => !o.ok).map((o) => o.reason).filter((x, i, arr) => arr.indexOf(x) === i).join('；')}</p>
        )}
      </Layer>
    </>
  );
}

function FacilityLayers({ a, ver }: { a: Asset; ver: AssetVersion }) {
  const st = useAssets();
  const caps = ver.capabilities;
  const p = ver.meta.planning ?? {};
  const size = ver.meta.display?.size_m;
  const [kind, setKind] = useState(p.obstacle_kind ?? 'building');
  const [len, setLen] = useState(String(p.footprint?.length_m ?? size?.length_m?.toFixed(2) ?? ''));
  const [wid, setWid] = useState(String(p.footprint?.width_m ?? size?.width_m?.toFixed(2) ?? ''));
  const save = async () => {
    const l = numOrNull(len), w = numOrNull(wid);
    try {
      const next = await assetsApi.meta(a.id, ver.v, { planning: { footprint: l && w ? { type: 'rect', length_m: l, width_m: w } : null, obstacle_kind: kind, height_m: size?.height_m ?? null, footprint_source: '用户填写' } });
      st.apply(next);
      say('ok', '规划占地已保存');
    } catch (e) {
      say('error', (e as Error).message);
    }
  };
  return (
    <>
      <Layer title="① 显示" ok={caps.display?.ok}><Checklist items={caps.display?.items ?? []} /></Layer>
      <Layer title="② 规划占地" ok={caps.planning?.ok} note="放入任务地图后，按此占地生成规划障碍多边形。">
        <div className={s.form}>
          <label>障碍类型</label>
          <Select value={kind} disabled={a.builtin} onChange={(e) => setKind(e.target.value)}>
            {Object.entries(OBSTACLE_STYLE).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </Select>
          <label>占地 长×宽</label>
          <div className={s.row}>
            <Input style={{ width: 70 }} value={len} disabled={a.builtin} onChange={(e) => setLen(e.target.value)} />×
            <Input style={{ width: 70 }} value={wid} disabled={a.builtin} onChange={(e) => setWid(e.target.value)} /> m
          </div>
        </div>
        {size && <p className={s.hint}>模型尺寸 {size.length_m?.toFixed(2)} × {size.width_m?.toFixed(2)} × {size.height_m?.toFixed(2)} m（{ver.meta.display?.confirmed ? '朝向已确认' : '朝向未确认'}）</p>}
        {!a.builtin && <div className={s.row}><span className={s.grow} /><Button size="sm" variant="primary" onClick={() => void save()}>保存占地</Button></div>}
      </Layer>
    </>
  );
}

/* --------------------------------------------------------------- maps -- */
function MapFacts({ a, ver }: { a: Asset; ver: AssetVersion }) {
  const m = ver.meta;
  const ins = (m.inspection ?? {}) as Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any
  if (a.subtype === 'ros_grid' && m.frame) {
    const stt = m.stats ?? {};
    const pct = (x?: number) => (stt.cells ? `${((100 * (x ?? 0)) / stt.cells).toFixed(1)}%` : '—');
    const meta = ins.meta ?? {};
    return (
      <div className={s.section}>
        <h4>栅格与坐标</h4>
        <div className={s.kv}>
          <span>坐标</span><span>{m.confirmed?.frame ? '已确认' : '待确认（在预览里核对后确认）'}</span>
          <span>分辨率</span><span>{m.frame.resolution} m/像素</span>
          <span>原点</span><span className={s.mono}>({m.frame.origin.map((v) => fmt.num(v, 3)).join(', ')})</span>
          <span>尺寸</span><span>{m.frame.width_px}×{m.frame.height_px} 像素 = {fmt.num(m.frame.width_m, 2)}×{fmt.num(m.frame.height_m, 2)} m</span>
          <span>范围</span><span className={s.mono}>x {fmt.num(m.frame.bounds[0], 2)}…{fmt.num(m.frame.bounds[2], 2)}，y {fmt.num(m.frame.bounds[1], 2)}…{fmt.num(m.frame.bounds[3], 2)}</span>
          <span>判读</span><span>{meta.mode ?? 'trinary'} · negate {String(meta.negate ?? 0)} · 占据阈值 {meta.occupied_thresh} · 空闲阈值 {meta.free_thresh}</span>
          <span>占比</span><span>空闲 {pct(stt.free)} · 占据 {pct(stt.occupied)} · 未知 {pct(stt.unknown)}{stt.intermediate ? ` · 中间值 ${pct(stt.intermediate)}` : ''}</span>
          <span>可通行面积</span><span>{fmt.num(stt.free_area_m2, 1)} m²</span>
        </div>
      </div>
    );
  }
  if (a.subtype === 'vector') {
    const tf = m.transform ?? {}, sum = m.summary ?? {};
    return (
      <div className={s.section}>
        <h4>坐标换算与语义</h4>
        <div className={s.kv}>
          <span>坐标</span><span>{m.confirmed?.frame ? '已确认' : '待确认'}</span>
          <span>源坐标系</span><span>{tf.source_crs} <small className={s.hint}>（{m.crs?.source}）</small></span>
          <span>投影</span><span>{tf.method === 'utm' ? `UTM ${tf.projected_crs}（按质心选带）` : tf.projected_crs}{tf.assumed ? ' · 用户确认已是米' : ''}</span>
          <span>局部原点</span><span className={s.mono}>{(tf.origin_projected ?? []).map((v: number) => v.toFixed(2)).join(', ')}</span>
          <span>范围</span><span>{sum.size_m?.join(' × ')} m</span>
          <span>要素</span><span>{Object.entries(sum.roles ?? {}).map(([r, n]) => `${r} ${n}`).join(' · ')}</span>
          <span>孔洞</span><span>{sum.holes ?? 0}（转成边界内障碍）</span>
        </div>
      </div>
    );
  }
  if (a.subtype === 'image') {
    const c = m.calibration;
    return (
      <div className={s.section}>
        <h4>图片底图</h4>
        <div className={s.kv}>
          <span>尺寸</span><span>{m.size_px?.join('×')} 像素</span>
          <span>标定</span><span>{c ? `${c.model === 'known_distance' ? '已知距离' : c.model === 'affine' ? '仿射' : '相似变换'} · ${(c.scale_m_per_px * 100).toFixed(2)} cm/像素 · 旋转 ${c.rotation_deg}°${c.rmse_m != null ? ` · RMSE ${c.rmse_m} m` : ''}` : '未标定'}</span>
          <span>通行</span><span>图片仅作底图；请在任务地图中描出边界和障碍。</span>
        </div>
      </div>
    );
  }
  return null;
}

/* ------------------------------------------------------------ versions -- */
function Versions({ a }: { a: Asset }) {
  const st = useAssets();
  const shown = st.version ?? a.current;
  const byVersion = st.refs?.by_version ?? {};
  return (
    <div className={s.section}>
      <h4><GitBranch size={13} /> 版本</h4>
      <div className={s.versions}>
        {[...a.versions].reverse().map((v) => (
          <button key={v.v} type="button" className={s.ver} aria-current={v.v === shown} onClick={() => st.setVersion(v.v)}>
            <b>v{v.v}</b>
            <span>
              {fmt.time(v.created_utc)}{v.based_on ? ` · 基于 v${v.based_on}` : ''}
              <div className={s.hint}><span className={s.mono}>{v.sha256.slice(0, 12)}</span>{byVersion[String(v.v)] ? ` · 被引用 ${byVersion[String(v.v)]} 次` : ''}</div>
            </span>
            <span className={s.row}>
              {v.locked ? <span className={s.chip}><Lock size={10} />锁定</span> : <span className={s.chip} data-tone="orange">草稿</span>}
              {v.v === a.current && <span className={s.chip} data-tone="blue">当前</span>}
            </span>
          </button>
        ))}
      </div>
      {shown !== a.current && !a.builtin && (
        <div className={s.row}>
          <span className={s.hint}>正在查看 v{shown}；新建任务地图默认用当前版本。</span>
          <Button size="sm" onClick={async () => { try { st.apply(await assetsApi.setCurrent(a.id, shown)); } catch (e) { say('error', (e as Error).message); } }}>设为当前版本</Button>
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------- provenance -- */
function Provenance({ a, ver }: { a: Asset; ver: AssetVersion }) {
  const st = useAssets();
  const src = ver.source;
  const [license, setLicense] = useState(src.license ?? '未声明');
  const [attribution, setAttribution] = useState(src.attribution ?? '');
  const [uri, setUri] = useState(src.uri ?? '');
  const dirty = license !== (src.license ?? '未声明') || attribution !== (src.attribution ?? '') || uri !== (src.uri ?? '');
  const licenses = useMemo(() => (SPDX.includes(license) ? SPDX : [license, ...SPDX]), [license]);
  return (
    <div className={s.section}>
      <h4>来源与许可</h4>
      <div className={s.form}>
        <label>来源类型</label><span>{{ upload: '上传', local: '本机资源', builtin: '内置', template: '场景模板' }[src.type] ?? src.type}{src.retrieved_utc ? ` · ${fmt.time(src.retrieved_utc)}` : ''}</span>
        <label>许可</label>
        <Select value={license} disabled={a.builtin} onChange={(e) => setLicense(e.target.value)}>{licenses.map((l) => <option key={l}>{l}</option>)}</Select>
        <label>署名</label><Input value={attribution} disabled={a.builtin} placeholder="作者 / 机构 / 年份" onChange={(e) => setAttribution(e.target.value)} />
        <label>原始地址</label><Input value={uri} disabled={a.builtin} placeholder="https://… 或 DOI" onChange={(e) => setUri(e.target.value)} />
        {src.original_files?.length ? <><label>原始文件</label><span className={s.mono}>{src.original_files.slice(0, 6).join(', ')}{src.original_files.length > 6 ? ' …' : ''}</span></> : null}
      </div>
      {(license === '未声明' || !license) && <p className={s.hint}>未声明许可的资产只能在本机研究中使用；发表或分享前请补全许可与署名。</p>}
      {dirty && !a.builtin && (
        <div className={s.row}>
          <span className={s.grow} />
          <Button size="sm" variant="primary" onClick={async () => {
            try {
              st.apply(await assetsApi.meta(a.id, ver.v, {}, { license, attribution, uri }));
              say('ok', ver.locked ? '来源信息已更新（生成了新版本）' : '来源信息已更新');
            } catch (e) {
              say('error', (e as Error).message);
            }
          }}>保存来源信息</Button>
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------- references -- */
function Refs() {
  const refs = useAssets((x) => x.refs);
  if (!refs) return null;
  return (
    <div className={s.section}>
      <h4>引用（{refs.total}）</h4>
      {refs.total === 0 && <p className={s.hint}>还没有场景或运行记录引用它。</p>}
      {refs.scenarios.map((r) => (
        <button key={`${r.id}-${r.version}`} type="button" className={s.ver} onClick={() => openTaskMap(r.id)} title="在任务规划里打开">
          <b>场景</b><span>{r.title}<div className={s.hint}>{r.role ?? ''} · 用 v{r.version ?? '?'}</div></span><span />
        </button>
      ))}
      {refs.runs.slice(0, 8).map((r) => (
        <div key={r.run_id} className={s.ver} style={{ cursor: 'default' }}>
          <b>运行</b><span>{r.algorithm ?? r.run_id}<div className={s.hint}>{r.scenario_id} · v{r.version} · {fmt.time(r.created_utc)}</div></span><span />
        </div>
      ))}
      {refs.runs.length > 8 && <p className={s.hint}>另有 {refs.runs.length - 8} 条运行记录。</p>}
    </div>
  );
}

function Files({ a, ver }: { a: Asset; ver: AssetVersion }) {
  const files = ver.files.filter((f) => f.path.startsWith('files/'));
  if (!files.length) return null;
  const total = files.reduce((x, f) => x + f.size, 0);
  return (
    <div className={s.section}>
      <h4>文件（{files.length} 个 · {(total / 1048576).toFixed(2)} MB）</h4>
      <div className={s.fileList}>
        {files.slice(0, 60).map((f) => (
          <div key={f.path}>
            <a href={`/lab/api/assets/${a.id}/v/${ver.v}/file/${f.path.split('/').map(encodeURIComponent).join('/')}`} target="_blank" rel="noreferrer" className={s.mono}>{f.path.slice(6)}</a>
            <span>{f.size < 1024 ? `${f.size} B` : f.size < 1048576 ? `${(f.size / 1024).toFixed(1)} KB` : `${(f.size / 1048576).toFixed(2)} MB`}</span>
            <span className={s.mono} title={f.sha256}>{f.sha256.slice(0, 8)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
