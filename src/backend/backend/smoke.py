"""Run the real-record HTTP loop once, then stop the local server. No solver runs."""
from __future__ import annotations
import argparse, hashlib, http.client, json, threading
from pathlib import Path
from .store import Store
from .server import make_server

def run(package_root:Path,db:Path):
    store=Store(db);server=make_server(store,package_root,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();events=[]
    def request(method,path,payload=None):
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10);body=json.dumps(payload) if payload is not None else None
        conn.request(method,path,body,{'Content-Type':'application/json'});r=conn.getresponse();data=r.read();headers=dict(r.getheaders());status=r.status;conn.close();return status,headers,data
    try:
        imported=[]
        for package in ['selector','budget','fleet','turns','bpp-history']:
            code,_,data=request('POST','/api/import',{'package':package});assert code==200,(code,data);receipt=json.loads(data);imported.append(receipt)
            code,_,data=request('GET','/api/experiments/'+receipt['id']);d=json.loads(data);assert code==200 and d['status']=='completed'
            item={'experiment_id':d['id'],'status':d['status'],'counts':d['counts'],'failure_reason':d['failure_reason'],'failures':d.get('failures'),'metrics':len(d['metrics']),'artifacts':len(d['artifacts'])}
            # Download every attached original file through HTTP and independently hash it.
            for a in d['artifacts']:
                code,headers,raw=request('GET',f"/api/experiments/{d['id']}/artifacts/{a['id']}");assert code==200
                assert hashlib.sha256(raw).hexdigest()==a['sha256']==headers['X-Content-SHA256']
            events.append(item)
        # Retry imports through the same public endpoint: no duplicate revision is created.
        for package in ['selector','budget']:
            code,_,data=request('POST','/api/import',{'package':package});assert code==200 and json.loads(data)['reused']
        items=[{'experiment_id':'selector','metric_id':f'family_holdout-{n}-delta_vs_subset_sbs'} for n in [5,40]]
        code,_,data=request('POST','/api/compare',{'items':items});assert code==200;comparison=json.loads(data)
        assert abs(comparison['differences_from_first'][1]-44.03148148148148)<1e-9
        items=[{'experiment_id':'budget','metric_id':f'all-{n}-random_regret2-mean_relative_regret_pct'} for n in [2500,10000]]
        code,_,data=request('POST','/api/compare',{'items':items});assert code==409;incomparable=json.loads(data);assert incomparable['error']=='incomparable_metrics'
        return {'status':'PASS','transport':'actual loopback HTTP + SQLite','experiments':events,'import_receipts':imported,'same_contract_comparison':comparison,'cross_budget_refused':incomparable,'repeated_imports_idempotent':True,'artifact_download_hashes_passed':sum(e['artifacts'] for e in events),'new_experiments_executed':0,'database':str(db)}
    finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--package-root',type=Path,default=Path('packages'));p.add_argument('--db',type=Path,default=Path('backend_data/research.sqlite3'));p.add_argument('--report',type=Path,default=Path('artifacts/backend-20261007/smoke.json'));args=p.parse_args()
    result=run(args.package_root,args.db);args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':result['status'],'experiments':len(result['experiments']),'artifacts_verified':result['artifact_download_hashes_passed']}))
