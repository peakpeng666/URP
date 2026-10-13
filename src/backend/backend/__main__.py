from __future__ import annotations
import argparse,json
from pathlib import Path
from .store import Store,StoreError
from .server import make_server
from .routes import import_vrptw
from .mature_routes import import_route_archive

def main():
    p=argparse.ArgumentParser(description='本地科研记录导入与查询，不运行实验')
    p.add_argument('--db',type=Path,default=Path('backend_data/research.sqlite3'))
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('import');a.add_argument('package',type=Path)
    a=sub.add_parser('import-vrptw');a.add_argument('source',type=Path);a.add_argument('--id',default='vrptw-20261007')
    a=sub.add_parser('import-routes');a.add_argument('source',type=Path);a.add_argument('--format',required=True,choices=['vrptw-frozen-v1','vrptw-mature-solver-v1','vrptw-archived-solomon-v1','vrptw-solver-portfolio-v1']);a.add_argument('--id');a.add_argument('--input-dir',type=Path)
    sub.add_parser('list')
    a=sub.add_parser('bootstrap');a.add_argument('--package-root',type=Path,default=Path('packages'))
    a=sub.add_parser('get');a.add_argument('id');a.add_argument('--revision',type=int)
    a=sub.add_parser('compare');a.add_argument('items',help='JSON数组，每项含experiment_id/metric_id')
    a=sub.add_parser('serve');a.add_argument('--port',type=int,default=4180);a.add_argument('--import-root',type=Path,default=Path('packages'))
    a=sub.add_parser('artifact');a.add_argument('id');a.add_argument('artifact_id');a.add_argument('--output',type=Path,required=True);a.add_argument('--revision',type=int)
    args=p.parse_args();store=Store(args.db)
    if args.command=='serve':
        server=make_server(store,args.import_root,args.port);print(f'Local research API: http://127.0.0.1:{server.server_port}',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()
        return
    if args.command=='bootstrap':result=[store.import_package(p.parent) for p in sorted(args.package_root.glob('*/experiment.json'))]
    elif args.command=='import':result=store.import_package(args.package)
    elif args.command=='import-vrptw':result=import_vrptw(store,args.source,args.id)
    elif args.command=='import-routes':result=import_route_archive(store,args.source,args.format,args.id,args.input_dir)
    elif args.command=='list':result=store.list()
    elif args.command=='get':result=store.get(args.id,args.revision)
    elif args.command=='compare':result=store.compare(json.loads(args.items))
    else:
        result,data=store.artifact(args.id,args.artifact_id,args.revision)
        with args.output.open('xb') as out:out.write(data)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
    try:main()
    except StoreError as e:raise SystemExit(f'{e.code}: {e}')
