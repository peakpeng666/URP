"""URP Lab gateway: serves the panel (src/frontend/dist), /lab/api (CONTRACT §2), SSE and the /api archive proxy."""
from __future__ import annotations

import asyncio
import importlib
import logging
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote, urlsplit

import httpx
from fastapi import Body, FastAPI, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response, StreamingResponse
from starlette.background import BackgroundTask
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import paths
from . import events as sse
from .events import EventBus, LogFollower
from .jobs import JobManager, resolve_params
from .services import ARCHIVE_PORT, SIM_PORT, ServiceError, ServiceManager
from .simclient import SimClient
from .store import Store

log = logging.getLogger('urp_lab.gateway')

try:
    from . import __version__ as VERSION
except ImportError:  # pragma: no cover
    VERSION = '0.1.0'

MAX_BODY = 8 * 1024 * 1024
WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
LOCAL_HOSTS = {'127.0.0.1', 'localhost', '::1', '[::1]'}
HOP_BY_HOP = {'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailer', 'trailers',
              'transfer-encoding', 'upgrade', 'content-length'}
ASSET_CACHE = 'public, max-age=31536000, immutable'
CATALOG_TTL_S = 30.0


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({'error': code, 'message': message}, status_code=status)


@dataclass
class Config:
    port: int = 4100
    runtime: Path | None = None
    dist: Path | None = None
    archive_url: str = f'http://127.0.0.1:{ARCHIVE_PORT}'
    sim_port: int = SIM_PORT
    archive_autostart: bool = False
    concurrency: int | None = None
    grace_s: float = 2.0
    worker_command: list[str] | None = None
    background: bool = True          # service monitor + sim poller threads (tests may disable)
    extra_hosts: set[str] = field(default_factory=set)


class Lab:
    """Process-wide state shared by the endpoints."""

    def __init__(self, config: Config):
        self.config = config
        self.runtime = Path(config.runtime or paths.RUNTIME)
        self.dist = Path(config.dist or paths.FRONTEND_DIST)
        self.bus = EventBus()
        self.store = Store(self.runtime / 'lab.sqlite3')
        self.jobs = JobManager(self.store, self.bus, concurrency=config.concurrency, grace_s=config.grace_s,
                               command=config.worker_command)
        self.services = ServiceManager(self.bus, port=config.port, runtime=self.runtime,
                                       archive_url=config.archive_url, sim_port=config.sim_port, jobs=self.jobs)
        self.sim = SimClient(self.store, self.bus, self.services)
        self._catalog: tuple[float, list[dict]] | None = None
        self._catalog_lock = threading.Lock()
        self.shutdown_event = threading.Event()

    def start(self):
        self.jobs.start()
        if self.config.background:
            self.services.start_monitor()
            self.sim.start()
        if self.config.archive_autostart:
            try:
                self.services.start_archive()
            except Exception:
                log.exception('archive autostart failed')

    def shutdown(self):
        self.jobs.shutdown()
        self.services.shutdown()
        self.sim.stop()
        for run in self.store.active_sim_runs():
            self.sim._finish_local(run, 'failed', '网关退出时仿真会话已关闭，执行中断')
        self.store.close()

    def catalog(self) -> list[dict]:
        with self._catalog_lock:
            if self._catalog and time.monotonic() - self._catalog[0] < CATALOG_TTL_S:
                return self._catalog[1]
            items = core('solvers').catalog()
            self._catalog = (time.monotonic(), items)
            return items


def core(name: str):
    """Core modules are imported lazily so a broken module degrades one endpoint, not the gateway."""
    try:
        return importlib.import_module(f'urp_lab.{name}')
    except Exception as exc:
        log.exception('core module %s failed to import', name)
        raise ApiError(503, 'core_unavailable', f'核心模块 urp_lab.{name} 无法加载：{type(exc).__name__}: {exc}') from exc


def scenario_or_404(scenario_id: str) -> dict:
    if not isinstance(scenario_id, str) or not scenario_id:
        raise ApiError(400, 'invalid_request', '缺少 scenario_id')
    try:
        return core('scenarios').get_scenario(scenario_id)
    except KeyError:
        raise ApiError(404, 'unknown_scenario', f'没有场景 {scenario_id}') from None


def instance_for(scenario: dict, instance: Any) -> dict:
    if instance is None:
        return scenario['instance']
    if not isinstance(instance, dict):
        raise ApiError(400, 'invalid_instance', 'instance 须为 JSON 对象')
    try:
        return core('scenarios').validate_instance(scenario['problem_class'], instance)
    except ValueError as exc:
        raise ApiError(400, 'invalid_instance', str(exc)) from None


def attachment(data: bytes, media_type: str, filename: str) -> Response:
    ascii_name = filename.encode('ascii', 'replace').decode().replace('?', '_').replace('"', '')
    disposition = f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(filename)}'
    return Response(data, media_type=media_type, headers={'Content-Disposition': disposition, 'Cache-Control': 'no-store'})


def export_with(fn, *args) -> Response:
    try:
        data, media_type, filename = fn(*args)
    except ValueError as exc:
        raise ApiError(400, 'invalid_format', str(exc)) from None
    return attachment(data, media_type, filename)


class Guard:
    """Host allow-list (DNS rebinding), cross-origin write rejection, JSON-only POST and body size limit."""

    def __init__(self, app, extra_hosts: set[str] = frozenset()):
        self.app = app
        self.hosts = LOCAL_HOSTS | set(extra_hosts)

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            denied = self.check(scope)
            if denied is not None:
                await denied(scope, receive, send)
                return
        await self.app(scope, receive, send)

    def check(self, scope):
        headers = Headers(scope=scope)
        host = headers.get('host', '')
        if urlsplit(f'//{host}').hostname not in {h.strip('[]') for h in self.hosts}:
            return error(403, 'invalid_host', f'拒绝的 Host：{host}（网关只服务本机地址）')
        method = scope['method']
        if method not in WRITE_METHODS:
            return None
        origin = headers.get('origin')
        if origin is not None and (origin == 'null' or urlsplit(origin).netloc.lower() != host.lower()):
            return error(403, 'cross_origin', '拒绝跨源写入请求')
        length = headers.get('content-length')
        if length and length.isdigit() and int(length) > MAX_BODY:
            return error(413, 'payload_too_large', f'请求体超过 {MAX_BODY // (1024 * 1024)} MiB')
        if method != 'DELETE' and scope['path'].startswith('/lab/api/'):
            ctype = headers.get('content-type', '').split(';')[0].strip().lower()
            if ctype != 'application/json':
                return error(415, 'unsupported_media_type', 'POST 只接受 application/json')
        return None


def create_app(config: Config | None = None) -> FastAPI:
    config = config or Config()
    lab = Lab(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=2.0), trust_env=False)
        await run_in_threadpool(lab.start)
        log.info('gateway ready on 127.0.0.1:%s (runtime %s)', config.port, lab.runtime)
        try:
            yield
        finally:
            lab.bus.close()
            await app.state.http.aclose()
            await asyncio.to_thread(lab.shutdown)
            log.info('gateway stopped')

    app = FastAPI(title='URP Lab', version=VERSION, lifespan=lifespan, docs_url=None, redoc_url=None,
                  openapi_url='/lab/api/openapi.json')
    app.state.lab = lab
    app.add_middleware(Guard, extra_hosts=config.extra_hosts)

    @app.exception_handler(ApiError)
    async def _api_error(request, exc: ApiError):
        return error(exc.status, exc.code, exc.message)

    @app.exception_handler(ServiceError)
    async def _service_error(request, exc: ServiceError):
        return error(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation(request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        where = '.'.join(str(x) for x in first.get('loc', ()) if x != 'body')
        return error(400, 'invalid_request', f"请求格式不正确：{where or '正文'} {first.get('msg', '')}".strip())

    @app.exception_handler(StarletteHTTPException)
    async def _http(request, exc: StarletteHTTPException):
        codes = {404: ('not_found', '没有这个接口或资源'), 405: ('method_not_allowed', '不支持该请求方法')}
        code, message = codes.get(exc.status_code, ('http_error', str(exc.detail)))
        return error(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def _internal(request, exc: Exception):
        log.exception('unhandled error on %s %s', request.method, request.url.path)
        return error(500, 'internal_error', f'网关内部错误：{type(exc).__name__}: {exc}')

    def body_dict(payload: Any) -> dict:
        if payload is None:
            return {}
        if not isinstance(payload, dict):
            raise ApiError(400, 'invalid_request', '请求体须为 JSON 对象')
        return payload

    api = '/lab/api'

    # ------------------------------------------------------------ status --
    @app.get(f'{api}/health')
    def health():
        return {'status': 'ok', 'version': VERSION, 'executes_solvers': True}

    @app.post(f'{api}/shutdown', status_code=202)
    def shutdown_gateway():
        lab.shutdown_event.set()
        return {'accepted': True, 'message': '正在有序关闭求解、仿真与网关；日志保留'}

    @app.get(f'{api}/services')
    def services(refresh: bool = False):
        if refresh:
            lab.services.refresh_checks_async()
        return {'services': lab.services.services()}

    @app.post(f'{api}/services/{{sid}}/{{action}}')
    def service_action(sid: str, action: str, payload: Any = Body(None)):
        return {'services': lab.services.action(sid, action, body_dict(payload))}

    @app.get(f'{api}/logs')
    def logs():
        return {'logs': lab.services.logs()}

    @app.get(f'{api}/logs/{{name:path}}')
    def log_tail(name: str, tail: int = Query(400, ge=1, le=5000)):
        return lab.services.tail(name, tail)

    @app.get(f'{api}/events')
    async def events(request: Request, logs: str | None = None):
        followers = []
        for name in filter(None, (logs or '').split(',')):
            followers.append(LogFollower(name, lab.services.log_path(name)))
        initial = [('services', {'services': await run_in_threadpool(lab.services.services)}),
                   ('sim_state', lab.sim.current_state())]
        return StreamingResponse(sse.stream(lab.bus, initial, followers), media_type='text/event-stream',
                                 headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

    # --------------------------------------------------------- scenarios --
    @app.get(f'{api}/scenarios')
    def scenarios():
        return {'scenarios': core('scenarios').list_scenarios()}

    @app.get(f'{api}/scenarios/{{scenario_id}}')
    def scenario(scenario_id: str):
        return scenario_or_404(scenario_id)

    @app.post(f'{api}/scenarios', status_code=201)
    def import_scenario(payload: Any = Body(None)):
        module = core('scenarios')
        fn = getattr(module, 'import_scenario', None) or getattr(module, 'save_scenario', None)
        if fn is None:
            raise ApiError(501, 'not_implemented', '当前版本不支持导入场景')
        try:
            return fn(body_dict(payload))
        except ValueError as exc:
            raise ApiError(400, 'invalid_scenario', str(exc)) from None

    @app.get(f'{api}/maps/{{world}}.png')
    def map_png(world: str):
        try:
            data = core('scenarios').map_png(world)
        except (KeyError, FileNotFoundError, ValueError):
            raise ApiError(404, 'unknown_map', f'没有地图 {world}') from None
        return Response(data, media_type='image/png', headers={'Cache-Control': 'public, max-age=3600'})

    @app.get(f'{api}/maps/{{world}}')
    def map_meta(world: str):
        try:
            return core('scenarios').world_map(world)
        except (KeyError, FileNotFoundError, ValueError):
            raise ApiError(404, 'unknown_map', f'没有地图 {world}') from None

    # ------------------------------------------------------- algorithms --
    @app.get(f'{api}/algorithms')
    def algorithms():
        return {'algorithms': lab.catalog()}

    @app.post(f'{api}/recommend')
    def recommend(payload: Any = Body(None)):
        body = body_dict(payload)
        sc = scenario_or_404(body.get('scenario_id'))
        return core('recommend').recommend(sc, instance_for(sc, body.get('instance')))

    @app.post(f'{api}/solve', status_code=202)
    def solve(payload: Any = Body(None)):
        body = body_dict(payload)
        sc = scenario_or_404(body.get('scenario_id'))
        instance = instance_for(sc, body.get('instance'))
        requested = body.get('algorithms')
        if not isinstance(requested, list) or not requested:
            raise ApiError(400, 'invalid_request', 'algorithms 须为非空数组')
        if len(requested) > 24:
            raise ApiError(400, 'invalid_request', '一次最多提交 24 个算法')
        label = body.get('label')
        if label is not None and (not isinstance(label, str) or len(label) > 200):
            raise ApiError(400, 'invalid_request', 'label 须为不超过 200 字的字符串')
        catalog = {a['id']: a for a in lab.catalog()}
        resolved = []
        for item in requested:
            item = {'id': item} if isinstance(item, str) else item
            if not isinstance(item, dict) or not isinstance(item.get('id'), str):
                raise ApiError(400, 'invalid_request', 'algorithms 的每项须为 {"id": …, "params": {…}}')
            algo = catalog.get(item['id'])
            if algo is None:
                raise ApiError(400, 'unknown_algorithm', f"没有算法 {item['id']}")
            if sc['problem_class'] not in algo.get('problem_classes', []):
                raise ApiError(400, 'algorithm_not_applicable', f"{algo['name']} 不适用于 {sc['problem_class']} 场景")
            if not algo.get('available'):
                raise ApiError(409, 'algorithm_unavailable',
                               f"{algo['name']} 当前不可用：{algo.get('unavailable_reason') or '未说明'}")
            if item.get('params') is not None and not isinstance(item['params'], dict):
                raise ApiError(400, 'invalid_params', 'params 须为 JSON 对象')
            try:
                resolved.append((algo, resolve_params(algo, item.get('params'))))
            except ValueError as exc:
                raise ApiError(400, 'invalid_params', str(exc)) from None
        try:
            job_id, run_ids = lab.jobs.submit(sc, instance, resolved, label)
        except RuntimeError as exc:
            raise ApiError(503, 'shutting_down', str(exc)) from None
        return {'job_id': job_id, 'runs': run_ids}

    @app.get(f'{api}/jobs/{{job_id}}')
    def job(job_id: str):
        runs = lab.store.list_runs(job_id=job_id, limit=100)
        if not runs:
            raise ApiError(404, 'not_found', f'没有任务 {job_id}')
        return {'job_id': job_id, 'runs': [{'run_id': r['run_id'], 'algorithm_id': r['algorithm']['id'],
                                            'state': r['state'], 'status': r['status']} for r in runs]}

    @app.get(f'{api}/runs')
    def runs(scenario_id: str | None = None, limit: int = Query(100, ge=1, le=1000)):
        return {'runs': lab.store.list_runs(scenario_id=scenario_id, limit=limit)}

    def run_or_404(run_id: str) -> dict:
        sol = lab.store.get_run(run_id)
        if sol is None:
            raise ApiError(404, 'not_found', f'没有运行记录 {run_id}')
        return sol

    @app.get(f'{api}/runs/{{run_id}}')
    def run(run_id: str):
        return run_or_404(run_id)

    @app.post(f'{api}/runs/{{run_id}}/cancel')
    def cancel_run(run_id: str, payload: Any = Body(None)):
        run_or_404(run_id)
        return lab.jobs.cancel(run_id)

    @app.get(f'{api}/runs/{{run_id}}/export')
    def export_run(run_id: str, format: str = 'json'):
        return export_with(core('export').export_run, run_or_404(run_id), format)

    @app.post(f'{api}/compare/export')
    def export_compare(payload: Any = Body(None)):
        body = body_dict(payload)
        ids = body.get('run_ids')
        if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids):
            raise ApiError(400, 'invalid_request', 'run_ids 须为非空字符串数组')
        return export_with(core('export').export_compare, [run_or_404(i) for i in ids], body.get('format', 'csv'))

    # ------------------------------------------------------- simulation --
    @app.get(f'{api}/sim/state')
    def sim_state():
        return lab.sim.current_state()

    @app.post(f'{api}/sim/session', status_code=202)
    def sim_start(payload: Any = Body(None)):
        lab.services.start_sim(body_dict(payload))
        return lab.sim.current_state()

    @app.delete(f'{api}/sim/session', status_code=202)
    def sim_stop():
        if lab.services.sim_alive() and not lab.services._busy.get('sim'):
            lab.services.stop_sim_async()
            time.sleep(0.05)
        return lab.sim.current_state()

    @app.post(f'{api}/sim/gui')
    def sim_gui(payload: Any = Body(None)):
        return lab.sim.set_window('gui', bool(body_dict(payload).get('on')))

    @app.post(f'{api}/sim/rviz')
    def sim_rviz(payload: Any = Body(None)):
        return lab.sim.set_window('rviz', bool(body_dict(payload).get('on')))

    @app.post(f'{api}/sim/runs', status_code=202)
    def sim_run_start(payload: Any = Body(None)):
        body = body_dict(payload)
        sol = run_or_404(body.get('run_id') or '')
        try:
            sc = sol.get('scenario_snapshot') or core('scenarios').get_scenario(sol['scenario_id'])
        except KeyError:
            raise ApiError(422, 'not_simulatable', f"运行所属场景 {sol['scenario_id']} 已不存在") from None
        return lab.sim.submit(sol, sc, body.get('mode') or 'follow_path', autostart=bool(body.get('autostart')),
                              gui=body.get('gui'), rviz=body.get('rviz'))

    @app.get(f'{api}/sim/runs')
    def sim_runs(run_id: str | None = None, limit: int = Query(100, ge=1, le=1000)):
        return {'sim_runs': lab.store.list_sim_runs(run_id=run_id, limit=limit)}

    def sim_run_or_404(sim_run_id: str) -> dict:
        run = lab.sim.get_run(sim_run_id)
        if run is None:
            raise ApiError(404, 'not_found', f'没有仿真运行 {sim_run_id}')
        return run

    @app.get(f'{api}/sim/runs/{{sim_run_id}}')
    def sim_run(sim_run_id: str):
        return sim_run_or_404(sim_run_id)

    @app.post(f'{api}/sim/runs/{{sim_run_id}}/cancel')
    def sim_run_cancel(sim_run_id: str, payload: Any = Body(None)):
        return lab.sim.cancel(sim_run_id)

    @app.get(f'{api}/sim/runs/{{sim_run_id}}/export')
    def sim_run_export(sim_run_id: str, format: str = 'json'):
        record = sim_run_or_404(sim_run_id)
        if format == 'json':
            record = {**record, 'planning_solution': run_or_404(record['run_id'])}
        return export_with(core('export').export_sim_run, record, format)

    @app.api_route(f'{api}/{{rest:path}}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
    def api_not_found(rest: str):
        raise ApiError(404, 'not_found', f'没有接口 /lab/api/{rest}')

    # ------------------------------------------------------ archive proxy --
    @app.api_route('/api/{rest:path}', methods=['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
    async def archive_proxy(request: Request, rest: str):
        url = f'{config.archive_url}/api/{rest}'
        if request.url.query:
            url += f'?{request.url.query}'
        headers = [(k, v) for k, v in request.headers.raw if k.decode('latin-1').lower() not in HOP_BY_HOP]
        client: httpx.AsyncClient = request.app.state.http
        upstream = client.build_request(request.method, url, headers=headers, content=await request.body())
        try:
            resp = await client.send(upstream, stream=True)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            return error(503, 'archive_offline', '档案后端未运行，可在概览页启动')
        except httpx.HTTPError as exc:
            return error(502, 'archive_error', f'档案后端请求失败：{type(exc).__name__}')
        out = StreamingResponse(resp.aiter_raw(), status_code=resp.status_code, background=BackgroundTask(resp.aclose))
        out.raw_headers = [(k, v) for k, v in resp.headers.raw if k.decode('latin-1').lower() not in HOP_BY_HOP - {'content-length'}]
        return out

    # ------------------------------------------------------------ static --
    def static_file(rel: str) -> Path | None:
        parts = PurePosixPath(rel).parts
        if not parts or any(p in ('..', '.') or p.startswith('/') for p in parts):
            return None
        path = lab.dist.joinpath(*parts)
        return path if path.is_file() else None

    def index() -> Response:
        page = lab.dist / 'index.html'
        if not page.is_file():
            return HTMLResponse('<!doctype html><meta charset="utf-8"><title>URP 科研面板</title>'
                                '<p>前端尚未构建。请在项目根目录运行 <code>bash setup/run.sh lab-setup</code>，'
                                '或 <code>bash setup/run.sh build</code>，然后刷新。</p>', status_code=503)
        return FileResponse(page, headers={'Cache-Control': 'no-cache'})

    @app.get('/', include_in_schema=False)
    def root():
        return index()

    @app.get('/data/{rest:path}', include_in_schema=False)
    def data(rest: str):
        path = static_file(f'data/{rest}')
        if path is None:
            return error(404, 'not_found', f'无历史数据：/data/{rest} 不存在（历史实验数据未恢复）')
        return FileResponse(path, headers={'Cache-Control': 'no-cache'})

    @app.get('/{rest:path}', include_in_schema=False)
    def static(request: Request, rest: str):
        path = static_file(rest)
        if path is not None:
            cache = ASSET_CACHE if rest.startswith('assets/') else 'no-cache'
            return FileResponse(path, headers={'Cache-Control': cache})
        if 'text/html' in request.headers.get('accept', '') and not rest.startswith('assets/'):
            return index()
        return error(404, 'not_found', f'没有文件 /{rest}')

    return app
