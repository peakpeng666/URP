"""Gateway side of the multi-vehicle field simulation: Gazebo world from a fleet plan, the ROS 2
session process (src/lab/ros/field_sim_session.py), its live state and the saved results."""
from __future__ import annotations

import json
import logging
import os
import shlex
import signal
import threading
from pathlib import Path

import shapely
from shapely.geometry import Polygon

from . import fieldworld, paths
from .jobs import new_id
from .services import ROS_SETUP, ManagedProcess, ServiceError, http_json

log = logging.getLogger('urp_lab.fieldsim')

FIELD_PORT = 4192
SCRIPT_REL = 'src/lab/ros/field_sim_session.py'
OBSTACLE_HEX = {'pond': '#4a8cdc', 'ditch': '#5a8dbd', 'building': '#a9a9ad', 'greenhouse': '#cfe3ea',
                'rock': '#8a857d', 'tree': '#2f7d3a'}


def _hex(rgba) -> str:
    return '#' + ''.join(f'{round(c * 255):02x}' for c in rgba[:3])


def _triangles(poly: Polygon) -> list[list[float]]:
    out = []
    for part in fieldworld._polys(poly.buffer(0)):
        for t in shapely.constrained_delaunay_triangles(part).geoms:
            out.extend([round(x, 3), round(y, 3)] for x, y in list(t.exterior.coords)[:3])
    return out


def marker_layers(inst: dict) -> tuple[list[dict], list[dict]]:
    """Filled field layers and outlines for the ROS view (visualization_msgs TRIANGLE_LIST / LINE_STRIP)."""
    boundary = Polygon(inst['boundary'])
    layers = [{'ns': 'field', 'color': _hex(fieldworld.SOIL), 'alpha': 1.0, 'z': 0.0, 'triangles': _triangles(boundary)}]
    outlines = [{'ns': 'boundary', 'color': '#5c4a36', 'width': 0.3, 'z': 0.04, 'points': [list(p) for p in boundary.exterior.coords]}]
    for plot in inst.get('plots', []):
        _, _, _, rgba = fieldworld.CROPS.get(plot.get('crop', ''), fieldworld.DEFAULT_CROP)
        poly = Polygon(plot['polygon'])
        layers.append({'ns': f"plot {plot.get('name') or plot.get('id')}", 'color': _hex(rgba), 'alpha': 0.75, 'z': 0.02,
                       'triangles': _triangles(poly)})
        outlines.append({'ns': 'plots', 'color': '#3f6b2a', 'width': 0.12, 'z': 0.05, 'points': [list(p) for p in poly.exterior.coords]})
    for o in inst.get('obstacles', []):
        layers.append({'ns': f"obstacle {o.get('kind', '')}", 'color': OBSTACLE_HEX.get(o.get('kind', ''), '#a9a9ad'),
                       'alpha': 0.9, 'z': 0.06, 'triangles': _triangles(Polygon(o['polygon']))})
    return layers, outlines


class FieldSimManager:
    def __init__(self, store, services, runtime: Path | None = None):
        self.store, self.services = store, services
        self.runtime = Path(runtime or paths.RUNTIME)
        self.url = f'http://127.0.0.1:{FIELD_PORT}'
        self.proc: ManagedProcess | None = None
        self.meta: dict | None = None
        self.last: dict | None = None
        self._lock = threading.Lock()
        services.field_sim = self

    @property
    def alive(self) -> bool:
        return self.proc is not None and self.proc.alive

    # -------------------------------------------------------------- start --
    def start(self, body: dict) -> dict:
        run = self.store.get_run(str(body.get('run_id') or ''))
        if not run:
            raise ServiceError(404, 'unknown_run', '没有这个运行记录')
        if run.get('problem_class') != 'fleet_routing' or run.get('state') != 'done' or not run.get('routes'):
            raise ServiceError(422, 'not_fleet_plan', '只有已完成的多车任务方案可以在 Gazebo 中执行')
        rtf = float(body.get('real_time_factor') or 4.0)
        if not 0.5 <= rtf <= 20:
            raise ServiceError(400, 'invalid_rtf', '仿真倍速需在 0.5–20 之间')
        with self._lock:
            if self.alive:
                raise ServiceError(409, 'fieldsim_running', '已有田间仿真在运行，请先停止')
            if self.services.sim_alive():
                raise ServiceError(409, 'sim_running', '机器人仿真会话正在运行，请先在仿真工作区停止它')
            status, _ = http_json('GET', f'{self.url}/state', timeout=0.5)
            if status is not None:
                raise ServiceError(409, 'port_busy', f'端口 {FIELD_PORT} 已被占用（可能是未关闭的田间仿真）')
            sid = new_id('field')
            out = self.runtime / 'fieldsim' / sid
            try:
                world = fieldworld.build(run['instance'], run['routes'], out, 'field_' + sid.rsplit('_', 1)[-1], rtf)
            except ValueError as exc:
                raise ServiceError(422, 'world_failed', str(exc)) from None
            routes = {r.get('vehicle_name'): r for r in run['routes']}
            for v in world['vehicles']:
                r = routes.get(v['label']) or {}
                v['planned_length_m'] = r.get('cost')
                v['planned_duration_s'] = r.get('duration_s')
            layers, outlines = marker_layers(run['instance'])
            metrics = run.get('metrics') or {}
            plan = {**world, 'session_id': sid, 'run_id': run['run_id'], 'scenario_id': run['scenario_id'],
                    'algorithm': (run.get('algorithm') or {}).get('name'), 'field_layers': layers, 'outlines': outlines,
                    'planned': {'makespan_s': metrics.get('makespan_s'), 'total_distance_m': metrics.get('total_distance_m')}}
            (out / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=1))
            args = ['--runtime', str(out), '--port', str(FIELD_PORT)]
            args += ['--gui'] if body.get('gui') else []
            args += ['--rviz'] if body.get('rviz') else []
            inner = f'source {ROS_SETUP} && exec bash setup/profile.sh simulation /usr/bin/python3 {SCRIPT_REL} ' + shlex.join(args)
            self.proc = ManagedProcess(f'fieldsim-{sid}', ['bash', '-c', inner], paths.REPO,
                                       self.runtime / 'logs' / f'fieldsim-{sid}.log', env=dict(os.environ))
            self.proc.start()
            self.meta = {'session_id': sid, 'run_id': run['run_id'], 'scenario_id': run['scenario_id'], 'world': world['world'],
                         'vehicles': len(world['vehicles']), 'real_time_factor': rtf, 'dir': str(out)}
            self.last = None
            log.info('field sim %s started for run %s (%d vehicles)', sid, run['run_id'], len(world['vehicles']))
        return self.state()

    # -------------------------------------------------------------- state --
    def state(self) -> dict:
        meta = self.meta or {}
        if self.alive:
            status, st = http_json('GET', f'{self.url}/state', timeout=0.8)
            if status == 200 and isinstance(st, dict):
                self.last = st
                return {**st, 'running': True}
            return {**meta, 'phase': 'starting', 'running': True, 'vehicles': [], 'components': {}, 'web': {},
                    'errors': [], 'warnings': []}
        if meta:
            st = dict(self.last or {**meta, 'vehicles': [], 'components': {}, 'web': {}, 'errors': [], 'warnings': []})
            st['running'] = False
            st['web'] = {}
            if st.get('phase') not in ('finished', 'failed'):
                st['phase'] = 'stopped'
            rc = self.proc.returncode if self.proc is not None else None
            if rc not in (0, None) and not (self.proc and self.proc.stop_requested):
                st.setdefault('errors', []).append(f'田间仿真进程退出，返回码 {rc}；见日志 fieldsim-{meta["session_id"]}')
            return st
        return {'phase': 'idle', 'running': False, 'vehicles': [], 'components': {}, 'web': {}, 'errors': [], 'warnings': []}

    def window(self, kind: str, on: bool) -> dict:
        if kind not in ('gui', 'rviz'):
            raise ServiceError(400, 'invalid_window', '窗口只能是 gui 或 rviz')
        if not self.alive:
            raise ServiceError(409, 'not_running', '田间仿真没有运行')
        http_json('POST', f'{self.url}/{kind}', timeout=3, json={'on': bool(on)})
        return self.state()

    # -------------------------------------------------------------- stop --
    def stop(self) -> dict:
        if not self.alive:
            return self.state()
        assert self.proc is not None
        self.proc.stop_requested = True
        self.state()  # keep the last live state for the stopped view
        http_json('POST', f'{self.url}/shutdown', timeout=3, json={})
        if not self.proc.wait(45):
            for sig, grace in ((signal.SIGINT, 10), (signal.SIGTERM, 6), (signal.SIGKILL, 4)):
                self.proc.signal_group(sig)
                if self.proc.wait(grace):
                    break
        log.info('field sim %s stopped rc=%s', (self.meta or {}).get('session_id'), self.proc.returncode)
        return self.state()

    def shutdown(self):
        if self.alive:
            log.info('gateway exit: stopping field simulation')
            self.stop()

    # ------------------------------------------------------------ results --
    def results(self, run_id: str | None = None) -> list[dict]:
        rows = []
        for path in sorted((self.runtime / 'fieldsim').glob('*/result.json'), reverse=True):
            try:
                r = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            if run_id and r.get('run_id') != run_id:
                continue
            rows.append({k: r.get(k) for k in ('session_id', 'run_id', 'scenario_id', 'algorithm', 'world', 'finished_utc',
                                               'state', 'metrics', 'real_time_factor', 'sim_time')}
                        | {'vehicles': [{k: v.get(k) for k in ('name', 'label', 'color', 'state', 'distance_m', 'duration_s',
                                                                'planned_length_m', 'planned_duration_s', 'tasks_done',
                                                                'tasks_total', 'cross_track_mean_m', 'cross_track_max_m')}
                                        for v in r.get('vehicles', [])]})
        return rows

    def result(self, session_id: str) -> dict:
        path = self.runtime / 'fieldsim' / session_id / 'result.json'
        if '/' in session_id or not path.is_file():
            raise ServiceError(404, 'unknown_result', '没有这次田间仿真的结果')
        return json.loads(path.read_text())
