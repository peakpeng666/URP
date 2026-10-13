"""Explicit full-source integration: no replacement data, no solver execution."""
import hashlib
import http.client
import json
import os
import tempfile
import threading
import unittest
from collections import Counter
from pathlib import Path
from backend.routes import import_vrptw
from backend.server import make_server
from backend.store import Store

class RealRouteIntegration(unittest.TestCase):
    def test_all_real_runs_vehicles_and_legacy_contracts(self):
        source=Path(os.environ['VRPTW_SOURCE_ROOT']).resolve()
        package_root=Path(os.environ['RESEARCH_CONSOLE_PACKAGE_ROOT']).resolve()
        report_path=os.environ.get('ROUTE_INTEGRATION_REPORT')
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir() if p.is_file()}
        rows=[json.loads(line) for line in (source/'routes.jsonl').read_text().splitlines()]
        inputs=json.loads((source/'inputs.json').read_text()); self.assertEqual(len(rows),240);self.assertEqual(len(inputs),48)
        with tempfile.TemporaryDirectory() as directory:
            db_path=Path(os.environ.get('ROUTE_INTEGRATION_DB',str(Path(directory)/'fresh.sqlite3')))
            self.assertFalse(db_path.exists(),'Use an independent new database')
            store=Store(db_path)
            for name in ['selector','budget','fleet','turns','bpp-history']:store.import_package(package_root/name)
            receipt=import_vrptw(store,source)
            self.assertFalse(receipt['reused']);self.assertEqual(receipt['revision'],1)
            self.assertTrue(import_vrptw(store,source)['reused'])
            server=make_server(store,package_root,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            requests=0
            def request(path,method='GET',payload=None):
                nonlocal requests
                requests+=1;c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
                c.request(method,path,None if payload is None else json.dumps(payload),{'Content-Type':'application/json'})
                r=c.getresponse();data=r.read();headers=dict(r.getheaders());status=r.status;c.close()
                return status,headers,data
            def get(path):
                code,_,data=request(path);self.assertEqual(code,200,(path,code,data[:500]));return json.loads(data)
            base='/api/experiments/vrptw-20261007'
            artifact_count=metric_count=vehicle_count=stop_count=0
            try:
                self.assertEqual(len(get('/api/experiments')['experiments']),6)
                for name in ['selector','budget','fleet','turns','bpp-history']:
                    d=get('/api/experiments/'+name);metric_count+=len(d['metrics'])
                    for a in d['artifacts']:
                        code,headers,data=request(f"/api/experiments/{name}/artifacts/{a['id']}")
                        self.assertEqual(code,200);self.assertEqual(hashlib.sha256(data).hexdigest(),a['sha256']);self.assertEqual(headers['X-Content-SHA256'],a['sha256']);artifact_count+=1
                    code,_,data=request('/api/import','POST',{'package':name});self.assertEqual(code,200);self.assertTrue(json.loads(data)['reused'])
                self.assertEqual(metric_count,690);self.assertEqual(artifact_count,28)
                items=[dict(experiment_id='selector',metric_id=f'family_holdout-{n}-delta_vs_subset_sbs') for n in [5,40]]
                code,_,data=request('/api/compare','POST',{'items':items});self.assertEqual(code,200);self.assertAlmostEqual(json.loads(data)['differences_from_first'][1],44.03148148148148)
                items=[dict(experiment_id='budget',metric_id=f'all-{n}-random_regret2-mean_relative_regret_pct') for n in [2500,10000]]
                self.assertEqual(request('/api/compare','POST',{'items':items})[0],409)
                self.assertEqual(request('/api/experiments/selector/runs')[0],404)
                d=get(base);self.assertEqual(d['routing']['run_count'],240)
                for a in d['artifacts']:
                    code,headers,data=request(f"{base}/artifacts/{a['id']}")
                    self.assertEqual(code,200);self.assertEqual(hashlib.sha256(data).hexdigest(),a['sha256'])
                self.assertEqual(len(get(base+'/instances')['instances']),48)
                listing=get(base+'/runs');self.assertEqual(listing['count'],240)
                states=Counter();methods={};missing=0
                for row in rows:
                    run_id=f"{row['instance']}.{row['method']}";run=get(base+'/runs/'+run_id)
                    self.assertEqual(run['routes'],row['routes']);self.assertEqual(run['source_status'],row['status'])
                    self.assertEqual(run['checker']['audit'],row['audit']);self.assertIsNone(run['solver_error'])
                    self.assertEqual(run['input']['id'],row['instance']);self.assertFalse(run['semantics']['is_road_network'])
                    self.assertEqual(run['full_service_success'],bool(row['audit'] and row['audit']['full_service_feasible']))
                    states[run['solution_status']]+=1
                    for v in range(run['input']['vehicles']):
                        response=get(base+'/runs/'+run_id+'/vehicles/'+str(v));vehicle=response['vehicle'];vehicle_count+=1
                        self.assertEqual(response['solution_status'],run['solution_status'])
                        if row['audit'] is None:
                            self.assertIsNone(vehicle);self.assertIsNone(run['unserved_task_ids']);self.assertIsNone(run['metrics']['full_oracle_objective']);continue
                        schedule=row['audit']['schedules'][v];self.assertEqual(vehicle['path_node_ids'],[0,*row['routes'][v],0]);self.assertEqual(vehicle['return_time'],schedule['return_time'])
                        load=0
                        for normalized,stop in zip(vehicle['stops'],schedule['stops']):
                            for key,value in stop.items():self.assertEqual(normalized[key],value)
                            self.assertEqual(normalized['load_before'],load);load+=stop['demand'];self.assertEqual(normalized['load_after'],load);self.assertIsNone(normalized['onboard_load']);stop_count+=1
                    if row['method'] in ['distance_first','time_window_first']:
                        m=methods.setdefault(row['method'],{'full_service_success':0,'served_unique':0});m['full_service_success']+=run['full_service_success'];m['served_unique']+=row['audit']['served_unique']
                self.assertEqual(states,{'feasible':137,'partial':53,'infeasible':15,'invalid':35})
                self.assertEqual(methods,{'distance_first':{'full_service_success':27,'served_unique':308},'time_window_first':{'full_service_success':31,'served_unique':310}})
                self.assertEqual(get(base+'/runs?solution_status=infeasible')['count'],15)
                self.assertEqual(get(base+'/runs?instance=G12_tight')['count'],5)
                for method,expected in [('distance_first',[7]),('time_window_first',[2,6])]:
                    r=get(base+'/runs/G12_tight.'+method);self.assertEqual(r['solution_status'],'partial');self.assertEqual(r['unserved_task_ids'],expected)
                self.assertEqual(request(base+'/runs','POST',{})[0],405)
            finally:server.shutdown();server.server_close();thread.join()
            self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir() if p.is_file()})
            report={'status':'PASS','database':str(db_path),'fresh_database':True,'idempotent':True,
                'transport':'actual loopback HTTP','http_requests':requests,'route_records':len(rows),
                'vehicle_responses':vehicle_count,'timetable_stops_checked':stop_count,'solution_status_counts':dict(states),
                'heuristic_counts':methods,'legacy_experiments':5,'legacy_metrics':metric_count,'legacy_artifacts_sha256_checked':artifact_count,
                'legacy_post_import_compare_compatible':True,'new_routes_post_rejected':True,'source_files_unchanged':True,
                'new_solver_runs':0,'source_python_executed':False,'browser_visual_tested':False,'deployed':False,'receipt':receipt}
            if report_path:Path(report_path).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':unittest.main()
