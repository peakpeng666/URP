import { useEffect, useState } from 'react';
import { ArrowLeft, Download, FileText, ShieldCheck } from 'lucide-react';
import type { Route } from '../app/router';
import { buildHash } from '../app/router';
import { loadBytes, loadJSON, loadMeta, useAsync } from '../data/api';
import type { Meta } from '../data/types';
import { sha256Hex, hashEngineName } from '../lib/sha256';
import { fmt, fmtBytes, shortHash } from '../lib/format';
import { Async, EmptyState, Panel, Spinner } from '../components/ui';
import { StatusMark, StatusTag } from '../components/Status';
import s from './EvidenceView.module.css';

interface Manifest {
  files: Record<string, { bytes: number; sha256: string }>;
  scientific_freeze_sha256?: string;
}

export function EvidenceView({ route }: { route: Route }) {
  const meta = useAsync('meta', () => loadMeta());
  const file = route.params.get('file');
  return (
    <div className={s.page}>
      <Async state={meta}>{(m) => (file ? <FilePreview key={`${file}:${m.sources['MANIFEST.json']?.sha256}`} meta={m} path={file} /> : <EvidenceHome meta={m} />)}</Async>
    </div>
  );
}

function EvidenceHome({ meta }: { meta: Meta }) {
  const iv = meta.import_validation;
  const pv = meta.project_validation;
  const ha = meta.historical_audit;

  return (
    <>
      <header className={s.header}>
        <h1 className={s.title}>证据与核验</h1>
        <p className={s.sub}>
          数值来自包内历史实验记录。下方列出打包时的独立审计、本机复算和待验证项。可下载关键文件并在浏览器中核对哈希（{hashEngineName()}）。
        </p>
      </header>

      <Panel title="交付包完整性" subtitle="导入时校验 ZIP 哈希、路径安全与完整 MANIFEST。原始 ZIP 保持不变。">
        <div className={s.integrity}>
          <IntegrityItem label="原始 ZIP SHA-256" value={shortHash(iv.archive_sha256, 20)} mono full={iv.archive_sha256} />
          <IntegrityItem label="字节数" value={fmt(iv.archive_bytes, 0)} />
          <IntegrityItem label="ZIP 成员" value={fmt(iv.zip_members, 0)} />
          <IntegrityItem label="MANIFEST 条目" value={fmt(iv.manifest_entries, 0)} />
          <IntegrityItem label="状态" value={iv.status} status={iv.status === 'PASS' ? 'pass' : 'fail'} />
        </div>
        <p className={s.note}>{iv.count_note}。{iv.scope}。</p>
      </Panel>

      <div className={s.scopes}>
        <ScopeCard
          title="包内历史审计"
          status="pass"
          badge="PASS"
          lines={[
            `科学数据与预定分析：${String(ha.scientific_result_status)}`,
            '独立重放 384 万步、120 选择、18 单元与 10000 bootstrap 一致',
            '打包时完成，审计对象为实验数据与分析',
          ]}
        />
        <ScopeCard
          title="本项目核验"
          status={pv.status === 'PASS' ? 'pass' : pv.status === 'FAIL' ? 'fail' : 'pending'}
          badge={pv.status}
          lines={[
            pv.generatedAt ? `生成于 ${pv.generatedAt.slice(0, 19).replace('T', ' ')} UTC` : '进行中',
            pv.environment ? `环境 Python ${pv.environment.python} / NumPy ${pv.environment.numpy}` : '',
            ...(pv.checks ?? []).map((c) => `${c.name}：${c.status}`),
          ].filter(Boolean)}
        />
        <ScopeCard
          title="未覆盖范围"
          status="none"
          badge="需另行验证"
          lines={[
            `历史整体 900 CPU 秒预算：${String(ha.historical_total_900_cpu_compliance)}`,
            '跨平台浮点位级一致性：待验证',
            '原生 Ubuntu 与真实手机：未实机验证',
          ]}
        />
      </div>

      <Panel title="关键来源文件" subtitle="点击查看文件内容并在本浏览器核对哈希。完整 1914 个文件的清单见 MANIFEST.json。">
        <ul className={s.fileList}>
          {Object.entries(meta.sources).map(([key, ref]) => (
            <li key={key}>
              <a className={s.fileRow} href={buildHash('evidence', null, { file: ref.path })}>
                <FileText size={15} aria-hidden className={s.fileIcon} />
                <span className={`mono ${s.filePath}`}>{ref.path}</span>
                <span className={`num ${s.fileBytes}`}>{fmtBytes(ref.bytes)}</span>
              </a>
            </li>
          ))}
        </ul>
      </Panel>
    </>
  );
}

const TEXT_EXT = ['.json', '.md', '.csv', '.txt', '.py', '.log', '.source'];
const IMAGE_EXT = ['.png', '.jpg', '.jpeg'];

function FilePreview({ meta, path }: { meta: Meta; path: string }) {
  const ext = path.slice(path.lastIndexOf('.')).toLowerCase();
  const isText = TEXT_EXT.includes(ext);
  const isImage = IMAGE_EXT.includes(ext);
  const url = `/data/evidence/${path.split('/').map(encodeURIComponent).join('/')}`;

  const manifestRef = meta.sources['MANIFEST.json'];
  const verify = useAsync(`verify:${path}:${manifestRef?.sha256}`, async (signal) => {
    if (!manifestRef?.sha256) throw new Error('缺少可信 MANIFEST.json 哈希，已停止核验。');
    // The manifest excludes itself. Its anchor is supplied by trusted meta.json;
    // every other source is resolved only after checking that manifest anchor.
    const expected = path === 'MANIFEST.json'
      ? manifestRef
      : (await loadJSON<Manifest>(manifestRef.url, manifestRef.sha256)).files[path];
    if (!expected || !/^[a-f0-9]{64}$/i.test(expected.sha256) || !Number.isSafeInteger(expected.bytes)) {
      throw new Error('可信清单未收录此文件或其记录无效，已停止作为可信数据。');
    }
    const bytes = await loadBytes(url, signal);
    const hash = await sha256Hex(bytes);
    const match = hash.toLowerCase() === expected.sha256.toLowerCase() && bytes.length === expected.bytes;
    return { hash, bytes, expectedHash: expected.sha256, match,
      text: isText ? new TextDecoder('utf-8').decode(bytes) : null };
  });

  const [verifiedBlob, setVerifiedBlob] = useState<{ bytes: Uint8Array; url: string } | null>(null);
  const verified = verify.status === 'ready' && verify.data.match ? verify.data : null;
  useEffect(() => {
    if (!verified) { setVerifiedBlob(null); return; }
    const mime = ext === '.png' ? 'image/png' : IMAGE_EXT.includes(ext) ? 'image/jpeg' : 'application/octet-stream';
    const objectUrl = URL.createObjectURL(new Blob([new Uint8Array(verified.bytes)], { type: mime }));
    setVerifiedBlob({ bytes: verified.bytes, url: objectUrl });
    return () => URL.revokeObjectURL(objectUrl);
  }, [verified, ext]);
  // Download and image preview use the exact verified buffer, never a second
  // network request whose response could differ from the displayed hash.
  const downloadUrl = verifiedBlob?.bytes === verified?.bytes ? verifiedBlob?.url : undefined;

  return (
    <>
      <header className={s.previewHead}>
        <a className={s.back} href={buildHash('evidence')}>
          <ArrowLeft size={15} aria-hidden /> 证据
        </a>
        <code className={`mono ${s.previewPath}`}>{path}</code>
        {downloadUrl && <a className={s.download} href={downloadUrl} download={path.split('/').at(-1)}>
          <Download size={14} aria-hidden /> 下载原始字节
        </a>}
      </header>

      <Panel title="字节核对" subtitle="先按元数据中的哈希核对 MANIFEST.json，再核对文件。预览、下载与哈希计算共用同一份字节。">
        <div className={s.verifyRow}>
          <Async state={verify} loading={<Spinner label="下载并计算哈希…" />}>
            {(v) => (
              <>
                <div className={s.hashBlock}>
                  <span className={s.hashLabel}>本浏览器计算</span>
                  <code className={`mono ${s.hashVal}`}>{v.hash}</code>
                </div>
                <div className={s.hashBlock}>
                  <span className={s.hashLabel}>{path === 'MANIFEST.json' ? '可信元数据记录' : '已核对清单记录'}</span>
                  <code className={`mono ${s.hashVal}`}>{v.expectedHash}</code>
                </div>
                <StatusTag status={v.match ? 'pass' : 'fail'}>
                  {v.match ? '逐字节一致' : '不一致，文件未通过核验'}
                </StatusTag>
                <span className={`num ${s.sizeNote}`}>{fmtBytes(v.bytes.length)}</span>
              </>
            )}
          </Async>
        </div>
      </Panel>

      <Panel title="内容">
        <Async state={verify} loading={<Spinner />}>
          {(v) => isImage ? (
            downloadUrl ? <img className={s.image} src={downloadUrl} alt={path} /> :
              <EmptyState title={v.match ? '正在准备预览…' : '文件未通过核验，已停止图像预览'} />
          ) : isText ? (
            <>
              {!v.match && <p className={s.note}>以下原始文本未通过核验，供排查使用。</p>}
              <pre className={s.textContent}>
                {(v.text?.length ?? 0) > 40000 ? `${v.text!.slice(0, 40000)}\n…（已截断；核验通过后可下载完整原始字节）` : v.text}
              </pre>
            </>
          ) : (
            <EmptyState title="二进制文件"
              detail={v.match ? `${ext} 文件（如 NPZ/PDF/DOCX）不在页面内渲染；可下载上方已核对的原始字节。NPZ 轨迹数组的逐步校验由回放内核在加载时完成。` : '文件未通过核验，已停止作为可信数据。'} />
          )}
        </Async>
      </Panel>
    </>
  );
}

function IntegrityItem({ label, value, mono, full, status }: { label: string; value: string; mono?: boolean; full?: string; status?: 'pass' | 'fail' }) {
  return (
    <div className={s.intItem}>
      <span className={s.intLabel}>{label}</span>
      <span className={`${s.intValue} ${mono ? 'mono' : 'num'}`} title={full}>
        {status && <StatusMark status={status} />} {value}
      </span>
    </div>
  );
}

function ScopeCard({ title, status, badge, lines }: { title: string; status: 'pass' | 'pending' | 'fail' | 'none'; badge: string; lines: string[] }) {
  return (
    <section className={s.scopeCard} data-status={status}>
      <header className={s.scopeHead}>
        <ShieldCheck size={16} aria-hidden />
        <h2 className={s.scopeTitle}>{title}</h2>
        <StatusTag status={status}>{badge}</StatusTag>
      </header>
      <ul className={s.scopeLines}>
        {lines.map((l, i) => (
          <li key={i}>{l}</li>
        ))}
      </ul>
    </section>
  );
}
