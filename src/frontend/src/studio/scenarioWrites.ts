/** Idempotent scenario creates on top of the existing Lab endpoints (see pendingWrites.ts). */
import { lab, LabApiError } from '../lab/api';
import type { Scenario } from '../lab/types';
import { studio } from './api';
import type { FleetScenario } from './types';
import { clientScenarioId, containsSubmittedValue, contentDigest, createOnce, mismatch } from './pendingWrites';

type ForkBody = { instance?: unknown; title?: string };

/** Fork / draft copy: the client chooses the new id, so a retry can ask for it first. */
export function forkScenarioOnce(sourceId: string, body: ForkBody = {}, kind: 'fork' | 'draft-copy' = 'fork'): Promise<Scenario> {
  return createOnce<Scenario>({
    key: `${kind}:${sourceId}:${contentDigest(body)}`,
    kind,
    id: () => clientScenarioId(sourceId),
    send: (id) => studio.forkScenario(sourceId, { ...body, client_id: id }),
    recover: async (id) => {
      const found = await lab.scenario(id);
      const forkedFrom = (found.provenance as { forked_from?: string } | undefined)?.forked_from;
      if (found.id !== id || forkedFrom !== sourceId
        || (body.instance !== undefined && !containsSubmittedValue(found.instance, body.instance))) throw mismatch(id);
      return found;
    },
    // An older gateway ignores client_id and names the copy itself; that write is still single.
    acceptForeignId: true,
  });
}

/** Scenario JSON import: the id is part of the submitted document. */
export function importScenarioOnce(obj: unknown): Promise<Scenario> {
  const doc = obj as { id?: unknown; problem_class?: unknown; instance?: unknown };
  const id = typeof doc?.id === 'string' ? doc.id.trim().toLowerCase() : '';
  if (!id) return studio.importScenario(obj); // the server reports the missing id
  return createOnce<Scenario>({
    key: `import:${contentDigest(obj)}`,
    kind: 'import',
    id: () => id,
    send: () => studio.importScenario(obj),
    recover: async (sid) => {
      const found = await lab.scenario(sid);
      if (found.id !== sid || found.problem_class !== doc.problem_class
        || (found as Scenario & { origin?: string }).origin !== 'user'
        || !containsSubmittedValue(found.instance, doc.instance)) throw mismatch(sid);
      return found;
    },
  });
}

/**
 * GeoJSON import: the endpoint names the scenario itself, so recovery after an uncertain outcome
 * looks for the user scenario this import produced (same title) before writing again.
 */
export function importGeojsonOnce(geojson: unknown, title?: string): Promise<FleetScenario> {
  const key = `geojson:${contentDigest({ geojson, title: title ?? null })}`;
  return createOnce<FleetScenario>({
    key,
    kind: 'geojson',
    id: () => clientScenarioId('geojson'),
    send: () => studio.importGeojson(geojson, title),
    recover: async () => {
      const { scenarios } = await lab.scenarios();
      const hit = scenarios.filter((x) => (x as { origin?: string }).origin === 'user' && x.title === title);
      if (hit.length !== 1) throw new LabApiError('未找到该 GeoJSON 的保存结果', 'not_found', 404);
      return (await lab.scenario(hit[0]!.id)) as unknown as FleetScenario;
    },
    acceptForeignId: true,
  });
}
