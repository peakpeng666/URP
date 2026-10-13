"""Loopback-only JSON API backed by the same import/query functions as the CLI."""
from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote, quote
from .store import Store, StoreError, safe_path
from .routes import RouteReader
from .route_comparison import compare_routes

def make_server(store: Store, import_root: Path, port=4180):
    import_root=Path(import_root).resolve()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def json(self,value,status=200):
            data=json.dumps(value,ensure_ascii=False,allow_nan=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_GET(self):self.handle_api('GET')
        def do_POST(self):self.handle_api('POST')
        def handle_api(self,method):
            try:
                u=urlparse(self.path);parts=[unquote(p) for p in u.path.split('/') if p];query=parse_qs(u.query)
                revision=int(query['revision'][0]) if 'revision' in query else None
                if revision is not None and revision < 1:raise StoreError('invalid_revision','版本必须为正整数。')
                if len(parts)>=4 and parts[:2]==['api','experiments'] and parts[3] in {'runs','instances'} and method!='GET':
                    raise StoreError('read_only_routes','路线数据接口仅支持GET；不能运行求解。',405)
                if parts==['api','route-comparison'] and method!='GET':
                    raise StoreError('read_only_routes','路线比较接口仅支持GET。',405)
                if method=='POST':
                    if self.headers.get_content_type()!='application/json':raise StoreError('content_type','POST仅接受application/json。',415)
                    origin=self.headers.get('Origin')
                    if origin and urlparse(origin).netloc!=self.headers.get('Host'):raise StoreError('cross_origin','本地API不接受跨源写入。',403)
                    length=int(self.headers.get('Content-Length','0'))
                    if length<1 or length>1024*1024:raise StoreError('request_size','JSON请求大小须在1字节到1MiB之间。',413)
                    payload=json.loads(self.rfile.read(length))
                    if parts==['api','import']:
                        package=safe_path(import_root,payload['package']);return self.json(store.import_package(package))
                    if parts==['api','compare']:return self.json(store.compare(payload['items']))
                if method=='GET':
                    if parts==['api','route-comparison']:
                        names=query.get('experiments',[''])[0].split(',')
                        revisions=query['revisions'][0].split(',') if 'revisions' in query else [None]*len(names)
                        if len(revisions)!=len(names):raise StoreError('invalid_revision','revisions数量必须与experiments一致。')
                        selections=[{'experiment_id':name,'revision':int(rev) if rev is not None else None} for name,rev in zip(names,revisions)]
                        if any(s['revision'] is not None and s['revision']<1 for s in selections):raise StoreError('invalid_revision','版本必须为正整数。')
                        return self.json(compare_routes(store,selections,query.get('instance',[None])[0]))
                    if parts==['api','health']:return self.json({'status':'ok','mode':'local_import_query','executes_experiments':False})
                    if parts==['api','experiments']:return self.json({'experiments':store.list()})
                    if len(parts)>=4 and parts[:2]==['api','experiments'] and parts[3] in {'runs','instances'}:
                        reader=RouteReader(store,parts[2],revision)
                        if len(parts)==4 and parts[3]=='instances':return self.json(reader.instances())
                        if len(parts)==4 and parts[3]=='runs':return self.json(reader.runs(query.get('instance',[None])[0],query.get('solution_status',[None])[0]))
                        if len(parts)==5 and parts[3]=='runs':return self.json(reader.run(parts[4]))
                        if len(parts)==7 and parts[3]=='runs' and parts[5]=='vehicles':return self.json(reader.vehicle(parts[4],int(parts[6])))
                    if len(parts)==3 and parts[:2]==['api','experiments']:return self.json(store.get(parts[2],revision))
                    if len(parts)==5 and parts[:2]==['api','experiments'] and parts[3]=='artifacts':
                        ref,data=store.artifact(parts[2],parts[4],revision);self.send_response(200);self.send_header('Content-Type',ref['media_type']);self.send_header('Content-Length',str(len(data)));self.send_header('X-Content-SHA256',ref['sha256']);self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(ref['filename']));self.end_headers();self.wfile.write(data);return
                raise StoreError('not_found','没有这个接口。',404)
            except StoreError as e:self.json({'error':e.code,'message':str(e)},e.status)
            except (KeyError,TypeError,ValueError) as e:self.json({'error':'invalid_request','message':'请求字段或JSON无效。'},400)
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)
