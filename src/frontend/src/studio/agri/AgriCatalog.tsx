import { useEffect, useRef, useState } from 'react';
import { Button, Input, Notice, Select } from '../../lab/ui';
import { useStudio } from '../store';
import { ENVIRONMENTS, OPERATIONS, PLANNING_PROBLEMS, SERVICE_OBJECTS, type AgriTaskPattern } from './taxonomy';
import { patternStatus } from './patterns';
import { buildPattern, defaultValues, filterPatterns, importPattern, STATUS_LABELS } from './catalog';
import { downloadFile, downloadMatrices } from './export';
import s from '../panels/panels.module.css';

export function AgriCatalog() {
  const [environment, setEnvironment] = useState('');
  const [operation, setOperation] = useState('');
  const [status, setStatus] = useState('');
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
      <Button size="sm" onClick={() => downloadMatrices('json')}>下载完整矩阵 JSON</Button>
      <Button size="sm" onClick={() => downloadMatrices('csv')}>下载完整矩阵 CSV</Button>
    </div>
    {!patterns.length && <p role="status">此组合暂无模式，请调整筛选条件。</p>}
    {patterns.map((p) => <PatternCard key={p.id} pattern={p} />)}
  </section>;
}

export function PatternCard({ pattern: p }: { pattern: AgriTaskPattern }) {
  const [values, setValues] = useState(() => defaultValues(p));
  const [seed, setSeed] = useState('42');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const pending = useRef(false);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const notify = useStudio((st) => st.notify);
  const status = patternStatus(p);
  async function submit() {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError('');
    const startingHash = location.hash;
    try {
      const scenario = await importPattern(p, values, seed.trim() ? Number(seed) : NaN);
      notify('ok', `已校验并保存 ${scenario.title}，请在推荐与求解中继续`);
      if (mounted.current && location.hash === startingHash) location.hash = `#/plan/${encodeURIComponent(scenario.id)}`;
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      setError(message); notify('error', `农业模板导入失败：${message}`);
    } finally { pending.current = false; setBusy(false); }
  }
  return <details className={s.algCard}>
    <summary>{p.name} · {STATUS_LABELS[status]}</summary>
    <p>{p.summary}</p><p>{p.modeling}</p>
    <p>目标：{SERVICE_OBJECTS.find((x) => x.id === p.serviceObject)?.name} / {PLANNING_PROBLEMS.find((x) => x.id === p.planningProblem)?.name}</p>
    {p.proxyModel && <Notice tone="warn">实际代理：{SERVICE_OBJECTS.find((x) => x.id === p.proxyModel!.serviceObject)?.name} / {PLANNING_PROBLEMS.find((x) => x.id === p.proxyModel!.planningProblem)?.name}。{p.proxyModel.note}</Notice>}
    {p.approximation && <Notice tone="warn">近似限制：{p.approximation}</Notice>}
    <ul>{Object.entries(p.capabilities).map(([axis, cap]) => <li key={axis}>{({ defined: '定义', editable: '编辑', solvable: '求解', checkable: '验算', simulatable: '仿真', experimented: '实验' } as Record<string, string>)[axis]}：{cap.level} · {cap.note}</li>)}</ul>
    {p.proposal ? <><Notice tone="warn">提案不可提交：{p.proposal.missing.join('；')}</Notice><p>接口草案：{p.proposal.apiDraft}</p></> : <>
      <fieldset disabled={busy} style={{ border: 0, padding: 0 }}>
        {(p.runnable?.params ?? []).map((param) => <label key={param.key} style={{ display: 'block', marginBottom: 8 }}>
          {param.label}{param.unit ? ` (${param.unit})` : ''}
          {param.type === 'select' ? <Select aria-label={`${p.name} ${param.label}`} value={String(values[param.key])} onChange={(e) => setValues({ ...values, [param.key]: e.target.value })}>
            {param.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </Select> : param.type === 'boolean' ? <input type="checkbox" aria-label={`${p.name} ${param.label}`} checked={Boolean(values[param.key])} onChange={(e) => setValues({ ...values, [param.key]: e.target.checked })} />
            : <Input type="number" step="any" min={param.min} max={param.max} aria-label={`${p.name} ${param.label}`} value={typeof values[param.key] === 'number' && Number.isNaN(values[param.key]) ? '' : String(values[param.key])} onChange={(e) => setValues({ ...values, [param.key]: e.target.value === '' ? NaN : Number(e.target.value) })} />}
          {param.help && <small>{param.help}</small>}
        </label>)}
        <label>随机种子<Input type="number" min={0} max={4294967295} step={1} aria-label={`${p.name} 随机种子`} value={seed} onChange={(e) => setSeed(e.target.value)} /></label>
        <Button onClick={() => {
          try {
            const built = buildPattern(p, values, seed.trim() ? Number(seed) : NaN);
            downloadFile({ fileName: `${p.id}-seed-${seed}.json`, mime: 'application/json;charset=utf-8', serialized: JSON.stringify(built, null, 2) });
            setError('');
          } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
        }}>下载原始场景 JSON</Button>
        <Button onClick={() => void submit()} disabled={busy || !p.runnable}>{busy ? '校验并保存中…' : '校验并导入任务规划'}</Button>
      </fieldset>
      <p>保存后可继续编辑地图、选择算法并求解；仿真可用性由当前场景与车型决定。</p>
    </>}
    {error && <div role="alert"><Notice tone="error">{error}</Notice></div>}
  </details>;
}
