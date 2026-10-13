import { useMemo } from 'react';
import { ArrowUpDown, Search } from 'lucide-react';
import type { Route } from '../app/router';
import { buildHash, navigate, patchParams } from '../app/router';
import { loadCatalog, useAsync } from '../data/api';
import type { Branch, Family, Order, Split, Stream } from '../data/types';
import {
  BRANCH_LABEL,
  FAMILY_LABEL,
  FAMILY_ORDER,
  ORDER_LABEL,
  ORDER_ORDER,
  SPLIT_LABEL,
  SPLIT_ORDER,
  streamTitle,
} from '../data/labels';
import { fmt, fmtSigned } from '../lib/format';
import { Async, EmptyState, Panel } from '../components/ui';
import s from './Samples.module.css';

type SortKey = 'order' | 'BF' | 'BF_then_EoH' | 'SELECTOR' | 'selector_minus_SBS' | 'selector_regret';
type Outcome = 'all' | 'win' | 'tie' | 'loss';

export function Samples({ route }: { route: Route }) {
  const catalog = useAsync('catalog', () => loadCatalog());
  return (
    <div className={s.page}>
      <header className={s.header}>
        <h1 className={s.title}>样本浏览</h1>
        <p className={s.sub}>
          264 条输入流 · 按 split、尺寸族、到达顺序、选择与胜负筛选。同一多重集的三种到达顺序归为一组显示。点击任一行打开回放。
        </p>
      </header>
      <Async state={catalog}>{(data) => <SamplesBody route={route} streams={data.streams} />}</Async>
    </div>
  );
}

function SamplesBody({ route, streams }: { route: Route; streams: Stream[] }) {
  const split = (route.params.get('split') as Split | 'all') ?? 'all';
  const family = (route.params.get('family') as Family | 'all') ?? 'all';
  const order = (route.params.get('order') as Order | 'all') ?? 'all';
  // Training runs have neither a selector decision nor its outcome. Ignore
  // incompatible parameters even in a pasted URL, and clear them on split change.
  const branch = split === 'train' ? 'all' : (route.params.get('branch') as Branch | 'all') ?? 'all';
  const outcome = split === 'train' ? 'all' : (route.params.get('outcome') as Outcome) ?? 'all';
  const q = route.params.get('q') ?? '';
  const sort = (route.params.get('sort') as SortKey) ?? 'order';
  const dir = (route.params.get('dir') as 'asc' | 'desc') ?? 'asc';

  const filtered = useMemo(() => {
    const qLower = q.trim().toLowerCase();
    const rows = streams.filter((st) => {
      if (split !== 'all' && st.split !== split) return false;
      if (family !== 'all' && st.family !== family) return false;
      if (order !== 'all' && st.order !== order) return false;
      const r = st.results;
      if (branch !== 'all' && r.selected_branch !== branch) return false;
      if (outcome !== 'all') {
        const d = r.selector_minus_SBS;
        if (d === null || d === undefined) return false;
        if (outcome === 'win' && !(d < 0)) return false;
        if (outcome === 'tie' && d !== 0) return false;
        if (outcome === 'loss' && !(d > 0)) return false;
      }
      if (qLower && !st.instance_id.toLowerCase().includes(qLower) && !st.group_id.toLowerCase().includes(qLower)) return false;
      return true;
    });
    const famRank = (f: Family) => FAMILY_ORDER.indexOf(f);
    const ordRank = (o: Order) => ORDER_ORDER.indexOf(o);
    const val = (st: Stream): number | string => {
      const r = st.results;
      switch (sort) {
        case 'BF':
          return r.BF;
        case 'BF_then_EoH':
          return r.BF_then_EoH;
        case 'SELECTOR':
          return r.SELECTOR ?? Number.POSITIVE_INFINITY;
        case 'selector_minus_SBS':
          return r.selector_minus_SBS ?? Number.POSITIVE_INFINITY;
        case 'selector_regret':
          return r.selector_regret ?? Number.POSITIVE_INFINITY;
        default:
          return 0;
      }
    };
    rows.sort((a, b) => {
      let cmp: number;
      if (sort === 'order') {
        cmp =
          SPLIT_ORDER.indexOf(a.split) - SPLIT_ORDER.indexOf(b.split) ||
          famRank(a.family) - famRank(b.family) ||
          a.replicate - b.replicate ||
          ordRank(a.order) - ordRank(b.order);
      } else {
        const av = val(a);
        const bv = val(b);
        cmp = typeof av === 'number' && typeof bv === 'number' ? av - bv : String(av).localeCompare(String(bv));
        if (cmp === 0) cmp = a.instance_id.localeCompare(b.instance_id);
      }
      return dir === 'desc' ? -cmp : cmp;
    });
    return rows;
  }, [streams, split, family, order, branch, outcome, q, sort, dir]);

  const setParam = (key: string, value: string) => patchParams({
    [key]: value === 'all' || value === '' ? null : value,
    ...(key === 'split' && value === 'train' ? { branch: null, outcome: null } : {}),
  });
  const toggleSort = (key: SortKey) => {
    if (sort === key) patchParams({ dir: dir === 'asc' ? 'desc' : 'asc' });
    else patchParams({ sort: key, dir: key === 'order' ? 'asc' : 'asc' });
  };

  const comparingBranch = split !== 'train';

  return (
    <>
      <Panel>
        <div className={s.filters}>
          <ChipGroup label="集合" value={split} options={[['all', '全部'], ...SPLIT_ORDER.map((x) => [x, SPLIT_LABEL[x]] as [string, string])]} onChange={(v) => setParam('split', v)} />
          <ChipGroup label="顺序" value={order} options={[['all', '全部'], ...ORDER_ORDER.map((x) => [x, ORDER_LABEL[x]] as [string, string])]} onChange={(v) => setParam('order', v)} />
          <ChipGroup
            label="选择"
            value={branch}
            options={[['all', '全部'], ['BF', BRANCH_LABEL.BF], ['BF_then_EoH', BRANCH_LABEL.BF_then_EoH]]}
            onChange={(v) => setParam('branch', v)}
            disabled={!comparingBranch}
          />
          <ChipGroup
            label="对 SBS"
            value={outcome}
            options={[['all', '全部'], ['win', '胜'], ['tie', '平'], ['loss', '负']]}
            onChange={(v) => setParam('outcome', v)}
            disabled={!comparingBranch}
          />
        </div>
        <div className={s.filters2}>
          <div className={s.familyChips}>
            <span className={s.chipLabel}>尺寸族</span>
            <button type="button" className={s.chip} data-active={family === 'all' || undefined} onClick={() => setParam('family', 'all')}>
              全部
            </button>
            {FAMILY_ORDER.map((f) => (
              <button key={f} type="button" className={s.chip} data-active={family === f || undefined} onClick={() => setParam('family', f)}>
                {FAMILY_LABEL[f]}
              </button>
            ))}
          </div>
          <label className={s.search}>
            <Search size={15} aria-hidden />
            <input
              type="search"
              placeholder="搜索 instance_id 或 group_id"
              value={q}
              onChange={(e) => setParam('q', e.target.value)}
              aria-label="搜索样本"
            />
          </label>
        </div>
        <p className={s.count}>
          符合条件 <strong className="num">{filtered.length}</strong> / {streams.length} 条
        </p>
      </Panel>

      {filtered.length === 0 ? (
        <EmptyState title="没有符合条件的样本" detail="放宽筛选条件，或清空搜索框。" />
      ) : (
        <div className={s.tableWrap}>
          <table className={s.table}>
            <thead>
              <tr>
                <th scope="col" className={s.thLeft}>
                  样本
                </th>
                <th scope="col">集合</th>
                <SortTh label="全程 BF" active={sort === 'BF'} dir={dir} onClick={() => toggleSort('BF')} />
                <SortTh label="BF→EoH" active={sort === 'BF_then_EoH'} dir={dir} onClick={() => toggleSort('BF_then_EoH')} />
                <SortTh label="选择器" active={sort === 'SELECTOR'} dir={dir} onClick={() => toggleSort('SELECTOR')} />
                <th scope="col">选择</th>
                <SortTh label="选择器−SBS" active={sort === 'selector_minus_SBS'} dir={dir} onClick={() => toggleSort('selector_minus_SBS')} />
                <SortTh label="后悔" active={sort === 'selector_regret'} dir={dir} onClick={() => toggleSort('selector_regret')} />
              </tr>
            </thead>
            <tbody>
              {filtered.map((st, i) => {
                const r = st.results;
                const prevGroup = i > 0 ? filtered[i - 1].group_id : null;
                const newGroup = st.group_id !== prevGroup;
                const d = r.selector_minus_SBS;
                return (
                  <tr
                    key={st.instance_id}
                    className={s.row}
                    data-newgroup={newGroup && sort === 'order' ? true : undefined}
                    tabIndex={0}
                    role="link"
                    onClick={() => openReplay(st)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        openReplay(st);
                      }
                    }}
                  >
                    <td className={s.tdLeft}>
                      <span className={s.sampleName}>{streamTitle(st)}</span>
                      <span className={`${s.sampleId} mono`}>{st.order}</span>
                    </td>
                    <td>
                      <span className={s.splitTag} data-split={st.split}>
                        {SPLIT_LABEL[st.split]}
                      </span>
                    </td>
                    <td className="num">{fmt(r.BF, 0)}</td>
                    <td className="num">{fmt(r.BF_then_EoH, 0)}</td>
                    <td className="num">{r.SELECTOR == null ? '—' : fmt(r.SELECTOR, 0)}</td>
                    <td>{r.selected_branch ? BRANCH_LABEL[r.selected_branch] : '—'}</td>
                    <td className={`num ${s.delta}`} data-tone={d == null ? undefined : d < 0 ? 'save' : d > 0 ? 'harm' : 'zero'}>
                      {d == null ? '—' : fmtSigned(d, 0)}
                    </td>
                    <td className="num">{r.selector_regret == null ? '—' : fmt(r.selector_regret, 0)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function openReplay(st: Stream) {
  const a = st.split === 'train' ? 'BF' : 'SELECTOR';
  const b = st.split === 'train' ? 'BF_then_EoH' : 'SBS';
  navigate(buildHash('replay', st.instance_id, { a, b, t: 500, view: 'observed' }));
}

function ChipGroup({
  label,
  value,
  options,
  onChange,
  disabled,
}: {
  label: string;
  value: string;
  options: [string, string][];
  onChange: (v: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className={s.chipGroup} data-disabled={disabled || undefined}>
      <span className={s.chipLabel}>{label}</span>
      {options.map(([v, l]) => (
        <button key={v} type="button" className={s.chip} data-active={value === v || undefined} onClick={() => !disabled && onChange(v)} disabled={disabled}>
          {l}
        </button>
      ))}
    </div>
  );
}

function SortTh({ label, active, dir, onClick }: { label: string; active: boolean; dir: 'asc' | 'desc'; onClick: () => void }) {
  return (
    <th scope="col" className={s.sortTh}>
      <button type="button" className={s.sortBtn} onClick={onClick} data-active={active || undefined}>
        {label}
        <ArrowUpDown size={12} aria-hidden />
        {active && <span className="visually-hidden">{dir === 'asc' ? '升序' : '降序'}</span>}
      </button>
    </th>
  );
}
