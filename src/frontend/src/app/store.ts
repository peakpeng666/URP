import { useSyncExternalStore } from 'react';
import type { SourceRef } from '../data/types';

/** Minimal external store; components select slices with useStore. */
export function createStore<T>(initial: T) {
  let state = initial;
  const listeners = new Set<() => void>();
  return {
    get: () => state,
    set(next: Partial<T> | ((s: T) => T)) {
      state = typeof next === 'function' ? (next as (s: T) => T)(state) : { ...state, ...next };
      for (const l of listeners) l();
    },
    subscribe(listener: () => void) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
  };
}

export function useStore<T, S>(store: ReturnType<typeof createStore<T>>, select: (s: T) => S): S {
  return useSyncExternalStore(
    store.subscribe,
    () => select(store.get()),
    () => select(store.get()),
  );
}

export type CheckScope = 'historical' | 'project' | 'browser';
export type CheckStatus = 'pass' | 'pending' | 'fail' | 'none';

export interface ProvenanceSource {
  ref: SourceRef;
  /** JSON pointer, CSV column/row or array name the value comes from. */
  field?: string;
  note?: string;
}

export interface ProvenanceCheck {
  label: string;
  status: CheckStatus;
  scope: CheckScope;
  detail?: string;
}

export interface Provenance {
  title: string;
  value?: string;
  meaning?: string;
  derivation?: string;
  sources: ProvenanceSource[];
  checks?: ProvenanceCheck[];
}

export const provenanceStore = createStore<{ open: Provenance | null; returnFocus: HTMLElement | null }>({
  open: null,
  returnFocus: null,
});

export function openProvenance(p: Provenance, trigger?: HTMLElement | null) {
  provenanceStore.set({ open: p, returnFocus: trigger ?? (document.activeElement as HTMLElement | null) });
}

export function closeProvenance() {
  const { returnFocus } = provenanceStore.get();
  provenanceStore.set({ open: null, returnFocus: null });
  // Restore focus only after the drawer and its focus trap have unmounted, so
  // the trap's focusin handler cannot bounce focus back into a removed panel.
  if (returnFocus && returnFocus.isConnected) {
    requestAnimationFrame(() => {
      if (returnFocus.isConnected) returnFocus.focus();
    });
  }
}
