import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent } from 'react';
import { ArrowDownToLine, Check, Copy, ScrollText } from 'lucide-react';
import { lab } from '../api';
import { Button, Notice, Select } from '../ui';
import { FOCUSABLE, LOG_REFRESH_MS, LOG_TAIL, formatBytes, isNearBottom, mergeLogNames, wrapFocus } from './LogSheet.logic';
import s from './LogSheet.module.css';

interface Tail {
  log: string;
  path: string;
  text: string;
  count: number;
}

/** macOS-style sheet that tails one gateway log (GET /lab/api/logs/{name}) once per second. */
export function LogSheet({ open, initialLog, onClose }: { open: boolean; initialLog?: string | null; onClose: () => void }) {
  if (!open) return null;
  return <LogSheetBody initialLog={initialLog ?? null} onClose={onClose} />;
}

function LogSheetBody({ initialLog, onClose }: { initialLog: string | null; onClose: () => void }) {
  const [logs, setLogs] = useState<{ log: string; path: string; bytes: number }[] | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [name, setName] = useState<string | null>(initialLog);
  const [tail, setTail] = useState<Tail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [follow, setFollow] = useState(true);
  const [copied, setCopied] = useState(false);
  const sheetRef = useRef<HTMLDivElement>(null);
  const preRef = useRef<HTMLPreElement>(null);
  const followRef = useRef(true);
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  // Focus in on open, trap it while open, give it back on close.
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    sheetRef.current?.querySelector<HTMLElement>('[data-autofocus]')?.focus();
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        closeRef.current();
      }
    };
    const onFocusIn = (e: FocusEvent) => {
      const sheet = sheetRef.current;
      if (sheet && !sheet.contains(e.target as Node)) sheet.querySelector<HTMLElement>(FOCUSABLE)?.focus();
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('focusin', onFocusIn);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('focusin', onFocusIn);
      document.body.style.overflow = overflow;
      previous?.focus?.();
    };
  }, []);

  useEffect(() => {
    let alive = true;
    lab
      .logs()
      .then((r) => {
        if (!alive) return;
        setLogs(r.logs);
        setName((n) => n ?? r.logs[0]?.log ?? null);
      })
      .catch((e: Error) => alive && setListError(e.message));
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!name) return undefined;
    let alive = true;
    let inflight = false;
    setTail(null);
    setError(null);
    followRef.current = true;
    setFollow(true);
    const tick = async () => {
      if (inflight) return;
      inflight = true;
      try {
        const r = await lab.log(name, LOG_TAIL);
        if (!alive) return;
        const text = r.lines.join('\n');
        setTail((prev) =>
          prev && prev.text === text && prev.path === r.path ? prev : { log: r.log, path: r.path, text, count: r.lines.length },
        );
        setError(null);
      } catch (e) {
        if (alive) setError((e as Error).message);
      } finally {
        inflight = false;
      }
    };
    void tick();
    const id = window.setInterval(tick, LOG_REFRESH_MS);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, [name]);

  useLayoutEffect(() => {
    const pre = preRef.current;
    if (pre && followRef.current) pre.scrollTop = pre.scrollHeight;
  }, [tail?.text]);

  const onScroll = () => {
    const pre = preRef.current;
    if (!pre) return;
    const near = isNearBottom(pre.scrollTop, pre.clientHeight, pre.scrollHeight);
    followRef.current = near;
    setFollow(near);
  };

  const jumpToEnd = () => {
    const pre = preRef.current;
    if (!pre) return;
    followRef.current = true;
    setFollow(true);
    pre.scrollTop = pre.scrollHeight;
  };

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== 'Tab' || !sheetRef.current) return;
    const items = [...sheetRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
    const i = items.indexOf(document.activeElement as HTMLElement);
    const atEdge = i === -1 || (e.shiftKey ? i === 0 : i === items.length - 1);
    if (!atEdge) return;
    e.preventDefault();
    items[wrapFocus(i, items.length, e.shiftKey)]?.focus();
  };

  const copy = async () => {
    const text = tail?.text ?? '';
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const area = document.createElement('textarea');
      area.value = text;
      area.style.position = 'fixed';
      area.style.opacity = '0';
      sheetRef.current?.appendChild(area);
      area.select();
      document.execCommand('copy');
      area.remove();
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  const names = mergeLogNames(logs, name);
  const meta = logs?.find((l) => l.log === name);

  return (
    <div
      className={s.scrim}
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div ref={sheetRef} className={s.sheet} role="dialog" aria-modal="true" aria-labelledby="log-sheet-title" onKeyDown={onKeyDown}>
        <header className={s.head}>
          <ScrollText size={18} strokeWidth={1.8} className={s.headIcon} aria-hidden />
          <div className={s.titleBlock}>
            <h2 id="log-sheet-title" className={s.title}>
              日志
            </h2>
            <p className={`${s.path} mono`} title={tail?.path ?? meta?.path}>
              {tail?.path ?? meta?.path ?? '—'}
            </p>
          </div>
          <Select
            aria-label="选择日志"
            value={name ?? ''}
            onChange={(e) => setName(e.target.value || null)}
            disabled={names.length === 0}
            className={s.picker}
          >
            {names.length === 0 && <option value="">{logs ? '没有可用日志' : '读取列表…'}</option>}
            {names.map((n) => {
              const l = logs?.find((x) => x.log === n);
              return (
                <option key={n} value={n}>
                  {n}
                  {l ? ` · ${formatBytes(l.bytes)}` : ''}
                </option>
              );
            })}
          </Select>
          <Button size="sm" icon={copied ? Check : Copy} onClick={copy} disabled={!tail}>
            {copied ? '已复制' : '复制'}
          </Button>
          <Button size="sm" variant="primary" onClick={onClose} data-autofocus>
            完成
          </Button>
        </header>

        {(listError || error) && (
          <div className={s.notices}>
            {listError && <Notice tone="error">无法读取日志列表：{listError}</Notice>}
            {error && <Notice tone="error">无法读取日志 {name}：{error}</Notice>}
          </div>
        )}

        <pre
          ref={preRef}
          className={s.pre}
          onScroll={onScroll}
          tabIndex={0}
          aria-label={name ? `日志 ${name} 末尾 ${LOG_TAIL} 行` : '日志'}
          aria-live="off"
        >
          {!name ? '没有选择日志。' : tail ? tail.text || '（日志为空）' : error ? '' : '正在读取…'}
        </pre>

        <footer className={s.foot}>
          <span>
            末尾 {LOG_TAIL} 行 · 每秒刷新{tail ? ` · 当前 ${tail.count} 行` : ''}
          </span>
          {follow ? (
            <span className={s.follow}>自动滚动到最新</span>
          ) : (
            <Button size="sm" variant="plain" icon={ArrowDownToLine} onClick={jumpToEnd}>
              已暂停自动滚动 · 跳到末尾
            </Button>
          )}
        </footer>
      </div>
    </div>
  );
}
