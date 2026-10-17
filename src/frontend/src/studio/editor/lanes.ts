import { useEffect, useRef, useState } from 'react';
import { studio } from '../api';
import type { FleetInstance, LaneInfo } from '../types';

/** Only these inputs decide where the crop rows and lanes are. */
export function laneKey(inst: FleetInstance): string {
  return JSON.stringify([
    inst.boundary,
    inst.plots.map((p) => [p.polygon, p.crop ?? '', p.rows_deg ?? 0]),
    inst.obstacles.map((o) => o.polygon),
    inst.robot_radius,
  ]);
}

const cache = new Map<string, LaneInfo>();
const pending = new Map<string, Promise<LaneInfo>>();

function fetchLanes(key: string, inst: FleetInstance): Promise<LaneInfo> {
  const hit = cache.get(key);
  if (hit) return Promise.resolve(hit);
  let p = pending.get(key);
  if (!p) {
    p = studio.lanes(inst).then((info) => {
      cache.set(key, info);
      if (cache.size > 24) cache.delete(cache.keys().next().value as string);
      return info;
    }).finally(() => pending.delete(key));
    pending.set(key, p);
  }
  return p;
}

/**
 * Lanes between the crop rows of a task map, laid out by the planner (POST fleet/lanes). Refetched a moment
 * after the rows' inputs change; the previous lanes stay on screen meanwhile. `null` while off or unavailable.
 */
export function useLanes(inst: FleetInstance | null, on: boolean): LaneInfo | null {
  const key = inst && on ? laneKey(inst) : '';
  const [info, setInfo] = useState<LaneInfo | null>(() => (key ? cache.get(key) ?? null : null));
  const latest = useRef(inst);
  latest.current = inst;
  useEffect(() => {
    const current = latest.current;
    if (!key || !current) {
      setInfo(null);
      return;
    }
    const hit = cache.get(key);
    if (hit) {
      setInfo(hit);
      return;
    }
    let live = true;
    const timer = setTimeout(() => {
      fetchLanes(key, current).then((r) => { if (live) setInfo(r); }).catch(() => { if (live) setInfo(null); });
    }, 250);
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [key]);
  return info;
}
