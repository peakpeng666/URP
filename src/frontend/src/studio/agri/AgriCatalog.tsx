import { useEffect, useMemo, useRef, useState } from 'react';
import { Button, Input, Notice, Select } from '../../lab/ui';
import { useStudio } from '../store';
import { ENVIRONMENTS, OPERATIONS, PLANNING_PROBLEMS, SERVICE_OBJECTS, type AgriTaskPattern } from './taxonomy';
import { AGRI_PATTERNS, patternStatus } from './patterns';
import { buildPattern, createImportGuard, defaultValues, filterPatterns, importPattern, STATUS_LABELS } from './catalog';
import { downloadFile, downloadMatrices } from './export';
import { clearDraft, lastImport, recordImport, loadDraft, loadFilters, onForeignDraftChange, saveDraft, saveFilters } from './drafts';
import { extractPreview, previewIssues } from './preview';
import { PreviewMap } from './PreviewMap';
import s from '../panels/panels.module.css';

export function AgriCatalog({ visible = true }: { visible?: boolean } = {}) {
  const [initialFilters] = useState(loadFilters);
  const [environment, setEnvironment] = useState(initialFilters.environment);
  const [operation, setOperation] = useState(initialFilters.operation);
  const [status, setStatus] = useState(initialFilters.status);
  useEffect(() => { saveFilters({ environment, operation, status }); }, [environment, operation, status]);
  const [downloadError, setDownloadError] = useState('');
  function download(format: 'json' | 'csv') {
    try { downloadMatrices(format); setDownloadError(''); }
    catch (e) { setDownloadError(e instanceof Error ? e.message : String(e)); }
  }
  const patterns = filterPatterns(environment, operation, status);
  return <section aria-label="农业任务目录" className={s.pad}>
    <p>选择农业任务并调整参数，保存后进入现有任务规划流程。</p>
    <label>生产环境<Select aria-label="生产环境" value={environment} onChange={(e) => setEnvironment(e.target.value)}>
      <option value="">全部环境</option>{ENVIRONMENTS.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
    </Select></label>
    <label>农业作业<Select aria-label="农业作业" value={operation} onChange={(e) => setOperation(e.target.value)}>
      <option value="">全部作业</option>{OPERATIONS.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
    </Select></label>
    <label>模式状态<Select aria-label="模式状态" value={status} onChange={(e) => setStatus(e.target.value)}>
      <option value="">全部状态</option>{Object.entries(STATUS_LABELS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
    </Select></label>
    <p>当前 {patterns.length} 个模式</p>
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      <Button size="sm" onClick={() => download('json')}>下载完整矩阵 JSON</Button>
      <Button size="sm" onClick={() => download('csv')}>下载完整矩阵 CSV</Button>
    </div>
    {downloadError && <div role="alert"><Notice tone="error">下载失败：{downloadError}</Notice></div>}
    {!patterns.length && <p role="status">此组合暂无模式，请调整筛选条件。</p>}
    {AGRI_PATTERNS.map((p) => <div key={p.id} hidden={!patterns.some((visible) => visible.id === p.id)}><PatternCard pattern={p} active={visible && patterns.some((shown) => shown.id === p.id)} /></div>)}
  </section>;
}

export function PatternCard({ pattern: p, active = true }: { pattern: AgriTaskPattern; active?: boolean }) {
  const [initial] = useState(() => (p.runnable ? loadDraft(p, defaultValues(p)) : { values: defaultValues(p), seed: '42', restored: false, notice: '' }));
  const [values, setValues] = useState(initial.values);
  const [seed, setSeed] = useState(initial.seed);
  const [draftNotice, setDraftNotice] = useState(initial.notice);
  const [saveError, setSaveError] = useState('');
  const [open, setOpen] = useState(false);
  const [prior, setPrior] = useState(() => lastImport(p.id));
  const touched = useRef(false);
  useEffect(() => {
    if (!p.runnable || !touched.current) return;
    const t = setTimeout(() => setSaveError(saveDraft(p, values, seed)), 300);
    return () => clearTimeout(t);
  }, [p, values, seed]);
  useEffect(() => onForeignDraftChange(p.id, () => setDraftNotice('另一个标签页修改了这个模式的草稿；本页保留当前内容，刷新后会读取较新的那份。')), [p.id]);
  const edit = (next: Record<string, unknown>) => { touched.current = true; setValues(next); };
  const editSeed = (next: string) => { touched.current = true; setSeed(next); };
  function resetDraft() {
    clearDraft(p.id); touched.current = false;
    setValues(defaultValues(p)); setSeed('42'); setDraftNotice('已清除本机草稿，恢复默认参数。'); setSaveError('');
  }
  const built = useMemo(() => {
    if (!open || !p.runnable) return null;
    try { const b = buildPattern(p, values, seed.trim() ? Number(seed) : NaN); const pv = extractPreview(b); return { preview: pv, issues: previewIssues(pv), error: '' }; }
    catch (e) { return { preview: null, issues: [], error: e instanceof Error ? e.message : String(e) }; }
  }, [open, p, values, seed]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const guard = useRef(createImportGuard());
  const mounted = useRef(true);
  const activeNow = useRef(active);
  activeNow.current = active;
  useEffect(() => { if (!active) guard.current.invalidateNavigation(); }, [active]);
  useEffect(() => {
    mounted.current = true;
    const changed = () => guard.current.invalidateNavigation();
    window.addEventListener('hashchange', changed);
    return () => { mounted.current = false; changed(); window.removeEventListener('hashchange', changed); };
  }, []);
  const notify = useStudio((st) => st.notify);
  const status = patternStatus(p);
  async function submit() {
    const ticket = guard.current.begin();
    if (ticket === null) return;
    setBusy(true); setError('');
    const startingHash = location.hash;
    try {
      const scenario = await importPattern(p, values, seed.trim() ? Number(seed) : NaN);
      const rec = { scenarioId: scenario.id, title: scenario.title, seed, at: new Date().toISOString() };
      recordImport(p.id, rec); if (mounted.current) setPrior(rec);
      notify('ok', `已校验并保存 ${scenario.title}，请在推荐与求解中继续`);
      if (mounted.current && activeNow.current && guard.current.canNavigate(ticket) && location.hash === startingHash) location.hash = `#/plan/${encodeURIComponent(scenario.id)}`;
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      if (mounted.current) setError(message); notify('error', `农业模板导入失败：${message}`);
    } finally { guard.current.finish(); if (mounted.current) setBusy(false); }
  }
  return <details className={s.algCard} onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}>
    <summary>{p.name} · {STATUS_LABELS[status]}</summary>
    <p>{p.summary}</p><p>{p.modeling}</p>
    <p>目标：{SERVICE_OBJECTS.find((x) => x.id === p.serviceObject)?.name} / {PLANNING_PROBLEMS.find((x) => x.id === p.planningProblem)?.name}</p>
    {p.proxyModel && <Notice tone="warn">实际代理：{SERVICE_OBJECTS.find((x) => x.id === p.proxyModel!.serviceObject)?.name} / {PLANNING_PROBLEMS.find((x) => x.id === p.proxyModel!.planningProblem)?.name}。{p.proxyModel.note}</Notice>}
    {p.approximation && <Notice tone="warn">近似限制：{p.approximation}</Notice>}
    <ul>{Object.entries(p.capabilities).map(([axis, cap]) => <li key={axis}>{({ defined: '定义', editable: '编辑', solvable: '求解', checkable: '验算', simulatable: '仿真', experimented: '实验' } as Record<string, string>)[axis]}：{cap.level} · {cap.note}</li>)}</ul>
    {p.proposal ? <><Notice tone="warn">提案不可提交：{p.proposal.missing.join('；')}</Notice><p>接口草案：{p.proposal.apiDraft}</p></> : <>
      {draftNotice && <p role="status">{draftNotice}</p>}
      {saveError && <Notice tone="warn">{saveError}</Notice>}
      {built?.preview && <PreviewMap preview={built.preview} issues={built.issues} title={p.name} />}
      {built?.error && <Notice tone="warn">当前参数无法生成预览：{built.error}</Notice>}
      <fieldset disabled={busy} style={{ border: 0, padding: 0 }}>
        {(p.runnable?.params ?? []).map((param) => <label key={param.key} style={{ display: 'block', marginBottom: 8 }}>
          {param.label}{param.unit ? ` (${param.unit})` : ''}
          {param.type === 'select' ? <Select aria-label={`${p.name} ${param.label}`} value={String(values[param.key])} onChange={(e) => edit({ ...values, [param.key]: e.target.value })}>
            {param.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </Select> : param.type === 'boolean' ? <input type="checkbox" aria-label={`${p.name} ${param.label}`} checked={Boolean(values[param.key])} onChange={(e) => edit({ ...values, [param.key]: e.target.checked })} />
            : <Input type="number" step="any" min={param.min} max={param.max} aria-label={`${p.name} ${param.label}`} value={typeof values[param.key] === 'number' && Number.isNaN(values[param.key]) ? '' : String(values[param.key])} onChange={(e) => edit({ ...values, [param.key]: e.target.value === '' ? NaN : Number(e.target.value) })} />}
          {param.help && <small>{param.help}</small>}
        </label>)}
        <label>随机种子<Input type="number" min={0} max={4294967295} step={1} aria-label={`${p.name} 随机种子`} value={seed} onChange={(e) => editSeed(e.target.value)} /></label>
        <Button onClick={() => {
          try {
            const built = buildPattern(p, values, seed.trim() ? Number(seed) : NaN);
            downloadFile({ fileName: `${p.id}-seed-${seed}.json`, mime: 'application/json;charset=utf-8', serialized: JSON.stringify(built, null, 2) });
            setError('');
          } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
        }}>下载原始场景 JSON</Button>
        {prior && <Notice tone="info">此模式上次导入为 <a href={`#/plan/${encodeURIComponent(prior.scenarioId)}`}>{prior.title}</a>（种子 {prior.seed}）。再次导入会新建一个场景，不会覆盖你在地图上对那份做的手工编辑；要保留手工成果请继续编辑原场景。</Notice>}
        <Button onClick={resetDraft}>清除草稿并恢复默认</Button>
        <Button onClick={() => void submit()} disabled={busy || !p.runnable}>{busy ? '校验并保存中…' : '校验并导入任务规划'}</Button>
      </fieldset>
      <p>保存后可继续编辑地图、选择算法并求解；仿真可用性由当前场景与车型决定。</p>
    </>}
    {error && <div role="alert"><Notice tone="error">{error}</Notice></div>}
  </details>;
}
