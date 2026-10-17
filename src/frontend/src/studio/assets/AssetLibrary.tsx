/** Asset library: maps, vehicles, obstacles / facilities and task-map templates, plus what this machine already has. */
import { useEffect, useMemo, useState, type DragEvent } from 'react';
import { Box, Car, FileUp, Image as ImageIcon, Layers, Map as MapIcon, RefreshCw, Sprout, Tractor, Warehouse } from 'lucide-react';
import { lab, useLabResource } from '../../lab/api';
import { Button, EmptyState, Input, Notice, Segmented, Spinner, Switch } from '../../lab/ui';
import { useStudio } from '../store';
import { assetsApi, KIND_LABEL, LEVEL_LABEL, localUrl, SUBTYPE_LABEL, type AssetKind, type AssetSummary, type LocalCatalog } from './api';
import { useAssets } from './store';
import s from './assets.module.css';

const KIND_ICON: Record<AssetKind, typeof MapIcon> = { map: MapIcon, vehicle: Tractor, facility: Warehouse, scenario: Layers };

export function AssetLibrary() {
  const st = useAssets();
  const [tab, setTab] = useState<'assets' | 'local' | 'templates'>('assets');
  const [over, setOver] = useState(false);
  useEffect(() => {
    void st.refresh();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    const files = [...e.dataTransfer.files];
    if (files.length) st.openImport(files);
  };
  return (
    <div className={`${s.panel} ${s.drop}`} data-over={over || undefined}
      onDragOver={(e) => { if (e.dataTransfer.types.includes('Files')) { e.preventDefault(); setOver(true); } }}
      onDragLeave={() => setOver(false)} onDrop={onDrop}>
      <div className={s.head}>
        <div className={s.row}>
          <Segmented<typeof tab> value={tab} onChange={setTab} label="资产来源"
            options={[{ value: 'assets', label: '资产' }, { value: 'templates', label: '场景模板' }, { value: 'local', label: '本机资源' }]} />
          <span className={s.grow} />
          <Button size="sm" variant="primary" icon={FileUp} onClick={() => st.openImport()}>导入</Button>
        </div>
        {tab === 'assets' && (
          <>
            <div className={s.row}>
              <Segmented<AssetKind | 'all'> value={st.kind} onChange={(kind) => st.setFilter({ kind })} label="类别"
                options={[{ value: 'all', label: '全部' }, { value: 'map', label: '地图' }, { value: 'vehicle', label: '车辆' }, { value: 'facility', label: '设施' }, { value: 'scenario', label: '场景' }]} />
            </div>
            <div className={s.row}>
              <Input className={s.grow} placeholder="搜索名称、分类、标签" value={st.q} onChange={(e) => st.setFilter({ q: e.target.value })} />
              <Switch checked={st.archived} onChange={(archived) => st.setFilter({ archived })} label="含归档" />
              <Button size="sm" variant="plain" icon={RefreshCw} title="刷新" onClick={() => void st.refresh()} />
            </div>
          </>
        )}
      </div>
      <div className={s.scroll}>
        {tab === 'assets' && <AssetGrid items={st.list.filter((a) => st.kind !== 'all' || a.kind !== 'scenario')} loading={st.loading} error={st.error} />}
        {tab === 'templates' && <Templates />}
        {tab === 'local' && <LocalResources />}
      </div>
    </div>
  );
}

function Thumb({ a }: { a: AssetSummary }) {
  const Icon = KIND_ICON[a.kind] ?? Box;
  return (
    <div className={s.thumb} style={a.thumb ? { backgroundImage: `url("${a.thumb}")` } : undefined}>
      {!a.thumb && (a.subtype === 'builtin' ? <Car size={34} /> : <Icon size={34} />)}
    </div>
  );
}

function AssetGrid({ items, loading, error }: { items: AssetSummary[]; loading: boolean; error: string | null }) {
  const st = useAssets();
  if (error) return <div style={{ padding: 12 }}><Notice tone="error">{error}</Notice></div>;
  if (loading && !items.length) return <div style={{ padding: 14 }}><Spinner /></div>;
  if (!items.length) {
    return <EmptyState icon={FileUp} title="还没有资产" detail="拖入 ROS 地图（YAML + PGM/PNG）、GeoJSON 田块、图片、GLB / glTF、URDF、SDF 或 zip，或从「本机资源」引用 Gazebo 模型。" />;
  }
  return (
    <div className={s.grid}>
      {items.map((a) => {
        const level = a.level ? LEVEL_LABEL[a.level] : null;
        return (
          <button key={a.id} type="button" className={s.card} aria-current={st.selected === a.id || undefined} onClick={() => void st.select(a.id)}>
            <Thumb a={a} />
            <div className={s.cardBody}>
              <span className={s.cardTitle} title={a.name}>{a.name}</span>
              <span className={s.cardMeta}>
                <span className={s.chip}>{KIND_LABEL[a.kind]}</span>
                <span>{SUBTYPE_LABEL[a.subtype] ?? a.subtype}</span>
              </span>
              <span className={s.cardMeta}>
                {level && <span className={s.chip} data-tone={level.tone}>{level.text}</span>}
                {a.confirmed != null && !a.builtin && (
                  <span className={s.chip} data-tone={a.confirmed ? 'green' : 'orange'}>
                    {a.subtype === 'image' ? (a.confirmed ? '已标定' : '未标定') : a.kind === 'map' ? (a.confirmed ? '坐标已确认' : '坐标待确认') : (a.confirmed ? '朝向已确认' : '朝向待确认')}
                  </span>
                )}
                {a.locked && !a.builtin && <span className={s.chip} title="当前版本已锁定，修改会生成新版本">锁定</span>}
                {a.errors > 0 && <span className={s.chip} data-tone="red">{a.errors} 个错误</span>}
                <span>v{a.current}{a.versions > 1 ? ` / ${a.versions}` : ''}</span>
                {a.archived && <span className={s.chip}>已归档</span>}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

function Templates() {
  const assets = useAssets();
  const studioSt = useStudio();
  const examples = useLabResource('asset-tpl-examples', () => fetch('/lab/api/compose/examples').then((r) => r.json() as Promise<{ examples: string[] }>));
  const scenarios = useLabResource('asset-tpl-scenarios', () => lab.scenarios());
  const saved = assets.list.filter((a) => a.kind === 'scenario');
  const coverage = (scenarios.data?.scenarios ?? []).filter((x) => x.problem_class === 'coverage').slice(0, 6);
  const groups = useMemo(() => {
    const ex = examples.data?.examples ?? [];
    const pick = (re: RegExp) => ex.filter((t) => re.test(t));
    return [
      { title: '果园行间巡检 / 运输', icon: Sprout, items: pick(/果园|猕猴桃|葡萄|茶|巡检|运输/) },
      { title: '地块间采收运输', icon: Tractor, items: pick(/采收|收获|运送|地块之间|转运|运输/) },
    ];
  }, [examples.data]);
  return (
    <div>
      <div className={s.section}>
        <h4>保存的任务地图模板</h4>
        <p className={s.hint}>在「任务规划」里把当前场景存为模板后出现在这里；实例化得到一份新的可编辑场景，模板本身不变。</p>
        {saved.length ? (
          <ul className={s.list}>
            {saved.map((a) => (
              <li key={a.id}>
                <div className={s.item}>
                  <div className={s.itemThumb}><Layers size={18} /></div>
                  <div><div className={s.itemTitle}>{a.name}</div><div className={s.itemSub}>v{a.current} · {new Date(a.updated_utc).toLocaleString()}</div></div>
                  <Button size="sm" onClick={async () => {
                    try {
                      const sc = await assetsApi.instantiate(a.id);
                      studioSt.notify('ok', `已从模板生成场景 ${sc.title}`);
                      studioSt.setWorkspace('plan');
                      location.hash = `#/plan/${encodeURIComponent(sc.id)}`;
                    } catch (e) { studioSt.notify('error', (e as Error).message); }
                  }}>实例化</Button>
                </div>
              </li>
            ))}
          </ul>
        ) : <p className={s.hint}>暂无。</p>}
      </div>
      {groups.map((g) => (
        <div key={g.title} className={s.section}>
          <h4><g.icon size={13} />{g.title}</h4>
          {g.items.length ? g.items.map((t) => (
            <button key={t} type="button" className={s.item} style={{ gridTemplateColumns: '1fr auto' }}
              onClick={async () => {
                studioSt.setWorkspace('plan');
                studioSt.setComposeText(t);
                await studioSt.composeFromText();
              }}>
              <span className={s.itemSub} style={{ whiteSpace: 'normal' }}>{t}</span>
              <span className={s.chip}>生成</span>
            </button>
          )) : <p className={s.hint}>没有对应的示例句。</p>}
        </div>
      ))}
      <div className={s.section}>
        <h4><MapIcon size={13} />田块覆盖</h4>
        <p className={s.hint}>覆盖作业场景（Fields2Cover）：打开后可改作业幅宽、转弯半径与地头宽度。</p>
        {coverage.map((x) => (
          <button key={x.id} type="button" className={s.item} style={{ gridTemplateColumns: '1fr auto' }}
            onClick={() => { studioSt.setWorkspace('plan'); location.hash = `#/plan/${encodeURIComponent(x.id)}`; }}>
            <span><span className={s.itemTitle}>{x.title}</span><br /><span className={s.itemSub}>{x.summary}</span></span>
            <span className={s.chip}>打开</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function LocalResources() {
  const cat = useLabResource<LocalCatalog>('asset-local-catalog', () => assetsApi.local());
  const st = useAssets();
  const notify = useStudio((x) => x.notify);
  const [busy, setBusy] = useState<string | null>(null);
  const run = async (key: string, body: Parameters<typeof assetsApi.importLocal>[0]) => {
    setBusy(key);
    try {
      const a = await assetsApi.importLocal(body);
      st.apply(a);
      await st.select(a.id);
      notify('ok', `已导入 ${a.name}（本机资源，${a.versions[0].source.license ?? '许可证未声明'}）`);
    } catch (e) {
      notify('error', (e as Error).message);
    } finally {
      setBusy(null);
    }
  };
  if (cat.error) return <div style={{ padding: 12 }}><Notice tone="error">{cat.error.message}</Notice></div>;
  if (!cat.data) return <div style={{ padding: 14 }}><Spinner /></div>;
  return (
    <div>
      <div className={s.section}>
        <h4><Warehouse size={13} />Gazebo Fuel 缓存（{cat.data.fuel_models.length}）</h4>
        <p className={s.hint}>仿真世界下载过的模型。导入为障碍物 / 设施资产（复制一份到资产库，保留来源与版本）。</p>
      </div>
      <ul className={s.list}>
        {cat.data.fuel_models.map((m) => (
          <li key={m.path}>
            <div className={s.item}>
              <div className={s.itemThumb} style={m.thumbnails[0] ? { backgroundImage: `url("${localUrl('fuel', m.thumbnails[0])}")` } : undefined}>{!m.thumbnails[0] && <Box size={18} />}</div>
              <div>
                <div className={s.itemTitle}>{m.title}</div>
                <div className={s.itemSub} title={m.description}>{m.owner} · v{m.version} · {(m.size_bytes / 1048576).toFixed(1)} MB</div>
              </div>
              <Button size="sm" disabled={busy !== null || m.size_bytes > 64 * 1048576} title={m.size_bytes > 64 * 1048576 ? '超过 64 MB，只在 Gazebo 世界里引用' : undefined}
                onClick={() => void run(m.path, { root: 'fuel', path: m.path, kind: 'facility', name: m.title, source_uri: m.source_uri, attribution: `${m.owner} · Gazebo Fuel` })}>
                {busy === m.path ? <Spinner /> : '导入'}
              </Button>
            </div>
          </li>
        ))}
      </ul>
      <div className={s.section}>
        <h4><Car size={13} />已安装的 ROS 机器人描述包</h4>
        <p className={s.hint}>只展开本机已安装包里的 Xacro（可信来源）；导入后是 URDF 车辆资产，网格从包内读取。</p>
      </div>
      <ul className={s.list}>
        {cat.data.ros_descriptions.flatMap((d) => d.entries.map((e) => (
          <li key={e}>
            <div className={s.item}>
              <div className={s.itemThumb}><Car size={18} /></div>
              <div><div className={s.itemTitle}>{d.package}</div><div className={s.itemSub}>{e}</div></div>
              <Button size="sm" disabled={busy !== null} onClick={() => void run(e, { root: 'ros', path: e, kind: 'vehicle', name: `${d.package} · ${e.split('/').pop()}` })}>
                {busy === e ? <Spinner /> : '导入'}
              </Button>
            </div>
          </li>
        )))}
      </ul>
      <div className={s.section}>
        <h4><ImageIcon size={13} />Gazebo 世界</h4>
        <p className={s.hint}>作为参考与预览导入；Gazebo 世界不直接提供规划几何。</p>
      </div>
      <ul className={s.list}>
        {cat.data.gazebo_worlds.map((w) => (
          <li key={w.path}>
            <div className={s.item}>
              <div className={s.itemThumb}><MapIcon size={18} /></div>
              <div><div className={s.itemTitle}>{w.name}</div><div className={s.itemSub}>{w.group} · {(w.size_bytes / 1024).toFixed(0)} KB</div></div>
              <Button size="sm" disabled={busy !== null} onClick={() => void run(w.path, { root: w.root, path: w.path, kind: 'map', name: `${w.group} · ${w.name}` })}>
                {busy === w.path ? <Spinner /> : '导入'}
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
