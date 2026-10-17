"""Loopback JSON API for immutable records and bounded, serial CVRP jobs."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import sqlite3
import threading
from urllib.parse import urlsplit, parse_qs, unquote, quote

from .jobs import JobManager
from .store import Store, StoreError, MEDIA_TYPE, canonical, parse_json, revision_number, safe_path
from .routes import RouteReader
from .route_comparison import compare_routes
from .route_scene import route_scene

MAX_REQUEST_BYTES = 1024 * 1024


class ResearchHTTPServer(ThreadingHTTPServer):
    """Bound active request threads and finish owned jobs on server close."""
    daemon_threads = False

    def __init__(self, address, handler):
        self.jobs = None
        self._slots = threading.BoundedSemaphore(16)
        super().__init__(address, handler)

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            body = b'{"error":"server_busy","message":"Too many active requests."}'
            try:
                request.settimeout(1)
                request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nContent-Type: application/json\r\n'
                                + b'Content-Length: '+str(len(body)).encode()+b'\r\nConnection: close\r\n\r\n'+body)
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()

    def server_close(self):
        try:
            super().server_close()
        finally:
            if self.jobs:
                self.jobs.close()


def make_server(store: Store, import_root: Path, port=4180):
    import_root = Path(import_root).resolve()

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *args):
            pass

        def send_bytes(self, data, status=200, media='application/json; charset=utf-8', headers=None):
            if not isinstance(media, str) or not MEDIA_TYPE.fullmatch(media):
                raise StoreError('invalid_media_type', '存储产物的媒体类型无效，停止下载。', 409)
            self.send_response(status)
            self.send_header('Content-Type', media)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(data)

        def json(self, value, status=200):
            self.send_bytes(canonical(value).encode(), status)

        def do_GET(self): self.handle_api('GET')
        def do_POST(self): self.handle_api('POST')
        def do_PUT(self): self.handle_api('PUT')
        def do_PATCH(self): self.handle_api('PATCH')
        def do_DELETE(self): self.handle_api('DELETE')
        def do_HEAD(self): self.handle_api('HEAD')
        def do_OPTIONS(self): self.handle_api('OPTIONS')

        def local_request(self):
            hosts = self.headers.get_all('Host', [])
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if self.server.server_port == 80:
                allowed |= {'127.0.0.1', 'localhost'}
            if len(hosts) != 1 or hosts[0].lower() not in allowed:
                raise StoreError('nonlocal_host', '本地API仅接受明确的本机Host与服务端口。', 403)
            origins = self.headers.get_all('Origin', [])
            if len(origins) > 1:
                raise StoreError('cross_origin', '本地API不接受多个Origin。', 403)
            if origins:
                origin = urlsplit(origins[0])
                if (origin.scheme != 'http' or origin.netloc.lower() != hosts[0].lower()
                        or origin.path or origin.query or origin.fragment):
                    raise StoreError('cross_origin', '本地API仅接受同源请求。', 403)
            if self.headers.get('Sec-Fetch-Site') == 'cross-site':
                raise StoreError('cross_origin', '本地API不接受跨站请求。', 403)

        def body(self):
            if self.headers.get('Transfer-Encoding') is not None:
                raise StoreError('invalid_request', '请求不支持Transfer-Encoding。')
            lengths = self.headers.get_all('Content-Length', [])
            if len(lengths) != 1 or not re.fullmatch(r'[0-9]+', lengths[0]):
                raise StoreError('invalid_request', '请求需要唯一有效的Content-Length。')
            length = int(lengths[0])
            if not 1 <= length <= MAX_REQUEST_BYTES:
                raise StoreError('request_size', 'JSON请求大小须在1字节到1MiB之间。', 413)
            if self.headers.get_content_type() != 'application/json':
                raise StoreError('content_type', 'POST仅接受application/json。', 415)
            data = self.rfile.read(length)
            if len(data) != length:
                raise StoreError('invalid_request', '请求正文未完整传输。')
            value = parse_json(data, 'invalid_request')
            if not isinstance(value, dict):
                raise StoreError('invalid_request', '请求正文必须是JSON对象。')
            return value

        def handle_api(self, method):
            try:
                self.local_request()
                url = urlsplit(self.path)
                if url.scheme or url.netloc or url.fragment:
                    raise StoreError('invalid_request', '请求需要本地相对API路径。')
                parts = [unquote(p, errors='strict') for p in url.path.split('/') if p]
                query = parse_qs(url.query, keep_blank_values=True, max_num_fields=16)
                scene_path = (len(parts) == 7 and parts[:3] == ['api','v1','experiments']
                              and parts[4] == 'runs' and parts[6] == 'route-scene')
                allowed_query = set()
                if scene_path:
                    allowed_query = {'revision'}
                elif parts == ['api','route-comparison']:
                    allowed_query = {'experiments','revisions','instance'}
                elif parts == ['api','jobs']:
                    allowed_query = {'limit','offset'} if method == 'GET' else set()
                elif len(parts) >= 3 and parts[:2] == ['api','experiments']:
                    allowed_query = {'revision'}
                    if len(parts) == 4 and parts[3] == 'runs':
                        allowed_query |= {'instance','solution_status'}
                if set(query)-allowed_query or any(len(values) != 1 or not values[0] for values in query.values()):
                    raise StoreError('invalid_query', '查询字段未知、重复或为空。')
                query = {key: values[0] for key, values in query.items()}
                revision = revision_number(int(query['revision'])) if 'revision' in query else None
                if scene_path:
                    if method != 'GET':
                        raise StoreError('read_only_routes', '路线场景仅支持GET。', 405)
                    return self.json(route_scene(store, parts[3], parts[5], revision))
                route_path = (len(parts) >= 4 and parts[:2] == ['api','experiments']
                              and parts[3] in {'runs','instances'})
                if (route_path or parts == ['api','route-comparison']) and method != 'GET':
                    raise StoreError('read_only_routes', '历史路线接口仅支持GET。', 405)
                if method == 'POST' and parts in (['api','import'], ['api','compare'], ['api','jobs']):
                    payload = self.body()
                    if parts == ['api','import']:
                        if set(payload) != {'package'}:
                            raise StoreError('invalid_request', '导入请求仅接受package字段。')
                        return self.json(store.import_package(safe_path(import_root, payload['package'])))
                    if parts == ['api','compare']:
                        if set(payload) != {'items'}:
                            raise StoreError('invalid_request', '指标比较仅接受items字段。')
                        return self.json(store.compare(payload['items']))
                    return self.json(self.server.jobs.submit(payload), 202)
                if method not in {'GET','POST'}:
                    raise StoreError('method_not_allowed', '此接口不支持该方法。', 405)
                if method == 'GET':
                    if parts == ['api','health']:
                        catalog = self.server.jobs.algorithms()
                        enabled = any(item['available'] for item in catalog['algorithms'])
                        return self.json({'status':'ok', 'mode':('local_import_query_and_cvrp_jobs' if enabled else 'local_import_query'),
                            'executes_experiments': enabled, 'execution_scope':'bounded_cvrp_engineering_validation' if enabled else None,
                            'algorithms': catalog['algorithms'], 'constraints':catalog['constraints'],
                            'job_source_sha256':catalog['source_sha256']})
                    if parts == ['api','algorithms']:
                        return self.json(self.server.jobs.algorithms())
                    if parts == ['api','jobs']:
                        return self.json(self.server.jobs.list(int(query.get('limit',100)), int(query.get('offset',0))))
                    if len(parts) == 3 and parts[:2] == ['api','jobs']:
                        return self.json(self.server.jobs.get(parts[2]))
                    if parts == ['api','experiments']:
                        return self.json({'experiments':store.list()})
                    if parts == ['api','route-comparison']:
                        names = query.get('experiments','').split(',')
                        revisions = query['revisions'].split(',') if 'revisions' in query else [None]*len(names)
                        if len(revisions) != len(names):
                            raise StoreError('invalid_revision', 'revisions数量必须与experiments一致。')
                        selections = [{'experiment_id':name, 'revision':revision_number(int(rev)) if rev is not None else None}
                                      for name, rev in zip(names,revisions)]
                        return self.json(compare_routes(store, selections, query.get('instance')))
                    if route_path:
                        reader = RouteReader(store, parts[2], revision)
                        if len(parts) == 4 and parts[3] == 'instances': return self.json(reader.instances())
                        if len(parts) == 4 and parts[3] == 'runs': return self.json(reader.runs(query.get('instance'),query.get('solution_status')))
                        if len(parts) == 5 and parts[3] == 'runs': return self.json(reader.run(parts[4]))
                        if len(parts) == 7 and parts[3] == 'runs' and parts[5] == 'vehicles':
                            return self.json(reader.vehicle(parts[4], int(parts[6])))
                    if len(parts) == 3 and parts[:2] == ['api','experiments']:
                        return self.json(store.get(parts[2], revision))
                    if len(parts) == 5 and parts[:2] == ['api','experiments'] and parts[3] == 'artifacts':
                        ref, data = store.artifact(parts[2], parts[4], revision)
                        return self.send_bytes(data, media=ref['media_type'], headers={
                            'X-Content-SHA256':ref['sha256'],
                            'Content-Disposition':"attachment; filename*=UTF-8''"+quote(ref['filename'],safe='')})
                raise StoreError('not_found', '没有这个接口。', 404)
            except (BrokenPipeError, ConnectionResetError):
                pass
            except StoreError as exc:
                self.json({'error':exc.code, 'message':str(exc)}, exc.status)
            except TimeoutError:
                self.json({'error':'request_timeout','message':'请求读取超时。'}, 408)
            except (KeyError, TypeError, ValueError, OverflowError, AttributeError, IndexError, RecursionError):
                self.json({'error':'invalid_request', 'message':'请求字段或JSON无效。'}, 400)
            except sqlite3.Error:
                self.json({'error':'database_unavailable','message':'数据库暂时不可用，请稍后查询任务状态。'}, 503)
            except OSError:
                self.json({'error':'io_error','message':'无法读取本地数据。'}, 500)

    server = ResearchHTTPServer(('127.0.0.1',port), Handler)
    try:
        server.jobs = JobManager(store)
    except BaseException:
        server.server_close()
        raise
    return server
