/**
 * Research figures in publication formats. Every figure is drawn by the workbench backend (matplotlib) from the
 * records in view — task map, focused plan and its comparison, the plan's field simulation, the selected study,
 * the map asset — at the exact column width of the chosen journal, with embedded fonts, source data and captions.
 */
import { useEffect, useMemo, useState } from 'react';
import { BookMarked, Copy, Download, FileArchive, ImageOff, Languages, RefreshCw } from 'lucide-react';
import { Badge, Button, EmptyState, Notice, Segmented, Select, Spinner } from '../../lab/ui';
import { useStudio } from '../store';
import { useAssets } from '../assets/store';
import { useReplay } from '../experiment/replay';
import s from './figures.module.css';

type Preset = 'elsevier' | 'ieee' | 'springer' | 'thesis';
type Size = 'single' | 'onehalf' | 'double';
interface CatalogItem { key: string; group: string; title_zh: string; title_en: string; size: Size; available: boolean; reason: string | null }
interface Catalog { figures: CatalogItem[]; sources: Record<string, unknown>; notes: string[]; digest: string }
interface Meta { title: string; caption: { zh: string; en: string }; size_mm: [number, number]; tables: Record<string, number> }

const BASE = '/lab/api/figures';
const GROUPS: [string, string, string][] = [
  ['map', '场景与地图', 'Scenario and map'], ['plan', '规划方案', 'Plans'], ['compare', '算法比较（单个任务地图）', 'Algorithm comparison'],
  ['study', '统计比较（课题）', 'Statistical comparison (study)'], ['recommend', '推荐评估', 'Recommendation'], ['sim', '仿真执行', 'Simulation'],
];
const PRESETS: { value: Preset; label: string; hint: string }[] = [
  { value: 'elsevier', label: 'Elsevier', hint: '90 / 140 / 190 mm · 7.5 pt（Computers and Electronics in Agriculture、Biosystems Engineering）' },
  { value: 'ieee', label: 'IEEE', hint: '88.9 / 181.9 mm · 8 pt（T-RO、RA-L、T-ASE）' },
  { value: 'springer', label: 'Springer', hint: '84 / 174 mm · 8 pt（Precision Agriculture、Autonomous Robots）' },
  { value: 'thesis', label: '学位论文', hint: '120–150 mm · 9 pt · 宋体 / Times New Roman，坐标轴“量/单位”' },
];
const SIZE_LABEL: Record<Size, string> = { single: '单栏', onehalf: '1.5 栏', double: '双栏' };

function useContext() {
  const scenarioId = useStudio((x) => x.scenarioId);
  const focusRun = useStudio((x) => x.focusRun);
  const runIds = useStudio((x) => x.runIds);
  const studyId = useStudio((x) => x.studyId);
  const replay = useReplay((x) => x.result);
  const asset = useAssets((x) => x.asset);
  const version = useAssets((x) => x.version);
  return useMemo(() => {
    const p = new URLSearchParams();
    if (scenarioId) p.set('scenario_id', scenarioId);
    if (focusRun) p.set('run_id', focusRun);
    if (runIds.length > 1) p.set('run_ids', runIds.join(','));
    if (replay && replay.run_id === focusRun) p.set('session_id', replay.session_id);
    if (studyId) p.set('study_id', studyId);
    if (asset?.kind === 'map') {
      p.set('asset_id', asset.id);
      p.set('asset_v', String(version ?? asset.current));
    }
    return p;
  }, [scenarioId, focusRun, runIds, studyId, replay, asset, version]);
}

export function FiguresPanel() {
  const ctx = useContext();
  const [preset, setPreset] = useState<Preset>(() => (localStorage.getItem('figures.preset') as Preset) || 'elsevier');
  const [lang, setLang] = useState<'zh' | 'en'>(() => (localStorage.getItem('figures.lang') as 'zh' | 'en') || 'zh');
  const [dpi, setDpi] = useState('600');
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const [onlyReady, setOnlyReady] = useState(false);
  useEffect(() => {
    try {
      localStorage.setItem('figures.preset', preset);
      localStorage.setItem('figures.lang', lang);
    } catch { /* storage unavailable */ }
  }, [preset, lang]);
  useEffect(() => {
    let alive = true;
    setError(null);
    fetch(`${BASE}/catalog?${ctx}`, { cache: 'no-store' })
      .then(async (r) => { if (!r.ok) throw new Error((await r.json().catch(() => ({}))).message ?? `HTTP ${r.status}`); return r.json(); })
      .then((c: Catalog) => alive && setCatalog(c))
      .catch((e) => alive && setError((e as Error).message));
    return () => { alive = false; };
  }, [ctx, nonce]);
  const style = new URLSearchParams({ preset, lang, dpi });
  const ready = catalog?.figures.filter((f) => f.available).length ?? 0;
  const bundle = (formats: string) => `${BASE}/bundle?${ctx}&${style}&formats=${formats}`;
  const src = catalog?.sources as { scenario?: { title?: string }; runs?: unknown[]; simulation?: { session_id?: string }; study?: { title?: string }; asset?: { id?: string; version?: number } } | undefined;
  return (
    <div className={s.panel}>
      <div className={s.head}>
        <div className={s.row}>
          <b className={s.title}><BookMarked size={14} /> 科研图表</b>
          <Badge tone="blue">{ready} 张可绘制</Badge>
          <span className={s.grow} />
          <Button size="sm" variant="plain" icon={RefreshCw} title="重新读取（新方案 / 仿真 / 课题完成后）" onClick={() => setNonce((n) => n + 1)} />
        </div>
        <div className={s.row}>
          <Segmented<Preset> value={preset} onChange={setPreset} label="期刊版式" options={PRESETS.map((x) => ({ value: x.value, label: x.label, title: x.hint }))} />
          <Segmented<'zh' | 'en'> value={lang} onChange={setLang} label="图中文字" options={[{ value: 'zh', label: '中文' }, { value: 'en', label: 'English', icon: Languages }]} />
          <Select aria-label="位图分辨率" value={dpi} onChange={(e) => setDpi(e.target.value)} title="PNG / TIFF 分辨率（线条图建议 600–1200 dpi）">
            {['300', '600', '1200'].map((d) => <option key={d} value={d}>{d} dpi</option>)}
          </Select>
        </div>
        <p className={s.hint}>{PRESETS.find((x) => x.value === preset)?.hint}。矢量 PDF / EPS 内嵌 TrueType 字体，SVG 文字可编辑；Okabe–Ito 色盲友好配色 + 标记 / 线型，可灰度印刷。</p>
        <div className={s.row}>
          <span className={s.ctx}>
            {src?.scenario ? <span>任务地图：{src.scenario.title}</span> : <span className={s.off}>未打开任务地图</span>}
            {src?.runs?.length ? <span>方案 {src.runs.length} 个</span> : <span className={s.off}>无方案</span>}
            {src?.simulation ? <span>仿真 {src.simulation.session_id}</span> : null}
            {src?.study ? <span>课题：{src.study.title}</span> : <span className={s.off}>未选课题</span>}
            {src?.asset ? <span>地图资产 {src.asset.id} v{src.asset.version}</span> : null}
          </span>
          <span className={s.grow} />
          <label className={s.hint}><input type="checkbox" checked={onlyReady} onChange={(e) => setOnlyReady(e.target.checked)} /> 只看可绘制</label>
          <a className={s.bundle} data-disabled={!ready || undefined} href={ready ? bundle('pdf,svg,png') : undefined} download title="全部可绘制的图：PDF + SVG + PNG、源数据 CSV、中英图注、来源清单">
            <FileArchive size={13} /> 论文图包
          </a>
          <a className={s.link} data-disabled={!ready || undefined} href={ready ? bundle('pdf,svg,eps,png,tiff') : undefined} download>含 EPS / TIFF</a>
        </div>
        {catalog?.notes.map((n) => <Notice key={n} tone="warn">{n}</Notice>)}
      </div>
      <div className={s.scroll}>
        {error && <div className={s.pad}><Notice tone="error">图表服务：{error}</Notice></div>}
        {!catalog && !error && <div className={s.pad}><Spinner /></div>}
        {catalog && GROUPS.map(([g, zh, en]) => {
          const items = catalog.figures.filter((f) => f.group === g && (!onlyReady || f.available));
          if (!items.length) return null;
          return (
            <section key={g} className={s.group}>
              <h4>{lang === 'zh' ? zh : en}</h4>
              <div className={s.grid}>
                {items.map((f) => <FigureCard key={f.key} f={f} ctx={ctx} style={style} lang={lang} digest={catalog.digest} />)}
              </div>
            </section>
          );
        })}
        {catalog && ready === 0 && (
          <EmptyState icon={ImageOff} title="当前没有可绘制的图" detail="打开一个多车任务地图并求解（规划方案图）、在 Gazebo 执行一个方案（仿真图），或在「算法实验」里选中课题（统计图）。" />
        )}
      </div>
    </div>
  );
}

function FigureCard({ f, ctx, style, lang, digest }: { f: CatalogItem; ctx: URLSearchParams; style: URLSearchParams; lang: 'zh' | 'en'; digest: string }) {
  const [size, setSize] = useState<Size>(f.size);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const q = `${ctx}&${style}&size=${size}&v=${digest}`;
  const url = (fmt: string, download = false) => `${BASE}/render/${f.key}?${q}&format=${fmt}${download ? '&download=1' : ''}`;
  useEffect(() => {
    setMeta(null);
    setFailed(null);
    setLoaded(false);
  }, [q]);
  const loadMeta = () => {
    fetch(`${BASE}/meta/${f.key}?${q}`, { cache: 'no-store' })
      .then(async (r) => { if (!r.ok) throw new Error((await r.json().catch(() => ({}))).message ?? `HTTP ${r.status}`); return r.json(); })
      .then(setMeta).catch((e) => setFailed((e as Error).message));
  };
  const title = lang === 'zh' ? f.title_zh : f.title_en;
  if (!f.available) {
    return (
      <div className={s.card} data-off>
        <div className={s.cardHead}><b>{title}</b></div>
        <p className={s.reason}>{f.reason}</p>
      </div>
    );
  }
  return (
    <div className={s.card} data-wide={size === 'double' || undefined}>
      <div className={s.cardHead}>
        <b>{title}</b>
        <span className={s.grow} />
        <Select aria-label="宽度" value={size} onChange={(e) => setSize(e.target.value as Size)}>
          {(['single', 'onehalf', 'double'] as Size[]).map((x) => <option key={x} value={x}>{SIZE_LABEL[x]}</option>)}
        </Select>
      </div>
      <div className={s.preview}>
        {!loaded && !failed && <div className={s.loading}><Spinner /></div>}
        {failed ? <p className={s.reason}>绘制失败：{failed}</p> : (
          <img src={url('svg')} alt={title} loading="lazy" onLoad={() => { setLoaded(true); loadMeta(); }}
            onError={() => { setFailed('预览加载失败'); loadMeta(); }} />
        )}
      </div>
      {meta && (
        <>
          <p className={s.caption}><b>{lang === 'zh' ? '图注　' : 'Caption. '}</b>{meta.caption[lang]}</p>
          <p className={s.meta}>{meta.size_mm[0]} × {meta.size_mm[1]} mm · 源数据 {Object.entries(meta.tables).map(([k, n]) => `${k} ${n} 行`).join('，') || '无'}</p>
        </>
      )}
      <div className={s.actions}>
        {(['pdf', 'svg', 'eps', 'png', 'tiff'] as const).map((fmt) => (
          <a key={fmt} href={url(fmt, true)} download className={s.fmt} title={fmt === 'png' || fmt === 'tiff' ? `${style.get('dpi')} dpi 位图` : '矢量，内嵌字体'}>
            <Download size={11} />{fmt.toUpperCase()}
          </a>
        ))}
        {meta && (
          <Button size="sm" variant="plain" icon={Copy} title="复制图注" onClick={() => void navigator.clipboard?.writeText(meta.caption[lang]).then(() => useStudio.getState().notify('ok', '图注已复制'))} />
        )}
      </div>
    </div>
  );
}
