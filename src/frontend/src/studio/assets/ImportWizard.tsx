/** Import wizard: files → inspection report (server + Khronos glTF-Validator in the browser) → metadata → versioned asset. */
import { useEffect, useRef, useState, type DragEvent } from 'react';
import { AlertTriangle, CheckCircle2, FileUp, FolderOpen, X } from 'lucide-react';
import { Button, Input, Notice, Select, Spinner, Switch } from '../../lab/ui';
import { useStudio } from '../store';
import { assetsApi, KIND_LABEL, SPDX, stagingUrl, SUBTYPE_LABEL, type AssetKind, type ImportReport } from './api';
import { ModelViewer } from './ModelViewer';
import { useAssets } from './store';
import s from './assets.module.css';

type Picked = { file: File; path: string };
interface GltfReport { errors: number; warnings: number; messages: string[]; generator?: string }

async function validateGltf(main: Picked, all: Picked[]): Promise<GltfReport> {
  const validator = await import('gltf-validator');
  const bytes = new Uint8Array(await main.file.arrayBuffer());
  const base = main.path.includes('/') ? main.path.slice(0, main.path.lastIndexOf('/') + 1) : '';
  const report = await validator.validateBytes(bytes, {
    uri: main.file.name,
    maxIssues: 30,
    externalResourceFunction: async (uri: string) => {
      const want = base + decodeURIComponent(uri);
      const hit = all.find((p) => p.path === want || p.path.endsWith('/' + decodeURIComponent(uri)) || p.file.name === decodeURIComponent(uri));
      if (!hit) throw new Error(`缺少 ${uri}`);
      return new Uint8Array(await hit.file.arrayBuffer());
    },
  });
  const issues = report.issues ?? { numErrors: 0, numWarnings: 0, messages: [] };
  return {
    errors: issues.numErrors, warnings: issues.numWarnings, generator: report.info?.generator,
    messages: (issues.messages ?? []).filter((m: { severity: number }) => m.severity <= 1).slice(0, 8)
      .map((m: { code: string; message: string; pointer?: string }) => `${m.code}：${m.message}${m.pointer ? `（${m.pointer}）` : ''}`),
  };
}

export function ImportWizard() {
  const st = useAssets();
  const notify = useStudio((x) => x.notify);
  const [picked, setPicked] = useState<Picked[]>([]);
  const [hint, setHint] = useState<'' | AssetKind>('');
  const [report, setReport] = useState<ImportReport | null>(null);
  const [gltf, setGltf] = useState<GltfReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [assumeMetres, setAssumeMetres] = useState(false);
  const [form, setForm] = useState({ name: '', kind: '' as '' | AssetKind, category: '', tags: '', license: '未声明', attribution: '', source_uri: '' });
  const autoFilled = useRef({ name: '', attribution: '' });
  const [over, setOver] = useState(false);
  const files = useRef<HTMLInputElement>(null);
  const folder = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (st.importSeed?.length) void choose(st.importSeed);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const close = () => {
    if (report?.token) void assetsApi.dropStaging(report.token).catch(() => undefined);
    st.closeImport();
  };

  async function choose(list: File[]) {
    const items = list.map((f) => ({ file: f, path: (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name }));
    setPicked(items);
    setReport(null);
    setGltf(null);
    setError(null);
    setBusy(true);
    try {
      const main = items.find((p) => /\.(glb|gltf)$/i.test(p.path));
      if (main) setGltf(await validateGltf(main, items).catch((e) => ({ errors: 1, warnings: 0, messages: [String(e?.message ?? e)] })));
      const rep = await assetsApi.inspect(items, hint, assumeMetres);
      setReport(rep);
      const stem = (rep.primary ?? items[0]?.path ?? '').split('/').pop()?.replace(/\.[^.]+$/, '') ?? '';
      // auto-filled values follow the newly picked files; anything the user typed is kept
      const auto = autoFilled.current;
      const copyright = rep.inspection?.copyright ?? '';
      setForm((f) => ({ ...f, name: !f.name || f.name === auto.name ? stem : f.name, kind: rep.kind ?? '',
                        attribution: !f.attribution || f.attribution === auto.attribution ? copyright : f.attribution }));
      autoFilled.current = { name: stem, attribution: copyright };
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function reinspect(next: { kind?: string; assume_metres?: boolean }) {
    if (!report) return;
    setBusy(true);
    try {
      const rep = await assetsApi.reinspect(report.token, { kind: next.kind ?? hint, assume_metres: next.assume_metres ?? assumeMetres });
      setReport(rep);
      setForm((f) => ({ ...f, kind: rep.kind ?? f.kind }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!report) return;
    setBusy(true);
    try {
      const a = await assetsApi.commit({
        token: report.token, kind: (form.kind || report.kind || undefined) as AssetKind | undefined, name: form.name, category: form.category,
        tags: form.tags.split(/[,，\s]+/).filter(Boolean), license: form.license, attribution: form.attribution, source_uri: form.source_uri,
      });
      st.apply(a);
      await st.select(a.id);
      notify('ok', `已导入 ${a.name}（${KIND_LABEL[a.kind]} · v1，待确认）`);
      st.closeImport();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    if (e.dataTransfer.files.length) void choose([...e.dataTransfer.files]);
  };
  const ins = report?.inspection ?? {};
  const isModel = report && ['gltf', 'mesh', 'urdf', 'sdf_model'].includes(report.subtype ?? '');
  const blocking = (report?.errors.length ?? 0) > 0 || (gltf?.errors ?? 0) > 0;
  const step = !picked.length ? 1 : !report ? 2 : 3;
  return (
    <div className={s.backdrop} role="dialog" aria-modal="true" aria-label="导入资产" onKeyDown={(e) => e.key === 'Escape' && close()}>
      <div className={s.modal}>
        <div className={s.modalHead}>
          <FileUp size={16} />
          <h3>导入资产</h3>
          <div className={s.steps}>
            <span data-on={step === 1 || undefined}>① 选择文件</span>›<span data-on={step === 2 || undefined}>② 检查</span>›<span data-on={step === 3 || undefined}>③ 信息与许可</span>
          </div>
          <span className={s.grow} />
          <Button size="sm" variant="plain" icon={X} onClick={close} title="关闭" />
        </div>
        <div className={`${s.modalBody} ${!report ? s.single : ''}`}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
            <div className={s.dropzone} data-over={over || undefined}
              onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop}>
              <span>拖入文件、文件夹或 zip</span>
              <span className={s.hint}>ROS 地图（YAML + PGM/PNG）· GeoJSON · 图片底图 · GLB / glTF（含 .bin 与贴图）· URDF（含网格）· SDF 模型 / 世界 · STL / OBJ / DAE</span>
              <div className={s.row} style={{ justifyContent: 'center' }}>
                <Button size="sm" icon={FileUp} onClick={() => files.current?.click()}>选择文件</Button>
                <Button size="sm" icon={FolderOpen} onClick={() => folder.current?.click()}>选择文件夹</Button>
                <label className={s.hint}>按
                  <Select aria-label="导入为" value={hint} onChange={(e) => { setHint(e.target.value as '' | AssetKind); if (report) void reinspect({ kind: e.target.value }); }}>
                    <option value="">自动识别</option><option value="map">地图</option><option value="vehicle">车辆</option><option value="facility">障碍物 / 设施</option>
                  </Select>导入
                </label>
              </div>
              <input ref={files} type="file" multiple hidden data-testid="asset-files" onChange={(e) => e.target.files && void choose([...e.target.files])} />
              <input ref={folder} type="file" multiple hidden {...({ webkitdirectory: '' } as Record<string, string>)} onChange={(e) => e.target.files && void choose([...e.target.files])} />
            </div>
            {busy && <div className={s.row}><Spinner /> <span className={s.hint}>检查中…</span></div>}
            {error && <Notice tone="error">{error}</Notice>}
            {picked.length > 0 && (
              <div className={s.fileList}>
                {(report?.files ?? picked.map((p) => ({ path: p.path, size: p.file.size, kind: '' }))).map((f) => (
                  <div key={f.path}><span title={f.path} style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.path === report?.primary ? <b>{f.path}</b> : f.path}</span><span>{f.kind}</span><span>{(f.size / 1024).toFixed(1)} KB</span></div>
                ))}
              </div>
            )}
            {report && (
              <div>
                <div className={s.row} style={{ marginBottom: 6 }}>
                  {blocking ? <AlertTriangle size={14} color="#b1271d" /> : <CheckCircle2 size={14} color="#30b158" />}
                  <b style={{ fontSize: 13 }}>{report.subtype ? SUBTYPE_LABEL[report.subtype] ?? report.subtype : '未识别'}</b>
                  {report.kind && <span className={s.chip}>{KIND_LABEL[report.kind]}</span>}
                </div>
                <ul className={s.issues}>
                  {report.errors.map((e) => <li key={e} data-tone="error">{e}</li>)}
                  {gltf && gltf.errors > 0 && gltf.messages.map((m) => <li key={m} data-tone="error">glTF-Validator：{m}</li>)}
                  {report.warnings.map((w) => <li key={w} data-tone="warn">{w}</li>)}
                  {gltf && gltf.errors === 0 && <li>Khronos glTF-Validator：0 错误，{gltf.warnings} 警告{gltf.generator ? ` · 生成器 ${gltf.generator}` : ''}</li>}
                </ul>
                <InspectionFacts report={report} />
                {ins.crs?.kind === 'unknown' && (
                  <Switch checked={assumeMetres} onChange={(v) => { setAssumeMetres(v); void reinspect({ assume_metres: v }); }} label="我确认这些坐标已经是米（局部投影坐标）" />
                )}
              </div>
            )}
          </div>
          {report && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
              <div className={s.miniPreview}>
                {report.subtype === 'ros_grid' && report.preview && <img alt="地图预览" src={stagingUrl(report.token, report.preview) ?? ''} style={{ width: '100%', height: '100%', objectFit: 'contain', imageRendering: 'pixelated' }} />}
                {report.subtype === 'image' && report.preview && <img alt="图片" src={stagingUrl(report.token, report.preview) ?? ''} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />}
                {isModel && !blocking && report.primary && (
                  <ModelViewer height={260} layers={{ appearance: true, footprint: false, collision: false, axes: true }}
                    forward={report.subtype === 'gltf' ? '+z' : '+x'} up={report.subtype === 'gltf' ? '+y' : '+z'}
                    source={report.subtype === 'urdf'
                      ? { type: 'urdf', url: stagingUrl(report.token, `files/${report.primary}`) ?? '', resolve: (pkg) => `/lab/api/assets/staging/${report.token}/file/files/${pkg}` }
                      : { type: report.subtype === 'gltf' ? 'gltf' : 'mesh', url: stagingUrl(report.token, `files/${report.primary}`) ?? '', ext: report.primary.split('.').pop()!.toLowerCase() }} />
                )}
                {(report.subtype === 'vector' || report.subtype === 'gazebo_world' || blocking) && (
                  <div style={{ padding: 16 }} className={s.hint}>{blocking ? '修正错误后才能保存。' : '保存后在「预览」里确认坐标、原点与单位。'}</div>
                )}
              </div>
              <div className={s.form}>
                <label>名称</label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
                {isModel && (<><label>类别</label>
                  <Select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value as AssetKind })}>
                    <option value="vehicle">车辆</option><option value="facility">障碍物 / 设施</option>
                  </Select></>)}
                <label>分类</label><Input placeholder="如：果园运输车、仓储设施" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
                <label>标签</label><Input placeholder="逗号分隔" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} />
                <label>许可证</label>
                <Select value={form.license} onChange={(e) => setForm({ ...form, license: e.target.value })}>{SPDX.map((l) => <option key={l}>{l}</option>)}</Select>
                <label>署名 / 版权</label><Input value={form.attribution} onChange={(e) => setForm({ ...form, attribution: e.target.value })} />
                <label>来源地址</label><Input placeholder="下载页或数据集 DOI" value={form.source_uri} onChange={(e) => setForm({ ...form, source_uri: e.target.value })} />
              </div>
            </div>
          )}
        </div>
        <div className={s.modalFoot}>
          <span className={s.hint}>导入只读取和解压文件，不执行其中任何脚本；外部网址不会被访问。</span>
          <span className={s.grow} />
          <Button onClick={close}>取消</Button>
          <Button variant="primary" disabled={!report || blocking || busy || !form.name} onClick={() => void save()}>保存为资产</Button>
        </div>
      </div>
    </div>
  );
}

function InspectionFacts({ report }: { report: ImportReport }) {
  const ins = report.inspection ?? {};
  const rows: [string, string][] = [];
  if (report.subtype === 'ros_grid' && ins.frame) {
    const f = ins.frame;
    rows.push(['分辨率', `${f.resolution} m/像素`], ['图像', `${f.width_px} × ${f.height_px} 像素 = ${f.width_m.toFixed(2)} × ${f.height_m.toFixed(2)} m`],
      ['原点', `(${f.origin[0]}, ${f.origin[1]}) m，yaw ${f.origin[2]} rad`], ['范围', f.bounds.map((v: number) => v.toFixed(2)).join(', ')],
      ['模式', `${ins.meta?.mode} · negate ${ins.meta?.negate} · 占据 > ${ins.meta?.occupied_thresh} · 空闲 < ${ins.meta?.free_thresh}`]);
    if (ins.stats) rows.push(['栅格', `空闲 ${ins.stats.free} · 占据 ${ins.stats.occupied} · 未知 ${ins.stats.unknown}（${(ins.stats.unknown_fraction * 100).toFixed(1)}%）`]);
  }
  if (report.subtype === 'vector' && ins.crs) {
    rows.push(['坐标系', `${ins.crs.kind === 'geographic' ? '经纬度' : ins.crs.kind === 'projected' ? '投影坐标' : '未知'} · ${ins.crs.source}`]);
    if (ins.transform) rows.push(['换算', `${ins.transform.source_crs} → ${ins.transform.projected_crs}（${ins.transform.method === 'utm' ? 'UTM 投影' : '平移'}），原点 ${ins.transform.origin_projected.map((v: number) => v.toFixed(1)).join(', ')}`]);
    if (ins.summary) rows.push(['范围', `${ins.summary.size_m[0]} × ${ins.summary.size_m[1]} m · ${ins.summary.features} 个要素 · 孔洞 ${ins.summary.holes}`],
      ['用途', Object.entries(ins.summary.roles as Record<string, number>).map(([k, v]) => `${k} ${v}`).join(' · ')]);
  }
  if (report.subtype === 'image' && ins.image) rows.push(['图片', `${ins.image.width_px} × ${ins.image.height_px} 像素 · ${ins.image.format}`]);
  if ((report.subtype === 'gltf' || report.subtype === 'mesh') && ins.bounds) {
    rows.push(['包围盒', `${ins.bounds.size.map((v: number) => v.toFixed(3)).join(' × ')}（模型坐标）`]);
    if (ins.counts) rows.push(['内容', `网格 ${ins.counts.meshes} · 材质 ${ins.counts.materials} · 贴图 ${ins.counts.images} · 动画 ${ins.counts.animations}`]);
  }
  if (report.subtype === 'urdf' || report.subtype === 'sdf_model') {
    rows.push(['结构', `${ins.links ?? 0} 个 link，碰撞 ${(ins.collision_links ?? []).length}，惯性 ${(ins.inertial_links ?? []).length}`],
      ['驱动', ins.drive ? `${ins.drive}（${ins.drive_source}）` : '未发现'], ['传感器', (ins.sensors ?? []).join(', ') || '无']);
  }
  if (!rows.length) return null;
  return (
    <div className={s.kv} style={{ marginTop: 8 }}>
      {rows.flatMap(([k, v]) => [<span key={k}>{k}</span>, <span key={k + 'v'}>{v}</span>])}
    </div>
  );
}
