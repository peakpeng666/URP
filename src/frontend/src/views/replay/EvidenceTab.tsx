import { useEffect, useMemo, useRef, useState } from 'react';
import { ExternalLink, ShieldCheck } from 'lucide-react';
import type { ReplayController } from '../../replay/controller';
import type { SourceRef, Stream } from '../../data/types';
import { loadBytes } from '../../data/api';
import { sha256Hex, hashEngineName } from '../../lib/sha256';
import { fmtBytes, shortHash } from '../../lib/format';
import { StatusMark } from '../../components/Status';
import type { CheckStatus } from '../../app/store';
import s from './EvidenceTab.module.css';

interface FileRow {
  key: string;
  label: string;
  ref: SourceRef;
}

/** Source files behind the loaded run(s), with in-browser byte verification. */
export function EvidenceTab({
  controller,
  stream,
  comparing,
}: {
  controller: ReplayController;
  stream: Stream;
  comparing: boolean;
}) {
  const a = controller.run('a');
  const b = controller.run('b');

  const files = useMemo<FileRow[]>(() => {
    const out: FileRow[] = [];
    const seen = new Set<string>();
    const push = (key: string, label: string, ref?: SourceRef) => {
      if (!ref || seen.has(ref.path)) return;
      seen.add(ref.path);
      out.push({ key, label, ref });
    };
    if (a) {
      push('aRecord', `${runLabel(a.policy)}：运行记录 JSON`, a.source.record);
      push('aTraj', `${runLabel(a.policy)}：轨迹 NPZ`, a.source.trajectory);
    }
    if (comparing && b) {
      push('bRecord', `${runLabel(b.policy)}：运行记录 JSON`, b.source.record);
      push('bTraj', `${runLabel(b.policy)}：轨迹 NPZ`, b.source.trajectory);
    }
    if (a) {
      push('input', '输入流 JSON', a.source.input);
      push('model', '冻结模型 MODEL.json', a.source.model);
      push('protocol', '协议 PROTOCOL.json', a.source.protocol);
      push('freeze', '模型冻结 MODEL_FREEZE.json', a.source.freeze);
    }
    return out;
  }, [a, b, comparing]);

  // A controller survives policy changes. Key the verification state by the
  // actual sources so a previous PASS can never be rendered for new files.
  const identity = JSON.stringify([stream.instance_id, files.map(f => [f.key, f.ref.path, f.ref.url, f.ref.sha256, f.ref.bytes])]);
  return <EvidenceFiles key={identity} files={files} instance={stream.instance_id} />;
}

function EvidenceFiles({ files, instance }: { files: FileRow[]; instance: string }) {
  const [results, setResults] = useState<Record<string, CheckStatus>>({});
  const [busy, setBusy] = useState(false);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);

  const verifyAll = async () => {
    active.current?.abort();
    const task = new AbortController();
    active.current = task;
    setBusy(true);
    const next: Record<string, CheckStatus> = {};
    for (const f of files) next[f.key] = 'pending';
    setResults({ ...next });
    for (const f of files) {
      try {
        const bytes = await loadBytes(f.ref.url, task.signal);
        const hash = await sha256Hex(bytes);
        if (task.signal.aborted) return;
        next[f.key] = hash.toLowerCase() === f.ref.sha256.toLowerCase() && bytes.length === f.ref.bytes ? 'pass' : 'fail';
      } catch {
        if (task.signal.aborted) return;
        next[f.key] = 'fail';
      }
      setResults({ ...next });
    }
    setBusy(false);
  };

  return (
    <div className={s.wrap}>
      <p className={s.lead}>
        这条流用到的原始文件。每个文件给出原包内相对路径、字节数与 SHA-256；可在本浏览器重新下载并逐字节核对哈希（{hashEngineName()}）。
      </p>
      <button type="button" className={s.verifyBtn} onClick={verifyAll} disabled={busy}>
        <ShieldCheck size={15} aria-hidden /> {busy ? '正在核对…' : '在本浏览器核对全部哈希'}
      </button>

      <ul className={s.list}>
        {files.map((f) => (
          <li key={f.key} className={s.item}>
            <div className={s.itemTop}>
              <span className={s.itemLabel}>{f.label}</span>
              {results[f.key] && <StatusMark status={results[f.key]} />}
            </div>
            <code className={`mono ${s.path}`}>{f.ref.path}</code>
            <div className={s.itemMeta}>
              <span className="mono" title={f.ref.sha256}>
                {shortHash(f.ref.sha256, 16)}
              </span>
              <span className="num">{fmtBytes(f.ref.bytes)}</span>
              <a className={s.open} href={`#/evidence?file=${encodeURIComponent(f.ref.path)}`}>
                查看 <ExternalLink size={11} aria-hidden />
              </a>
            </div>
          </li>
        ))}
      </ul>

      <p className={s.foot}>
        选择器的特征、邻居、预测与选择的逐项复算核对，见“第 500 项决策”页的“在本浏览器复算核对”。该流其余结果数值的出处见“事后对照”页的证据标记。
      </p>
      <span className="visually-hidden">{instance}</span>
    </div>
  );
}

function runLabel(policy: string): string {
  const map: Record<string, string> = {
    BF: '全程 BF',
    BF_then_EoH: 'BF→EoH',
    published_EoH: '全程 EoH',
    SELECTOR: '选择器',
  };
  return map[policy] ?? policy;
}
