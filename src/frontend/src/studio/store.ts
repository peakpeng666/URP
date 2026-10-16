import { create } from 'zustand';
import { navigate } from '../app/router';
import { events, lab, LabApiError } from '../lab/api';
import type { Algorithm, Instance, Recommendation, Scenario, Solution } from '../lab/types';
import { studio } from './api';
import type { FleetInstance, ParseResult, Selection, Tool, ObstacleKind } from './types';

export type Workspace = 'plan' | 'experiments' | 'sim' | 'library' | 'system';

type SaveState = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';

interface StudioState {
  workspace: Workspace;
  scenarioId: string | null;
  scenario: Scenario | null;
  loadError: string | null;
  draft: Instance | null;
  past: Instance[];
  future: Instance[];
  save: SaveState;
  saveError: string | null;
  tool: Tool;
  obstacleKind: ObstacleKind;
  selection: Selection;
  algorithms: Algorithm[];
  recommendation: Recommendation | null;
  recommending: boolean;
  chosen: string[];
  budget: number;
  runIds: string[];
  runs: Record<string, Solution>;
  focusRun: string | null;
  manualFocus: boolean;
  hiddenVehicles: string[];
  playback: number | null;
  composeText: string;
  parse: ParseResult | null;
  busy: string | null;
  toast: { tone: 'ok' | 'error' | 'info'; text: string } | null;
  cursor: [number, number] | null;
  paletteOpen: boolean;
  codePath: string | null;
  studyId: string | null;

  setWorkspace: (w: Workspace) => void;
  open: (id: string) => Promise<void>;
  edit: (fn: (inst: Instance) => Instance) => void;
  undo: () => void;
  redo: () => void;
  setTool: (t: Tool) => void;
  setObstacleKind: (k: ObstacleKind) => void;
  select: (s: Selection) => void;
  setChosen: (ids: string[]) => void;
  setBudget: (s: number) => void;
  refreshRecommendation: () => Promise<void>;
  solve: (ids?: string[]) => Promise<void>;
  focus: (runId: string | null) => void;
  toggleVehicle: (name: string) => void;
  setPlayback: (t: number | null) => void;
  setComposeText: (t: string) => void;
  composeFromText: (opts?: { field_id?: string }) => Promise<void>;
  notify: (tone: 'ok' | 'error' | 'info', text: string) => void;
  setCursor: (p: [number, number] | null) => void;
  setPalette: (open: boolean) => void;
  openCode: (path: string | null) => void;
  setStudy: (id: string | null) => void;
  loadAlgorithms: () => Promise<void>;
}

const HISTORY = 120;
let saveTimer: number | undefined;
let recommendTimer: number | undefined;

const message = (e: unknown) => (e instanceof LabApiError || e instanceof Error ? e.message : String(e));

export const useStudio = create<StudioState>((set, get) => ({
  workspace: 'plan',
  scenarioId: null,
  scenario: null,
  loadError: null,
  draft: null,
  past: [],
  future: [],
  save: 'idle',
  saveError: null,
  tool: 'select',
  obstacleKind: 'pond',
  selection: null,
  algorithms: [],
  recommendation: null,
  recommending: false,
  chosen: [],
  budget: 3,
  runIds: [],
  runs: {},
  focusRun: null,
  manualFocus: false,
  hiddenVehicles: [],
  playback: null,
  composeText: '',
  parse: null,
  busy: null,
  toast: null,
  cursor: null,
  paletteOpen: false,
  codePath: null,
  studyId: null,

  setWorkspace: (workspace) => set({ workspace }),

  async open(id) {
    if (get().scenarioId === id && get().scenario) return;
    set({ scenarioId: id, loadError: null, busy: '载入场景', selection: null, past: [], future: [], save: 'idle', chosen: [],
          runIds: [], runs: {}, focusRun: null, manualFocus: false, recommendation: null, playback: null, hiddenVehicles: [] });
    try {
      const sc = await lab.scenario(id);
      if (get().scenarioId !== id) return;
      set({ scenario: sc, draft: sc.instance, busy: null });
      void get().refreshRecommendation();
      const recent = await lab.runs({ scenario_id: id, limit: 30 });
      const runs = Object.fromEntries(recent.runs.map((r) => [r.run_id, r]));
      const latestJob = recent.runs[0]?.job_id;
      const ids = recent.runs.filter((r) => r.job_id === latestJob).map((r) => r.run_id);
      set({ runs, runIds: ids, focusRun: pickBest(ids.map((i) => runs[i])) });
    } catch (e) {
      set({ loadError: message(e), busy: null });
    }
  },

  edit(fn) {
    const { draft, past } = get();
    if (!draft) return;
    const next = fn(draft);
    if (next === draft) return;
    set({ draft: next, past: [...past.slice(-HISTORY), draft], future: [], save: 'dirty' });
    scheduleSave();
    scheduleRecommend();
  },

  undo() {
    const { past, draft, future } = get();
    if (!past.length || !draft) return;
    set({ draft: past[past.length - 1], past: past.slice(0, -1), future: [draft, ...future], save: 'dirty' });
    scheduleSave();
    scheduleRecommend();
  },

  redo() {
    const { past, draft, future } = get();
    if (!future.length || !draft) return;
    set({ draft: future[0], future: future.slice(1), past: [...past, draft], save: 'dirty' });
    scheduleSave();
    scheduleRecommend();
  },

  setTool: (tool) => set({ tool }),
  setObstacleKind: (obstacleKind) => set({ obstacleKind, tool: 'obstacle' }),
  select: (selection) => set({ selection }),
  setChosen: (chosen) => set({ chosen }),
  setBudget: (budget) => set({ budget }),

  async refreshRecommendation() {
    const { scenario, draft } = get();
    if (!scenario || !draft) return;
    set({ recommending: true });
    try {
      const rec = await lab.recommend(scenario.id, draft);
      if (get().scenario?.id !== scenario.id) return;
      const compare = (rec as Recommendation & { compare?: string[] }).compare ?? (rec.recommended ? [rec.recommended] : []);
      set((s) => {
        const kept = s.chosen.filter((id) => rec.ranking.some((r) => r.algorithm_id === id && r.applicable));
        return { recommendation: rec, recommending: false, chosen: kept.length ? kept : compare };
      });
      const hint = rec.ranking.find((r) => r.algorithm_id === rec.recommended)?.suggested_params?.time_limit_s;
      if (typeof hint === 'number' && get().budget === 3) set({ budget: hint });
    } catch (e) {
      set({ recommending: false });
      get().notify('error', `推荐失败：${message(e)}`);
    }
  },

  async solve(ids) {
    const { scenario, draft, chosen, budget, algorithms } = get();
    const list = ids ?? chosen;
    if (!scenario || !draft || !list.length) return;
    await flushSave();
    const current = get().scenario ?? scenario;
    set({ busy: '求解中' });
    try {
      const specs = list.map((id) => {
        const a = algorithms.find((x) => x.id === id);
        const params: Record<string, unknown> = {};
        if (a?.params.some((p) => p.name === 'time_limit_s')) params.time_limit_s = budget;
        return { id, params };
      });
      const job = await lab.solve(current.id, specs, get().draft ?? draft, '工作台对比');
      set({ runIds: job.runs, focusRun: null, manualFocus: false, busy: null, playback: null });
      for (const id of job.runs) void pollRun(id);
    } catch (e) {
      set({ busy: null });
      get().notify('error', message(e));
    }
  },

  focus: (focusRun) => set({ focusRun, manualFocus: true, playback: null }),
  toggleVehicle: (name) => set((s) => ({ hiddenVehicles: s.hiddenVehicles.includes(name) ? s.hiddenVehicles.filter((v) => v !== name) : [...s.hiddenVehicles, name] })),
  setPlayback: (playback) => set({ playback }),
  setComposeText: (composeText) => set({ composeText }),

  async composeFromText(opts) {
    const text = get().composeText.trim();
    if (!text && !opts?.field_id) return;
    set({ busy: '生成地图' });
    try {
      const sc = await studio.compose(text, opts);
      set({ busy: null });
      location.hash = `#/plan/${encodeURIComponent(sc.id)}`;
      get().notify('ok', `已生成：${sc.summary}`);
    } catch (e) {
      set({ busy: null });
      get().notify('error', message(e));
    }
  },

  notify(tone, text) {
    set({ toast: { tone, text } });
    window.setTimeout(() => {
      if (get().toast?.text === text) set({ toast: null });
    }, tone === 'error' ? 6000 : 3200);
  },

  setCursor: (cursor) => set({ cursor }),
  setPalette: (paletteOpen) => set({ paletteOpen }),
  openCode: (codePath) => set({ codePath }),
  setStudy: (studyId) => set({ studyId }),

  async loadAlgorithms() {
    try {
      const { algorithms } = await lab.algorithms();
      set({ algorithms });
    } catch (e) {
      get().notify('error', `算法库读取失败：${message(e)}`);
    }
  },
}));

export function pickBest(runs: (Solution | undefined)[]): string | null {
  const done = runs.filter((r): r is Solution => !!r && r.state === 'done' && !!r.routes.length);
  done.sort((a, b) => Number(!a.check?.valid) - Number(!b.check?.valid) || (a.objective.value ?? Infinity) - (b.objective.value ?? Infinity));
  return done[0]?.run_id ?? null;
}

async function pollRun(id: string) {
  for (let i = 0; i < 2400; i++) {
    try {
      const r = await lab.run(id);
      useStudio.setState((s) => ({ runs: { ...s.runs, [id]: r } }));
      if (!['queued', 'running'].includes(r.state)) {
        const s = useStudio.getState();
        if (!s.manualFocus) useStudio.setState({ focusRun: pickBest(s.runIds.map((x) => s.runs[x])) });
        return;
      }
    } catch {
      /* transient: retry */
    }
    await new Promise((r) => setTimeout(r, i < 20 ? 300 : 1000));
  }
}

events.subscribe((type, data) => {
  if (type !== 'run') return;
  const r = data as Solution;
  const s = useStudio.getState();
  if (s.runIds.includes(r.run_id)) useStudio.setState({ runs: { ...s.runs, [r.run_id]: r } });
});

function scheduleSave() {
  window.clearTimeout(saveTimer);
  saveTimer = window.setTimeout(() => void flushSave(), 700);
}

function scheduleRecommend() {
  window.clearTimeout(recommendTimer);
  recommendTimer = window.setTimeout(() => void useStudio.getState().refreshRecommendation(), 900);
}

/** Persist the draft: user scenarios are updated in place; built-in/library ones are first copied to "我的场景". */
export async function flushSave() {
  window.clearTimeout(saveTimer);
  const { scenario, draft, save } = useStudio.getState();
  if (!scenario || !draft || save !== 'dirty') return;
  useStudio.setState({ save: 'saving', saveError: null });
  try {
    const origin = (scenario as Scenario & { origin?: string }).origin;
    let stored: Scenario;
    if (origin === 'user') {
      stored = (await studio.saveScenario(scenario.id, { instance: draft })) as unknown as Scenario;
    } else {
      stored = await studio.forkScenario(scenario.id, { instance: draft });
      useStudio.setState({ scenarioId: stored.id });
      navigate(`#/plan/${encodeURIComponent(stored.id)}`, { replace: true });
      useStudio.getState().notify('info', '已另存为“我的场景”，之后的修改会自动保存');
    }
    if (useStudio.getState().draft === draft) useStudio.setState({ save: 'saved', scenario: stored });
    else useStudio.setState({ scenario: stored });
  } catch (e) {
    useStudio.setState({ save: 'error', saveError: message(e) });
  }
}

export const isFleet = (sc: Scenario | null): boolean => sc?.problem_class === 'fleet_routing';
export const asFleet = (inst: Instance | null) => inst as unknown as FleetInstance;
