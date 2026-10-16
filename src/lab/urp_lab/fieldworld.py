"""Gazebo Fortress world for a multi-vehicle field task.

The task map becomes a world whose frame equals the map frame (local metres): soil, plots with
crop rows along each plot's row direction, obstacles by kind, the depot and a marker per task,
coloured by the vehicle the plan assigned it to. Every vehicle is a differential-drive robot built
from the official Fortress ``diff_drive.sdf`` example (DiffDrive system), parked next to the depot.

Polygons are written as extruded binary STL meshes so both the Gazebo GUI and gzweb in the browser
can draw them; obstacle collisions use SDF polylines. Crop rows are visual only: the planner treats
plots as drivable, so the robots must be able to cross them.
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

import shapely
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

GRASS = (0.47, 0.63, 0.36, 1)
SOIL = (0.55, 0.45, 0.33, 1)
OBSTACLES = {  # kind → (height m, rgba, collides)
    'pond': (0.06, (0.27, 0.55, 0.86, 1), True),
    'ditch': (0.05, (0.33, 0.55, 0.74, 1), True),
    'building': (4.0, (0.74, 0.74, 0.76, 1), True),
    'greenhouse': (3.0, (0.86, 0.93, 0.95, 0.55), True),
    'rock': (0.7, (0.52, 0.5, 0.47, 1), True),
    'tree': (0.0, (0.2, 0.5, 0.24, 1), True),
}
CROPS = {  # crop → (row spacing m, row width m, height m, rgba)
    '小麦': (1.2, 0.5, 0.35, (0.85, 0.76, 0.38, 1)),
    '玉米': (1.5, 0.6, 0.6, (0.36, 0.62, 0.25, 1)),
    '大豆': (1.2, 0.5, 0.3, (0.42, 0.64, 0.3, 1)),
    '油菜': (1.2, 0.5, 0.35, (0.86, 0.82, 0.3, 1)),
    '水稻': (1.0, 0.45, 0.25, (0.5, 0.72, 0.36, 1)),
    '茶': (1.8, 0.9, 0.6, (0.22, 0.48, 0.24, 1)),
    '猕猴桃': (3.5, 1.2, 0.9, (0.3, 0.52, 0.22, 1)),
    '果树': (4.0, 1.4, 1.0, (0.26, 0.5, 0.22, 1)),
}
DEFAULT_CROP = (1.5, 0.6, 0.4, (0.4, 0.63, 0.29, 1))
MAX_ROWS = 160
# Robot: 0.8 × 0.56 m footprint (circumscribed radius 0.49 m, inside the planner's robot radius).
WHEEL_R, WHEEL_SEP = 0.15, 0.66


@dataclass
class Vehicle:
    name: str           # Gazebo model name, also the ROS namespace
    label: str          # what the plan calls it (① 号车 …)
    color: str          # hex from the plan
    start: tuple[float, float, float]
    path: list[list[float]]   # start → depot → planned polyline (incl. returns to the depot)
    tasks: list[dict]          # [{id, label, xy, service_s}] in visiting order


def _rgba(hexcolor: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hexcolor.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)) + (alpha,)  # type: ignore[return-value]


def _material(rgba) -> str:
    r, g, b, a = rgba
    return (f'<material><ambient>{r:.3f} {g:.3f} {b:.3f} {a:.3f}</ambient><diffuse>{r:.3f} {g:.3f} {b:.3f} {a:.3f}</diffuse>'
            f'<specular>0.05 0.05 0.05 1</specular></material>' + (f'<transparency>{1 - a:.2f}</transparency>' if a < 1 else ''))


def _polys(geom) -> list[Polygon]:
    if geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return [g for g in getattr(geom, 'geoms', []) if isinstance(g, Polygon)]


def extrude(polys: list[Polygon], z0: float, z1: float) -> list[tuple]:
    """Triangles (a, b, c, normal) of extruded polygons: top face plus walls."""
    tris = []
    for poly in polys:
        poly = orient(poly.buffer(0), 1.0)
        for t in shapely.constrained_delaunay_triangles(poly).geoms:
            (x1, y1), (x2, y2), (x3, y3) = list(t.exterior.coords)[:3]
            if (x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1) < 0:
                (x2, y2), (x3, y3) = (x3, y3), (x2, y2)
            tris.append(((x1, y1, z1), (x2, y2, z1), (x3, y3, z1), (0.0, 0.0, 1.0)))
        if z1 - z0 > 1e-6:
            for ring in [poly.exterior, *poly.interiors]:
                pts = list(ring.coords)
                for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                    dx, dy = bx - ax, by - ay
                    length = math.hypot(dx, dy)
                    if length < 1e-9:
                        continue
                    n = (dy / length, -dx / length, 0.0)
                    tris.append(((ax, ay, z0), (bx, by, z0), (bx, by, z1), n))
                    tris.append(((ax, ay, z0), (bx, by, z1), (ax, ay, z1), n))
    return tris


def write_stl(path: Path, polys: list[Polygon], z0: float, z1: float) -> int:
    """Binary STL: read by Gazebo and by gzweb over the WebSocket server (its OBJ path expects text)."""
    tris = extrude(polys, z0, z1)
    out = bytearray(b'generated field mesh'.ljust(80, b' '))
    out += struct.pack('<I', len(tris))
    for a, b, c, n in tris:
        out += struct.pack('<12fH', *n, *a, *b, *c, 0)
    path.write_bytes(bytes(out))
    return len(tris)


def crop_rows(plot: dict) -> list[Polygon]:
    poly = Polygon(plot['polygon'])
    spacing, width, _, _ = CROPS.get(plot.get('crop', ''), DEFAULT_CROP)
    angle = math.radians(float(plot.get('rows_deg', 0) or 0))
    inner = poly.buffer(-0.8)
    if inner.is_empty:
        return []
    ux, uy = math.cos(angle), math.sin(angle)
    nx, ny = -uy, ux
    cx, cy = inner.centroid.x, inner.centroid.y
    corners = list(inner.envelope.exterior.coords)
    offsets = [(x - cx) * nx + (y - cy) * ny for x, y in corners]
    span = max(math.hypot(x - cx, y - cy) for x, y in corners) + 1
    spacing = max(spacing, (max(offsets) - min(offsets)) / MAX_ROWS)
    rows = []
    k = math.ceil(min(offsets) / spacing)
    while k * spacing <= max(offsets):
        ox, oy = cx + nx * k * spacing, cy + ny * k * spacing
        line = LineString([(ox - ux * span, oy - uy * span), (ox + ux * span, oy + uy * span)])
        rows.extend(_polys(line.buffer(width / 2, cap_style='flat').intersection(inner)))
        k += 1
    return rows


def _robot(v: Vehicle, index: int, speed: float) -> str:
    x, y, yaw = v.start
    body = _rgba(v.color)
    bit = f'0x{1 << (index + 1):04x}'  # robots never collide with each other, only with the world
    chassis_z = WHEEL_R + 0.1

    def wheel(name, wy):
        return f"""
      <link name='{name}'>
        <pose>0.12 {wy} {WHEEL_R} -1.5707 0 0</pose>
        <inertial><mass>2</mass><inertia><ixx>0.012</ixx><ixy>0</ixy><ixz>0</ixz><iyy>0.012</iyy><iyz>0</iyz><izz>0.0225</izz></inertia></inertial>
        <visual name='visual'><geometry><cylinder><radius>{WHEEL_R}</radius><length>0.08</length></cylinder></geometry>{_material((0.12, 0.12, 0.13, 1))}</visual>
        <collision name='collision'><geometry><cylinder><radius>{WHEEL_R}</radius><length>0.08</length></cylinder></geometry>
          <surface><contact><collide_bitmask>{bit}</collide_bitmask></contact></surface></collision>
      </link>"""

    return f"""
    <model name='{v.name}'>
      <pose>{x:.3f} {y:.3f} 0.02 0 0 {yaw:.4f}</pose>
      <link name='chassis'>
        <pose>0 0 {chassis_z:.3f} 0 0 0</pose>
        <inertial><mass>20</mass><inertia><ixx>0.67</ixx><ixy>0</ixy><ixz>0</ixz><iyy>1.22</iyy><iyz>0</iyz><izz>1.59</izz></inertia></inertial>
        <visual name='body'><geometry><box><size>0.8 0.56 0.22</size></box></geometry>{_material((0.93, 0.93, 0.92, 1))}</visual>
        <visual name='top'><pose>0 0 0.12 0 0 0</pose><geometry><box><size>0.7 0.5 0.03</size></box></geometry>{_material(body)}</visual>
        <visual name='mast'><pose>-0.25 0 0.45 0 0 0</pose><geometry><cylinder><radius>0.02</radius><length>0.7</length></cylinder></geometry>{_material((0.3, 0.3, 0.32, 1))}</visual>
        <visual name='beacon'><pose>-0.25 0 0.82 0 0 0</pose><geometry><sphere><radius>0.09</radius></sphere></geometry>{_material(body)}</visual>
        <visual name='front'><pose>0.41 0 0.02 0 0 0</pose><geometry><box><size>0.02 0.4 0.08</size></box></geometry>{_material((0.15, 0.15, 0.16, 1))}</visual>
        <collision name='collision'><geometry><box><size>0.8 0.56 0.22</size></box></geometry>
          <surface><contact><collide_bitmask>{bit}</collide_bitmask></contact></surface></collision>
      </link>{wheel('left_wheel', WHEEL_SEP / 2)}{wheel('right_wheel', -WHEEL_SEP / 2)}
      <link name='caster'>
        <pose>-0.3 0 0.06 0 0 0</pose>
        <inertial><mass>0.5</mass><inertia><ixx>0.001</ixx><ixy>0</ixy><ixz>0</ixz><iyy>0.001</iyy><iyz>0</iyz><izz>0.001</izz></inertia></inertial>
        <visual name='visual'><geometry><sphere><radius>0.06</radius></sphere></geometry>{_material((0.2, 0.2, 0.2, 1))}</visual>
        <collision name='collision'><geometry><sphere><radius>0.06</radius></sphere></geometry>
          <surface><friction><ode><mu>0.01</mu><mu2>0.01</mu2></ode></friction><contact><collide_bitmask>{bit}</collide_bitmask></contact></surface></collision>
      </link>
      <joint name='left_wheel_joint' type='revolute'><parent>chassis</parent><child>left_wheel</child>
        <axis><xyz>0 0 1</xyz><limit><lower>-1.79769e+308</lower><upper>1.79769e+308</upper></limit></axis></joint>
      <joint name='right_wheel_joint' type='revolute'><parent>chassis</parent><child>right_wheel</child>
        <axis><xyz>0 0 1</xyz><limit><lower>-1.79769e+308</lower><upper>1.79769e+308</upper></limit></axis></joint>
      <joint name='caster_joint' type='ball'><parent>chassis</parent><child>caster</child></joint>
      <plugin filename="ignition-gazebo-diff-drive-system" name="gz::sim::systems::DiffDrive">
        <left_joint>left_wheel_joint</left_joint>
        <right_joint>right_wheel_joint</right_joint>
        <wheel_separation>{WHEEL_SEP}</wheel_separation>
        <wheel_radius>{WHEEL_R}</wheel_radius>
        <odom_publish_frequency>20</odom_publish_frequency>
        <topic>/model/{v.name}/cmd_vel</topic>
        <odom_topic>/model/{v.name}/odometry</odom_topic>
        <frame_id>{v.name}/odom</frame_id>
        <child_frame_id>{v.name}/base_link</child_frame_id>
        <max_linear_acceleration>1.5</max_linear_acceleration>
        <min_linear_acceleration>-2</min_linear_acceleration>
        <max_angular_acceleration>4</max_angular_acceleration>
        <min_angular_acceleration>-4</min_angular_acceleration>
        <max_linear_velocity>{max(0.5, speed * 1.2):.2f}</max_linear_velocity>
        <min_linear_velocity>-0.5</min_linear_velocity>
        <max_angular_velocity>2.0</max_angular_velocity>
        <min_angular_velocity>-2.0</min_angular_velocity>
      </plugin>
    </model>"""


def plan_vehicles(inst: dict, routes: list[dict]) -> list[Vehicle]:
    """Parking spots next to the depot (collision free), and each vehicle's drive path."""
    boundary = Polygon(inst['boundary'])
    blocked = unary_union([Polygon(o['polygon']) for o in inst.get('obstacles', [])]) if inst.get('obstacles') else Polygon()
    free = boundary.buffer(-0.7).difference(blocked.buffer(0.7))
    dx, dy = inst['depot']
    candidates = [(dx + 1.6 * i, dy + 1.6 * j) for d in range(0, 8) for i in range(-d, d + 1) for j in range(-d, d + 1)
                  if max(abs(i), abs(j)) == d and (i, j) != (0, 0)]
    spots = []
    for c in sorted(candidates, key=lambda c: (math.dist(c, (dx, dy)), c)):
        if free.contains(Point(c)) and all(math.dist(c, s) >= 1.5 for s in spots):
            spots.append(c)
        if len(spots) >= len(routes):
            break
    if len(spots) < len(routes):
        raise ValueError('车库附近没有足够的空地停放所有车辆')
    tasks = {t['id']: t for t in inst['tasks']}
    out = []
    for i, (r, spot) in enumerate(zip(routes, spots)):
        poly = [list(map(float, p)) for p in r.get('polyline') or []]
        if len(poly) < 2:
            continue
        path = [list(spot), [float(dx), float(dy)], *poly]
        clean = [path[0]]
        for p in path[1:]:
            if math.dist(p, clean[-1]) > 1e-3:
                clean.append(p)
        first = clean[1]
        yaw = math.atan2(first[1] - spot[1], first[0] - spot[0])
        order = [tasks[t] for t in r.get('sequence', []) if t in tasks]
        out.append(Vehicle(name=f'vehicle_{i + 1}', label=r.get('vehicle_name') or f'车{i + 1}', color=r.get('color') or '#0a84ff',
                           start=(spot[0], spot[1], yaw), path=clean,
                           tasks=[{'id': t['id'], 'label': str(t.get('label', t['id'])), 'xy': t['xy'],
                                   'service_s': float(t.get('service_s') or 0)} for t in order]))
    return out


def build(inst: dict, routes: list[dict], out_dir: Path, world: str, real_time_factor: float = 4.0) -> dict:
    """Writes world.sdf and its meshes into out_dir; returns what the session needs to drive it."""
    out_dir.mkdir(parents=True, exist_ok=True)
    mesh_dir = out_dir / 'meshes'
    mesh_dir.mkdir(exist_ok=True)
    boundary = Polygon(inst['boundary'])
    minx, miny, maxx, maxy = boundary.bounds
    vehicles = plan_vehicles(inst, routes)
    speed = float(inst['vehicles'].get('speed_mps') or 1.0)
    triangles = 0
    visuals = []

    def mesh_visual(name, polys, z0, z1, rgba):
        nonlocal triangles
        if not polys:
            return
        path = mesh_dir / f'{name}.stl'
        triangles += write_stl(path, polys, z0, z1)
        visuals.append(f"<visual name='{name}'><geometry><mesh><uri>{escape(str(path))}</uri></mesh></geometry>{_material(rgba)}</visual>")

    mesh_visual('field', [boundary], 0.0, 0.02, SOIL)
    for k, plot in enumerate(inst.get('plots', [])):
        _, _, height, rgba = CROPS.get(plot.get('crop', ''), DEFAULT_CROP)
        mesh_visual(f'plot_{k + 1}', _polys(Polygon(plot['polygon']).buffer(0)), 0.02, 0.035,
                    tuple(c * 0.82 for c in SOIL[:3]) + (1,))
        mesh_visual(f'rows_{k + 1}', crop_rows(plot), 0.035, 0.035 + height, rgba)

    obstacles = []
    for k, o in enumerate(inst.get('obstacles', [])):
        kind = o.get('kind', 'building')
        height, rgba, collides = OBSTACLES.get(kind, OBSTACLES['building'])
        poly = Polygon(o['polygon']).buffer(0)
        name = f'obstacle_{k + 1}'
        if kind == 'tree':
            c = poly.centroid
            radius = max(0.6, math.sqrt(poly.area / math.pi))
            obstacles.append(f"""
    <model name='{name}'><static>true</static><pose>{c.x:.3f} {c.y:.3f} 0 0 0 0</pose><link name='link'>
      <visual name='trunk'><pose>0 0 1 0 0 0</pose><geometry><cylinder><radius>{min(0.35, radius / 4):.2f}</radius><length>2</length></cylinder></geometry>{_material((0.42, 0.3, 0.2, 1))}</visual>
      <visual name='canopy'><pose>0 0 {2 + radius * 0.7:.2f} 0 0 0</pose><geometry><sphere><radius>{radius:.2f}</radius></sphere></geometry>{_material(rgba)}</visual>
      <collision name='collision'><pose>0 0 1 0 0 0</pose><geometry><cylinder><radius>{radius:.2f}</radius><length>2</length></cylinder></geometry></collision>
    </link></model>""")
            continue
        path = mesh_dir / f'{name}.stl'
        triangles += write_stl(path, _polys(poly), 0.0, max(height, 0.04))
        ring = list(orient(poly, 1.0).exterior.coords)[:-1] if isinstance(poly, Polygon) else []
        collision = ''
        if collides and ring:
            points = ''.join(f'<point>{x:.3f} {y:.3f}</point>' for x, y in ring)
            collision = f"<collision name='collision'><geometry><polyline>{points}<height>{max(height, 0.5):.2f}</height></polyline></geometry></collision>"
        obstacles.append(f"""
    <model name='{name}'><static>true</static><link name='link'>
      <visual name='visual'><geometry><mesh><uri>{escape(str(path))}</uri></mesh></geometry>{_material(rgba)}</visual>{collision}
    </link></model>""")

    task_colors = {t['id']: v.color for v in vehicles for t in v.tasks}
    markers = []
    for t in inst['tasks']:
        x, y = t['xy']
        rgba = _rgba(task_colors.get(t['id'], '#8e8e93'))
        markers.append(f"<visual name='task_{escape(str(t['id']))}'><pose>{x:.3f} {y:.3f} 0.35 0 0 0</pose>"
                       f"<geometry><cylinder><radius>0.18</radius><length>0.7</length></cylinder></geometry>{_material(rgba)}</visual>")
    dx, dy = inst['depot']
    w, h = maxx - minx + 60, maxy - miny + 60
    sdf = f"""<?xml version="1.0"?>
<sdf version="1.8">
  <world name="{world}">
    <physics name="fast" type="ignored">
      <max_step_size>0.004</max_step_size>
      <real_time_factor>{real_time_factor:g}</real_time_factor>
    </physics>
    <plugin filename="ignition-gazebo-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="ignition-gazebo-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="ignition-gazebo-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <scene><ambient>0.72 0.72 0.72 1</ambient><background>0.8 0.87 0.94 1</background><shadows>false</shadows><grid>false</grid></scene>
    <light type="directional" name="sun">
      <cast_shadows>false</cast_shadows>
      <pose>0 0 80 0 0 0</pose>
      <diffuse>0.95 0.94 0.9 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.35 0.25 -0.9</direction>
    </light>
    <model name="ground"><static>true</static><pose>{(minx + maxx) / 2:.3f} {(miny + maxy) / 2:.3f} -0.01 0 0 0</pose><link name="link">
      <collision name="collision"><geometry><plane><normal>0 0 1</normal><size>{w:.1f} {h:.1f}</size></plane></geometry></collision>
      <visual name="visual"><geometry><plane><normal>0 0 1</normal><size>{w:.1f} {h:.1f}</size></plane></geometry>{_material(GRASS)}</visual>
    </link></model>
    <model name="field"><static>true</static><link name="link">
      {''.join(visuals)}
    </link></model>
    <model name="depot"><static>true</static><pose>{dx:.3f} {dy:.3f} 0 0 0 0</pose><link name="link">
      <visual name="pad"><pose>0 0 0.03 0 0 0</pose><geometry><box><size>3 3 0.04</size></box></geometry>{_material((0.62, 0.62, 0.6, 1))}</visual>
      <visual name="pole"><pose>0 0 1.5 0 0 0</pose><geometry><cylinder><radius>0.04</radius><length>3</length></cylinder></geometry>{_material((0.3, 0.3, 0.32, 1))}</visual>
      <visual name="flag"><pose>0.3 0 2.75 0 0 0</pose><geometry><box><size>0.6 0.02 0.4</size></box></geometry>{_material((0.95, 0.75, 0.1, 1))}</visual>
    </link></model>
    <model name="tasks"><static>true</static><link name="link">
      {''.join(markers)}
    </link></model>{''.join(obstacles)}{''.join(_robot(v, i, speed) for i, v in enumerate(vehicles))}
  </world>
</sdf>
"""
    (out_dir / 'world.sdf').write_text(sdf)
    return {'world': world, 'sdf': str(out_dir / 'world.sdf'), 'triangles': triangles, 'speed_mps': speed,
            'real_time_factor': real_time_factor, 'bounds': [minx, miny, maxx, maxy], 'depot': [dx, dy],
            'vehicles': [{'name': v.name, 'label': v.label, 'color': v.color, 'start': list(v.start), 'path': v.path,
                          'tasks': v.tasks} for v in vehicles]}
