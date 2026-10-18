import { fleetClassFor } from './fleet';
import type { FleetInstance, FleetRoute } from './types';

type ServiceStop = { distance: number; seconds: number };

function routeTiming(inst: FleetInstance, route: FleetRoute): { speed: number; length: number; stops: ServiceStop[]; computedDuration: number } {
  const speed = route.speed_mps ?? fleetClassFor(inst, route.fleet_class)?.speed_mps ?? inst.vehicles.speed_mps ?? 1;
  const safeSpeed = Number.isFinite(speed) && speed > 0 ? speed : 1;
  const cumulative = [0];
  for (let i = 1; i < route.polyline.length; i++) {
    const a = route.polyline[i - 1];
    const b = route.polyline[i];
    cumulative.push(cumulative[i - 1] + Math.hypot(b[0] - a[0], b[1] - a[1]));
  }
  const length = cumulative[cumulative.length - 1] ?? 0;
  const stops = (route.services ?? []).map((service) => {
    const task = inst.tasks.find((item) => item.id === service.task);
    const index = Math.max(0, Math.min(cumulative.length - 1, Math.round(service.position)));
    const seconds = task?.service_s ?? 0;
    return { distance: cumulative[index] ?? 0, seconds: Number.isFinite(seconds) && seconds > 0 ? seconds : 0 };
  }).filter((stop) => stop.seconds > 0).sort((a, b) => a.distance - b.distance);
  const serviceDuration = stops.reduce((sum, stop) => sum + stop.seconds, 0);
  return { speed: safeSpeed, length, stops, computedDuration: length / safeSpeed + serviceDuration };
}

export function playbackDuration(inst: FleetInstance, routes: FleetRoute[]): number {
  return Math.max(1, ...routes.map((route) => {
    const timing = routeTiming(inst, route);
    return Number.isFinite(route.duration_s) && route.duration_s > 0 ? route.duration_s : timing.computedDuration;
  }));
}

export function playbackDistanceAtTime(inst: FleetInstance, route: FleetRoute, time: number): number {
  const timing = routeTiming(inst, route);
  const t = Math.max(0, time);
  let elapsed = 0;
  let distance = 0;
  for (const stop of timing.stops) {
    const arrival = elapsed + (stop.distance - distance) / timing.speed;
    if (t < arrival) return distance + (t - elapsed) * timing.speed;
    if (t <= arrival + stop.seconds) return stop.distance;
    elapsed = arrival + stop.seconds;
    distance = stop.distance;
  }
  return Math.min(timing.length, distance + Math.max(0, t - elapsed) * timing.speed);
}
