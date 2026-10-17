/** Where the live views get their streams: the field fleet simulation or the TurtleBot4 session. */
import { useEffect } from 'react';
import { create } from 'zustand';
import { lab, useLabResource } from '../../lab/api';
import type { SimState } from '../../lab/types';
import { studio } from '../api';
import type { FieldSimState, LiveWeb } from '../types';
import { ros } from './foxglove';

interface FieldSimStore {
  state: FieldSimState | null;
  error: string | null;
  actionError: string | null;
}
export const useFieldSimStore = create<FieldSimStore>(() => ({ state: null, error: null, actionError: null }));
export function setFieldSimActionError(actionError: string | null) {
  useFieldSimStore.setState({ actionError });
}

let watchers = 0;
let timer = 0;
export async function refreshFieldSim() {
  try {
    useFieldSimStore.setState({ state: await studio.fieldsim(), error: null });
  } catch (e) {
    useFieldSimStore.setState({ error: (e as Error).message });
  }
}

/** Field simulation state, polled once for all mounted views. */
export function useFieldSim(): FieldSimStore {
  useEffect(() => {
    if (watchers++ === 0) {
      void refreshFieldSim();
      timer = window.setInterval(refreshFieldSim, 1000);
    }
    return () => {
      if (--watchers === 0) window.clearInterval(timer);
    };
  }, []);
  return useFieldSimStore();
}

export interface LiveSource {
  web: LiveWeb;
  kind: 'field' | 'robot' | null;
  field: FieldSimState | null;
  robot: SimState | null;
}

/** The running simulation's web endpoints; also keeps the shared ROS connection pointed at it. */
export function useLive(): LiveSource {
  const field = useFieldSim().state;
  const robot = useLabResource<SimState>('live-sim-state', () => lab.simState(), { event: 'sim_state', pollMs: 5000 }).data;
  const robotWeb = (robot as (SimState & { web?: LiveWeb }) | null)?.web;
  const kind = field?.running && field.web?.ros ? 'field' : robotWeb?.ros || robotWeb?.gazebo ? 'robot' : field?.running ? 'field' : null;
  const web = (kind === 'field' ? field?.web : kind === 'robot' ? robotWeb : undefined) ?? {};
  const url = web.ros?.url ?? null;
  useEffect(() => {
    ros.connect(url);
  }, [url]);
  return { web, kind, field, robot };
}
