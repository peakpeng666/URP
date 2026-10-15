import type { XY } from '../types';
import type { Units } from './view';

export type NodeKind = 'depot' | 'task' | 'start' | 'other';
export type TaskState = 'pending' | 'reached' | 'missed';

export interface CanvasNode {
  id: string;
  xy: XY;
  kind: NodeKind;
  /** Graph role shown in the tooltip (row / headland / grid …). */
  role?: string;
  label?: string;
  demand?: number | null;
  state?: TaskState;
  /** Highlight ring (e.g. current task). */
  focus?: boolean;
  extra?: string[];
}

export interface CanvasPolygon {
  id: string;
  ring: XY[];
  kind: 'field' | 'headland' | 'row' | 'obstacle' | 'other';
}

export interface CanvasPath {
  id: string;
  points: XY[];
  color: string;
  /** Screen width in px. */
  width?: number;
  /** Screen-pixel dash pattern. */
  dash?: number[];
  opacity?: number;
  chevrons?: boolean;
  /** Translucent band of this world width under the line (coverage swath). */
  swath?: number | null;
  /** Service order badges along the path. */
  order?: { xy: XY; text: string }[];
  /** Text placed near the start of the path (e.g. "接驳 (Nav2)"). */
  tag?: string;
  title?: string;
  /** Layer toggle controlling this path (default 'routes'). */
  layer?: 'routes' | 'trails';
}

export interface CanvasMarker {
  id: string;
  xy: XY;
  kind: 'violation' | 'info';
  title: string;
}

export interface CanvasRobot {
  id: string;
  xy: XY;
  yaw: number;
  color: string;
  /** Physical radius in world units (drawn when big enough on screen). */
  radius?: number;
  ghost?: boolean;
  title: string;
}

export interface CanvasScene {
  units: Units;
  map?: { image: string; resolution: number; origin: readonly number[]; width: number; height: number } | null;
  polygons?: CanvasPolygon[];
  /** Graph arcs; `oneWay` arcs get arrowheads when zoomed in. */
  arcs?: { a: XY; b: XY; oneWay: boolean }[];
  nodes?: CanvasNode[];
  labels?: { xy: XY; text: string }[];
  paths?: CanvasPath[];
  markers?: CanvasMarker[];
  robots?: CanvasRobot[];
  /** Forbidden-turn polylines through a hovered node (u→v→w). */
  turnHints?: (nodeId: string) => XY[][];
}

export type LayerKey = 'map' | 'grid' | 'areas' | 'arcs' | 'nodes' | 'labels' | 'routes' | 'chevrons' | 'order' | 'markers' | 'trails';

export const DEFAULT_LAYERS: Record<LayerKey, boolean> = {
  map: true,
  grid: true,
  areas: true,
  arcs: true,
  nodes: true,
  labels: true,
  routes: true,
  chevrons: true,
  order: true,
  markers: true,
  trails: true,
};

export const LAYER_LABELS: Record<LayerKey, string> = {
  map: '占据栅格地图',
  grid: '网格',
  areas: '田块 / 作物行 / 地头',
  arcs: '路网弧',
  nodes: '节点',
  labels: '任务标签',
  routes: '路线',
  chevrons: '方向箭头',
  order: '服务顺序',
  markers: '地图检查违规',
  trails: '实际轨迹',
};
