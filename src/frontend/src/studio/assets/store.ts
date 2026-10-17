import { create } from 'zustand';
import { assetsApi, type Asset, type AssetKind, type AssetSummary, type References } from './api';

interface AssetsState {
  list: AssetSummary[];
  loading: boolean;
  error: string | null;
  kind: AssetKind | 'all';
  q: string;
  archived: boolean;
  selected: string | null;
  asset: Asset | null;
  version: number | null;
  refs: References | null;
  importOpen: boolean;
  importSeed: File[] | null;
  taskMapFrom: { id: string; v: number } | null;
  refresh: () => Promise<void>;
  select: (id: string | null, v?: number) => Promise<void>;
  reload: () => Promise<void>;
  setVersion: (v: number) => void;
  setFilter: (patch: Partial<Pick<AssetsState, 'kind' | 'q' | 'archived'>>) => void;
  openImport: (files?: File[] | null) => void;
  closeImport: () => void;
  setTaskMapFrom: (x: { id: string; v: number } | null) => void;
  /** Replace the asset in the list and detail after an edit. */
  apply: (a: Asset) => void;
}

export const useAssets = create<AssetsState>((set, get) => ({
  list: [],
  loading: false,
  error: null,
  kind: 'all',
  q: '',
  archived: false,
  selected: null,
  asset: null,
  version: null,
  refs: null,
  importOpen: false,
  importSeed: null,
  taskMapFrom: null,
  async refresh() {
    const { kind, q, archived } = get();
    set({ loading: true });
    try {
      const r = await assetsApi.list(kind === 'all' ? undefined : kind, q || undefined, archived);
      set({ list: r.assets, loading: false, error: null });
    } catch (e) {
      set({ loading: false, error: (e as Error).message });
    }
  },
  async select(id, v) {
    if (!id) {
      set({ selected: null, asset: null, version: null, refs: null });
      return;
    }
    set({ selected: id, refs: null });
    try {
      const a = await assetsApi.get(id);
      set({ asset: a, version: v ?? a.current });
      assetsApi.references(id).then((refs) => get().selected === id && set({ refs })).catch(() => undefined);
    } catch (e) {
      set({ error: (e as Error).message, asset: null });
    }
  },
  async reload() {
    const { selected, version } = get();
    await get().refresh();
    if (selected) await get().select(selected, version ?? undefined);
  },
  setVersion: (v) => set({ version: v }),
  setFilter(patch) {
    set(patch);
    void get().refresh();
  },
  openImport: (files = null) => set({ importOpen: true, importSeed: files }),
  closeImport: () => set({ importOpen: false, importSeed: null }),
  setTaskMapFrom: (x) => set({ taskMapFrom: x }),
  apply(a) {
    set((st) => ({
      asset: st.selected === a.id ? a : st.asset,
      version: st.selected === a.id ? a.current : st.version,
      list: st.list.some((x) => x.id === a.id) ? st.list.map((x) => (x.id === a.id ? a.summary : x)) : [a.summary, ...st.list],
    }));
  },
}));
