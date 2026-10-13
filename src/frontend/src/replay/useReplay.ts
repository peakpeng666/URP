import { useEffect, useMemo, useRef, useSyncExternalStore } from 'react';
import { ReplayController, type ReplaySnapshot } from './controller';
import { loadStreamIndex } from '../data/api';
import type { Policy, Stream } from '../data/types';
import { useAsync } from '../data/api';

const POLICIES: Policy[] = ['BF', 'BF_then_EoH', 'published_EoH', 'SELECTOR'];

/** "SBS" is a role alias; resolve it to the training SBS branch policy. */
export function resolvePolicy(token: string | null, sbs: Policy): Policy | null {
  if (!token) return null;
  if (token === 'SBS') return sbs;
  return POLICIES.includes(token as Policy) ? (token as Policy) : null;
}

export function useController(): ReplayController {
  const ref = useRef<ReplayController | null>(null);
  if (!ref.current) ref.current = new ReplayController();
  // Only stop playback on unmount. We deliberately do NOT abort in-flight loads
  // or reset state here: under React StrictMode the mount→unmount→mount cycle
  // would otherwise cancel the keeper load. load() dedupes a repeat of the same
  // request, so the double-invoke is a no-op rather than an abort storm.
  useEffect(() => () => ref.current?.pause(), []);
  return ref.current;
}

export function useReplaySnapshot(controller: ReplayController): ReplaySnapshot {
  return useSyncExternalStore(controller.subscribe, controller.getSnapshot, controller.getSnapshot);
}

export function useStreamIndex() {
  return useAsync('stream-index', () => loadStreamIndex());
}

export function useStream(index: Map<string, Stream> | null, instanceId: string | null) {
  return useMemo(() => (index && instanceId ? index.get(instanceId) ?? null : null), [index, instanceId]);
}
