/** A map asset drawn as a background in task-map metres (inside an SVG group that already draws world coordinates). */
import { useEffect, useState } from 'react';
import type { XY } from '../../lab/types';
import { assetUrl, svgMatrix } from './api';
import type { BackgroundLayer } from './planBridge';

type Feature = { id: string | number; geometry: { type: string; coordinates: any }; properties: Record<string, any> }; // eslint-disable-line @typescript-eslint/no-explicit-any

const FILL: Record<string, string> = {
  boundary: 'rgba(140,115,84,0.10)', plot: 'rgba(98,160,72,0.22)', obstacle: 'rgba(90,110,150,0.35)', nogo: 'rgba(255,69,58,0.18)',
  road: 'rgba(150,150,150,0.30)', headland: 'rgba(200,170,110,0.25)', unload: 'rgba(191,90,242,0.5)', depot: 'rgba(255,159,10,0.6)', task: 'rgba(10,132,255,0.6)',
};
const STROKE: Record<string, string> = {
  boundary: '#6d5a40', plot: '#3f6b2a', obstacle: '#3c4a66', nogo: '#c0392b', road: '#7d7d7d', headland: '#9a7b3c', row: '#3f6b2a', unload: '#8e3cb8',
};

const cache = new Map<string, Promise<Feature[]>>();
function loadFeatures(url: string): Promise<Feature[]> {
  if (!cache.has(url)) cache.set(url, fetch(url).then((r) => (r.ok ? r.json() : { features: [] })).then((d) => d.features ?? []).catch(() => []));
  return cache.get(url)!;
}

const ring = (r: XY[]) => `M${r.map((p) => p.join(',')).join('L')}Z`;

function Shape({ f }: { f: Feature }) {
  const role = String(f.properties.role ?? 'unknown');
  const fill = FILL[role] ?? 'rgba(120,120,120,0.12)';
  const stroke = STROKE[role] ?? '#888';
  const g = f.geometry;
  const common = { stroke, strokeWidth: 1, vectorEffect: 'non-scaling-stroke' as const };
  switch (g.type) {
    case 'Polygon': return <path d={(g.coordinates as XY[][]).map(ring).join('')} fill={fill} fillRule="evenodd" {...common} />;
    case 'MultiPolygon': return <>{(g.coordinates as XY[][][]).map((p, i) => <path key={i} d={p.map(ring).join('')} fill={fill} fillRule="evenodd" {...common} />)}</>;
    case 'LineString': return <polyline points={(g.coordinates as XY[]).map((p) => p.join(',')).join(' ')} fill="none" {...common} strokeWidth={role === 'road' ? 3 : 1.2} />;
    case 'MultiLineString': return <>{(g.coordinates as XY[][]).map((l, i) => <polyline key={i} points={l.map((p) => p.join(',')).join(' ')} fill="none" {...common} />)}</>;
    default: return null;
  }
}

export function BackgroundShape({ layer, opacity }: { layer: BackgroundLayer; opacity?: number }) {
  const [feats, setFeats] = useState<Feature[] | null>(null);
  const url = assetUrl(layer.asset.id, layer.asset.version, layer.file) ?? '';
  useEffect(() => {
    if (layer.type !== 'vector') return;
    let alive = true;
    void loadFeatures(url).then((f) => alive && setFeats(f));
    return () => { alive = false; };
  }, [layer.type, url]);
  const op = opacity ?? layer.opacity ?? 0.6;
  if (layer.type === 'vector') {
    return <g opacity={op} pointerEvents="none">{(feats ?? []).map((f) => <Shape key={String(f.id)} f={f} />)}</g>;
  }
  if (!layer.affine || !layer.size_px) return null;
  return (
    <image href={url} width={layer.size_px[0]} height={layer.size_px[1]} transform={svgMatrix(layer.affine)} preserveAspectRatio="none"
      opacity={op} pointerEvents="none" style={{ imageRendering: layer.type === 'raster' ? 'pixelated' : 'auto' }} />
  );
}
