import type { XY } from '../lab/types';
import type { FleetClass, FleetInstance, FleetVehicles } from './types';

export function depotsOf(inst: FleetInstance): XY[] {
  return inst.depots?.length ? inst.depots : [inst.depot];
}

export function normalizeFleetInstance(inst: FleetInstance): FleetInstance {
  const depots = depotsOf(inst).map(([x, y]) => [x, y] as XY);
  const vehicles = { ...inst.vehicles } as FleetVehicles;
  if (vehicles.fleet?.length) {
    delete vehicles.count;
    delete vehicles.capacity;
    delete vehicles.names;
  }
  return { ...inst, depot: depots[0], depots, vehicles };
}

export function setDepot(inst: FleetInstance, index: number, xy: XY): FleetInstance {
  const depots = depotsOf(inst).slice();
  if (index < 0 || index >= depots.length) return inst;
  depots[index] = xy;
  return normalizeFleetInstance({ ...inst, depots, depot: depots[0] });
}

export function addDepot(inst: FleetInstance, xy: XY): FleetInstance {
  const depots = depotsOf(inst);
  if (depots.length >= 8) return inst;
  return normalizeFleetInstance({ ...inst, depots: [...depots, xy], depot: depots[0] });
}

export function removeDepot(inst: FleetInstance, index: number): FleetInstance {
  const depots = depotsOf(inst);
  if (depots.length <= 1 || index < 0 || index >= depots.length) return inst;
  const next = depots.filter((_, i) => i !== index);
  return normalizeFleetInstance({ ...inst, depots: next, depot: next[0] });
}

export function fleetClasses(inst: FleetInstance): FleetClass[] {
  const v = inst.vehicles;
  if (v.fleet?.length) return v.fleet;
  return [{
    name: '统一车型',
    count: v.count ?? 1,
    capacity: v.capacity ?? 1,
    speed_mps: v.speed_mps ?? 1,
    robot_radius: inst.robot_radius,
    payload: 'load',
    min_turn_radius_m: 0,
  }];
}

export function fleetClassFor(inst: FleetInstance, reference: string | number | undefined): FleetClass | undefined {
  const classes = fleetClasses(inst);
  if (typeof reference === 'number') return classes[reference];
  if (typeof reference === 'string') return classes.find((item, index) => (item.name ?? `车型${index + 1}`) === reference);
  return classes.length === 1 ? classes[0] : undefined;
}

export function fleetSize(inst: FleetInstance): number {
  return fleetClasses(inst).reduce((sum, item) => sum + item.count, 0);
}

export function fleetSpeed(inst: FleetInstance): number {
  return inst.vehicles.speed_mps ?? fleetClasses(inst)[0]?.speed_mps ?? 1;
}

export function fleetCapacity(inst: FleetInstance): number {
  const classes = fleetClasses(inst);
  return classes.length === 1 ? classes[0].capacity : Math.max(...classes.map((item) => item.capacity));
}

function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .filter(([, item]) => item !== undefined)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, item]) => [key, canonical(item)]),
    );
  }
  return value;
}

export function stableStringify(value: unknown): string {
  return JSON.stringify(canonical(value));
}

export function planningFingerprint(inst: FleetInstance | null | undefined): string {
  if (!inst) return '';
  const normalized = normalizeFleetInstance(inst);
  const { depot: _alias, ...input } = normalized;
  void _alias;
  return stableStringify({
    ...input,
    vehicles: {
      ...input.vehicles,
      trips: input.vehicles.trips ?? 'multi',
      travel: input.vehicles.travel ?? 'free',
    },
  });
}
