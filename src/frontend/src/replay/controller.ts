import { ReplayComparison, ReplayEngine } from '@core/replay.mjs';
import { loadRun } from '../data/api';
import type { Policy, RunRecord, Stream } from '../data/types';

/**
 * Playback controller around Codex's deterministic kernel (core/replay.mjs).
 * The kernel owns replay semantics and validates every applied step against
 * the record; this class only decides WHICH integer t is shown and when.
 */
export type Side = 'a' | 'b';

export interface ReplaySnapshot {
  status: 'idle' | 'loading' | 'ready' | 'error';
  error: Error | null;
  key: string;
  t: number;
  playing: boolean;
  speed: number;
  total: number;
  boundary: number;
  /** Bumps whenever anything visible may have changed. */
  version: number;
  /** Set when playback stopped by itself at the decision point. */
  pausedAtBoundary: boolean;
}

export const SPEEDS = [1, 5, 25, 100, 500] as const;

interface BinView {
  bin: number;
  count: number;
  remaining: number;
  load: number;
  used: boolean;
  active: boolean;
  items?: { index: number; itemNumber: number; size: number }[];
}

export interface StepView {
  index: number;
  itemNumber: number;
  size: number;
  bin: number;
  before: number;
  after: number;
  feasibleSlots: number;
  usedBinsAfter: number;
  openedBin: boolean;
}

export interface SideState {
  processed: number;
  usedBins: number;
  totalVolume: number;
  unusedCapacity: number;
  fillRatio: number | null;
  current: StepView | null;
  activeBin: number | null;
  selectedBranch: string | null;
  phase: 'prefix' | 'decision' | 'continuation';
  finished: boolean;
  slotCount: number;
  capacity: number;
}

type Engine = InstanceType<typeof ReplayEngine>;
type Comparison = InstanceType<typeof ReplayComparison>;

export class ReplayController {
  private listeners = new Set<() => void>();
  private snap: ReplaySnapshot = {
    status: 'idle',
    error: null,
    key: '',
    t: 0,
    playing: false,
    speed: 25,
    total: 5000,
    boundary: 500,
    version: 0,
    pausedAtBoundary: false,
  };

  private single: Engine | null = null;
  private pair: Comparison | null = null;
  runA: RunRecord | null = null;
  runB: RunRecord | null = null;
  policyA: Policy | null = null;
  policyB: Policy | null = null;
  stream: Stream | null = null;
  /** Full recorded curves (validated by the kernel at load). Gate before drawing. */
  curveA: Int32Array | null = null;
  curveB: Int32Array | null = null;

  private revision = 0;
  private abort: AbortController | null = null;
  private timer: ReturnType<typeof setInterval> | 0 = 0;
  private lastTs = 0;
  private acc = 0;
  private loadsCache = new Map<string, Float32Array>();
  pauseAtBoundary = true;

  subscribe = (listener: () => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getSnapshot = () => this.snap;

  private set(patch: Partial<ReplaySnapshot>) {
    this.snap = { ...this.snap, ...patch, version: this.snap.version + 1 };
    for (const l of this.listeners) l();
  }

  get ready() {
    return this.snap.status === 'ready';
  }

  get comparing() {
    return this.pair !== null;
  }

  async load(stream: Stream, a: Policy, b: Policy | null, t: number): Promise<void> {
    const key = `${stream.instance_id}|${a}|${b ?? ''}`;
    if (key === this.snap.key && (this.snap.status === 'ready' || this.snap.status === 'loading')) {
      if (this.snap.status === 'ready' && t !== this.snap.t) this.seek(t);
      return;
    }
    this.pause();
    const rev = ++this.revision;
    this.abort?.abort();
    const controller = new AbortController();
    this.abort = controller;
    this.loadsCache.clear();
    this.set({ status: 'loading', error: null, key, playing: false, pausedAtBoundary: false });
    try {
      const descA = stream.runs.find((r) => r.policy === a);
      const descB = b ? stream.runs.find((r) => r.policy === b) : null;
      if (!descA) throw new Error(`该输入流没有 ${a} 运行记录`);
      if (b && !descB) throw new Error(`该输入流没有 ${b} 运行记录`);
      const [runA, runB] = await Promise.all([
        loadRun(descA.data_url, descA.sha256, controller.signal),
        descB ? loadRun(descB.data_url, descB.sha256, controller.signal) : Promise.resolve(null),
      ]);
      if (rev !== this.revision) return;
      let single: Engine | null = null;
      let pair: Comparison | null = null;
      if (runB) {
        pair = new ReplayComparison(runA, runB);
        // Validate both complete trajectories once (pre/post residuals, counts,
        // final residuals, volume conservation) before anything is drawn.
        pair.seek(runA.items.length);
      } else {
        single = new ReplayEngine(runA);
        single.seek(runA.items.length);
      }
      const total = runA.items.length;
      const boundary = runA.selector_consumed_count ?? 500;
      const target = Math.max(0, Math.min(total, Math.round(t)));
      (pair ?? single)!.seek(target);
      if (rev !== this.revision) return;
      this.single = single;
      this.pair = pair;
      this.runA = runA;
      this.runB = runB;
      this.policyA = a;
      this.policyB = b;
      this.stream = stream;
      this.curveA = Int32Array.from(runA.used_bins_after);
      this.curveB = runB ? Int32Array.from(runB.used_bins_after) : null;
      this.set({ status: 'ready', error: null, t: target, total, boundary, pausedAtBoundary: false });
    } catch (error) {
      if (rev !== this.revision || (error as Error)?.name === 'AbortError') return;
      this.single = null;
      this.pair = null;
      this.set({ status: 'error', error: error as Error, playing: false });
    }
  }

  /**
   * Abort in-flight work and return to idle so the instance can be reused. This
   * runs on React StrictMode's simulated unmount too, so it must leave the
   * controller loadable again rather than permanently torn down.
   */
  dispose() {
    this.pause();
    this.revision += 1;
    this.abort?.abort();
    this.abort = null;
    this.single = null;
    this.pair = null;
    this.snap = { ...this.snap, status: 'idle', key: '', error: null, playing: false };
    for (const l of this.listeners) l();
  }

  seek(t: number) {
    const engine = this.pair ?? this.single;
    if (!engine) return;
    const target = Math.max(0, Math.min(this.snap.total, Math.round(t)));
    if (target === this.snap.t && this.snap.status === 'ready') return;
    try {
      engine.seek(target);
      this.loadsCache.clear();
      this.set({ t: target, pausedAtBoundary: false });
    } catch (error) {
      this.pause();
      this.set({ status: 'error', error: error as Error });
    }
  }

  step(delta: number) {
    this.pause();
    this.seek(this.snap.t + delta);
  }

  reset() {
    this.pause();
    this.seek(0);
  }

  setSpeed(speed: number) {
    this.set({ speed });
  }

  play() {
    if (!this.ready || this.snap.playing) return;
    if (this.snap.t >= this.snap.total) this.seek(0);
    this.lastTs = performance.now();
    this.acc = 0;
    this.set({ playing: true, pausedAtBoundary: false });
    // A timer (not requestAnimationFrame) so playback keeps advancing even when
    // the tab is backgrounded — rAF is fully suspended while hidden. dt comes
    // from performance.now(), so the wall-clock speed stays correct either way.
    this.timer = setInterval(this.tick, 1000 / 60);
  }

  pause() {
    if (this.timer) clearInterval(this.timer);
    this.timer = 0;
    if (this.snap.playing) this.set({ playing: false });
  }

  toggle() {
    if (this.snap.playing) this.pause();
    else this.play();
  }

  private tick = () => {
    if (!this.snap.playing) return;
    const now = performance.now();
    const dt = Math.min(0.25, (now - this.lastTs) / 1000);
    this.lastTs = now;
    this.acc += dt * this.snap.speed;
    const advance = Math.floor(this.acc);
    if (advance > 0) {
      this.acc -= advance;
      const from = this.snap.t;
      let to = Math.min(this.snap.total, from + advance);
      const b = this.snap.boundary;
      const stopAtBoundary = this.pauseAtBoundary && from < b && to >= b;
      if (stopAtBoundary) to = b;
      this.seek(to);
      if (stopAtBoundary) {
        this.pause();
        this.set({ pausedAtBoundary: true });
        return;
      }
      if (to >= this.snap.total) {
        this.pause();
      }
    }
  };

  // ---- read helpers (all gated by the kernel's knowledge rules) ----

  private sideName(side: Side): 'left' | 'right' {
    return side === 'a' ? 'left' : 'right';
  }

  has(side: Side): boolean {
    return side === 'a' ? Boolean(this.pair ?? this.single) : Boolean(this.pair);
  }

  state(side: Side, retrospective = false): SideState | null {
    if (this.pair) {
      const s = this.pair.getState({ retrospective });
      return (side === 'a' ? s.left : s.right) as unknown as SideState;
    }
    if (side === 'b' || !this.single) return null;
    return this.single.getState({ retrospective }) as unknown as SideState;
  }

  bin(side: Side, bin: number): BinView | null {
    if (this.pair) return this.pair.getBin(this.sideName(side), bin, { includeItems: true }) as unknown as BinView;
    if (side === 'a' && this.single) return this.single.getBin(bin, { includeItems: true }) as unknown as BinView;
    return null;
  }

  /** Loads (0..capacity) of all slots at the current t; cached per t. */
  loads(side: Side): Float32Array | null {
    if (!this.has(side)) return null;
    const cacheKey = `${side}:${this.snap.t}`;
    const hit = this.loadsCache.get(cacheKey);
    if (hit) return hit;
    const st = this.state(side);
    if (!st) return null;
    const out = new Float32Array(st.slotCount);
    const options = { offset: 0, limit: st.slotCount, usedOnly: true, includeItems: false };
    const { bins } = (this.pair
      ? this.pair.getBins(this.sideName(side), options)
      : this.single!.getBins(options)) as unknown as { bins: BinView[] };
    for (const b of bins) out[b.bin] = b.load;
    this.loadsCache.set(cacheKey, out);
    return out;
  }

  items(start: number, limit: number, retrospective = false): StepView[] {
    const engine = this.pair ?? this.single;
    if (!engine) return [];
    return engine.getItems({ start, limit, retrospective }) as unknown as StepView[];
  }

  decision(side: Side, retrospective = false) {
    if (this.pair) return this.pair.getDecision(this.sideName(side), { retrospective });
    if (side === 'a' && this.single) return this.single.getDecision({ retrospective });
    return null;
  }

  run(side: Side): RunRecord | null {
    return side === 'a' ? this.runA : this.runB;
  }

  policy(side: Side): Policy | null {
    return side === 'a' ? this.policyA : this.policyB;
  }

  curve(side: Side): Int32Array | null {
    return side === 'a' ? this.curveA : this.curveB;
  }
}
