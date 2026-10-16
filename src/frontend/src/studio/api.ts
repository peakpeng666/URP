import { LabApiError } from '../lab/api';
import type { Scenario } from '../lab/types';
import type {
  Analysis,
  CvrplibInstance,
  CvrplibSet,
  FieldEntry,
  FieldSimState,
  FieldSimSummary,
  FleetInstance,
  FleetScenario,
  InstanceSpace,
  ParseResult,
  Reference,
  Study,
  StudySpec,
} from './types';

const BASE = '/lab/api';

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      cache: 'no-store',
      headers: body === undefined ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new LabApiError('连接不上工作台服务（127.0.0.1:4100）', 'network', 0);
  }
  const text = await response.text();
  const data = text ? (JSON.parse(text) as unknown) : null;
  if (!response.ok) {
    const e = (data ?? {}) as { error?: string; message?: string };
    throw new LabApiError(e.message ?? `请求失败（HTTP ${response.status}）`, e.error ?? 'http_error', response.status);
  }
  return data as T;
}

export const studio = {
  examples: () => call<{ examples: string[] }>('GET', '/compose/examples'),
  parse: (text: string) => call<ParseResult>('POST', '/compose/parse', { text }),
  compose: (text: string, opts: { seed?: number; field_id?: string; overrides?: Record<string, unknown> } = {}) =>
    call<FleetScenario>('POST', '/compose', { text, ...opts }),
  saveScenario: (id: string, body: { instance?: FleetInstance | unknown; title?: string; summary?: string }) =>
    call<FleetScenario>('PUT', `/scenarios/${encodeURIComponent(id)}`, body),
  forkScenario: (id: string, body: { instance?: unknown; title?: string } = {}) =>
    call<Scenario>('POST', `/scenarios/${encodeURIComponent(id)}/fork`, body),
  importGeojson: (geojson: unknown, title?: string) => call<FleetScenario>('POST', '/scenarios/import/geojson', { geojson, title }),
  importScenario: (scenario: unknown) => call<Scenario>('POST', '/scenarios', scenario),
  library: () => call<{ cvrplib: Record<string, number | string>; fields: Record<string, unknown>; references: { count: number } }>('GET', '/library'),
  cvrplibSets: () => call<{ sets: CvrplibSet[] }>('GET', '/library/cvrplib/sets'),
  cvrplibInstances: (set?: string, q?: string) => {
    const p = new URLSearchParams();
    if (set) p.set('set', set);
    if (q) p.set('q', q);
    return call<{ instances: CvrplibInstance[] }>('GET', `/library/cvrplib/instances?${p}`);
  },
  fields: (country?: string, q?: string) => {
    const p = new URLSearchParams();
    if (country) p.set('country', country);
    if (q) p.set('q', q);
    return call<{ status: { downloaded: boolean; fields: number; images: boolean }; fields: FieldEntry[] }>('GET', `/library/fields?${p}`);
  },
  fetchFields: (images = false) => call<Record<string, unknown>>('POST', '/library/fields/fetch', { images }),
  references: (topic?: string, q?: string) => {
    const p = new URLSearchParams();
    if (topic) p.set('topic', topic);
    if (q) p.set('q', q);
    return call<{ references: Reference[]; topics: Record<string, string> }>('GET', `/references?${p}`);
  },
  source: (path: string) => call<{ path: string; language: string; text: string }>('GET', `/source?path=${encodeURIComponent(path)}`),
  studies: () => call<{ studies: Study[] }>('GET', '/studies'),
  study: (id: string) => call<Study>('GET', `/studies/${encodeURIComponent(id)}`),
  createStudy: (spec: StudySpec) => call<Study>('POST', '/studies', spec),
  cancelStudy: (id: string) => call<Study>('POST', `/studies/${encodeURIComponent(id)}/cancel`, {}),
  analysis: (id: string) => call<Analysis>('GET', `/studies/${encodeURIComponent(id)}/analysis`),
  instanceSpace: (id: string) => call<InstanceSpace>('GET', `/studies/${encodeURIComponent(id)}/instance-space`),
  analyzeRuns: (run_ids: string[]) => call<Analysis>('POST', '/analysis', { run_ids }),
  fieldsim: () => call<FieldSimState>('GET', '/fieldsim'),
  startFieldsim: (run_id: string, opts: { gui?: boolean; rviz?: boolean; real_time_factor?: number } = {}) =>
    call<FieldSimState>('POST', '/fieldsim', { run_id, ...opts }),
  stopFieldsim: () => call<FieldSimState>('POST', '/fieldsim/stop', {}),
  fieldsimWindow: (kind: 'gui' | 'rviz', on: boolean) => call<FieldSimState>('POST', '/fieldsim/window', { kind, on }),
  fieldsimResults: (run_id?: string) =>
    call<{ results: FieldSimSummary[] }>('GET', `/fieldsim/results${run_id ? `?run_id=${encodeURIComponent(run_id)}` : ''}`),
};

export const urls = {
  referencesBib: (keys?: string[]) => `${BASE}/references.bib${keys?.length ? `?keys=${keys.join(',')}` : ''}`,
  fieldImage: (id: string) => `${BASE}/library/fields/${encodeURIComponent(id)}/image`,
  fieldOutline: (id: string) => `${BASE}/library/fields/${encodeURIComponent(id)}/outline.svg`,
  scenarioExport: (id: string, format: 'json' | 'geojson') => `${BASE}/scenarios/${encodeURIComponent(id)}/export?format=${format}`,
  studyExport: (id: string, format: 'csv' | 'json' | 'latex') => `${BASE}/studies/${encodeURIComponent(id)}/export?format=${format}`,
  fieldsimResult: (sid: string) => `${BASE}/fieldsim/results/${encodeURIComponent(sid)}`,
  robotUrdf: (model = 'turtlebot4') => `${BASE}/ros/robots/${model}.urdf`,
  rosPackage: (pkg: string) => `${BASE}/ros/package/${pkg}`,
};
