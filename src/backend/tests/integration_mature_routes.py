"""Opt-in original + mature archive HTTP integration, with no experiment execution."""
import hashlib
import http.client
import json
import os
import tempfile
import threading
import unittest
from collections import Counter
from pathlib import Path
from backend.mature_routes import import_mature
from backend.routes import import_vrptw
from backend.server import make_server
from backend.store import Store

class MatureArchiveIntegration(unittest.TestCase):
    def test_real_336_runs_and_budget_comparison(self):
        old=Path(os.environ['VRPTW_SOURCE_ROOT']);new=Path(os.environ['MATURE_VRPTW_SOURCE_ROOT'])
        def snapshot(p):return {str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
        before={str(p):snapshot(p) for p in [old,new]}
        source=[json.loads(line) for line in (new/'results.jsonl').read_text().splitlines()]
        self.assertEqual(len(source),96)
        with tempfile.TemporaryDirectory() as directory:
            db=Path(os.environ.get('MATURE_INTEGRATION_DB',str(Path(directory)/'fresh.sqlite3')));self.assertFalse(db.exists())
            store=Store(db);oldreceipt=import_vrptw(store,old);receipt=import_mature(store,new)
            self.assertEqual(oldreceipt['fingerprint'],'b98ff9710eda1bf5bd77997767d8b6d765e780e962e850abdd8ed40eb649393e')
            self.assertTrue(import_mature(store,new)['reused']);self.assertTrue(import_vrptw(store,old)['reused'])
            server=make_server(store,old,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();requests=0
            def request(path,method='GET'):
                nonlocal requests
                requests+=1;c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=15);c.request(method,path);r=c.getresponse();data=r.read();status=r.status;headers=dict(r.getheaders());c.close();return status,headers,data
            def get(path):
                status,_,data=request(path);self.assertEqual(status,200,(path,status,data[:200]));return json.loads(data)
            base='/api/experiments/vrptw-mature-20261007';states=Counter();vehicles=stops=0
            try:
                self.assertEqual(get('/api/experiments/vrptw-20261007/runs')['count'],240)
                self.assertEqual(get(base+'/runs')['count'],96)
                self.assertEqual(get(base+'/runs?solution_status=no_solution')['count'],30)
                self.assertEqual(get(base+'/runs?solution_status=infeasible')['count'],0)
                self.assertEqual(get(base+'/runs?solution_status=invalid')['count'],0)
                self.assertEqual(len(get(base+'/instances')['instances']),48)
                for row in source:
                    run=get(base+'/runs/'+row['run_id']);states[run['solution_status']]+=1
                    self.assertEqual(run['routes'],row['routes']);self.assertEqual(run['provenance']['source_run_id'],row['run_id'])
                    self.assertEqual(run['budget']['value'],row['budget_ms']);self.assertEqual(run['solver_status']['name'],row['ortools_status_name'])
                    self.assertFalse(run['semantics']['is_road_network']);self.assertEqual(run['execution_status'],'completed')
                    for vehicle in range(2):
                        v=get(base+'/runs/'+row['run_id']+'/vehicles/'+str(vehicle));vehicles+=1
                        if row['routes'] is None:
                            self.assertIsNone(v['vehicle']);self.assertEqual(v['solution_status'],'no_solution');self.assertFalse(run['full_service_success']);self.assertIsNone(run['checker']['audit']);continue
                        self.assertTrue(run['checker']['recomputed_at_import']);schedule=v['vehicle'];saved=row['audit']['schedules'][vehicle]
                        self.assertEqual(schedule['route'],saved['route']);self.assertAlmostEqual(schedule['return_time'],saved['return_time']);load=0
                        for actual,original in zip(schedule['stops'],saved['stops']):
                            for key,value in original.items():self.assertAlmostEqual(actual[key],value)
                            self.assertEqual(actual['load_before'],load);load+=original['demand'];self.assertEqual(actual['load_after'],load);self.assertIsNone(actual['onboard_load']);stops+=1
                self.assertEqual(states,{'feasible':66,'no_solution':30});self.assertEqual(stops,462)
                comparison=get('/api/route-comparison?experiments=vrptw-20261007,vrptw-mature-20261007')
                self.assertEqual(comparison['row_count'],336);self.assertEqual(comparison['unique_input_count'],48);self.assertEqual(len(comparison['groups']),7);self.assertFalse(comparison['same_known_budget'])
                self.assertEqual(len({(r['experiment_id'],r['revision'],r['run_id']) for r in comparison['rows']}),336)
                newgroups=[g for g in comparison['groups'] if g['algorithm']['id']=='ortools_routing']
                self.assertEqual(sorted((g['budget']['value'],g['run_count'],g['full_service_success_count']) for g in newgroups),[(250,48,33),(1000,48,33)])
                for r in comparison['rows']:
                    if not r['full_service_success']:self.assertIsNone(r['full_service_distance']);self.assertIsNone(r['distance_minus_best_returned_full'])
                self.assertEqual(get('/api/route-comparison?experiments=vrptw-mature-20261007')['row_count'],96)
                self.assertEqual(get('/api/route-comparison?experiments=vrptw-20261007,vrptw-mature-20261007&instance=G12_tight')['row_count'],7)
                self.assertEqual(request('/api/route-comparison?experiments=vrptw-mature-20261007,vrptw-mature-20261007')[0],400)
                self.assertEqual(request('/api/route-comparison?experiments=vrptw-20261007,vrptw-mature-20261007','POST')[0],405)
                artifact_count=0
                for a in get(base)['artifacts']:
                    status,headers,data=request(base+'/artifacts/'+a['id']);self.assertEqual(status,200);self.assertEqual(hashlib.sha256(data).hexdigest(),a['sha256']);self.assertEqual(headers['X-Content-SHA256'],a['sha256']);artifact_count+=1
                self.assertEqual(store.get('vrptw-20261007')['revision'],1)
            finally:server.shutdown();server.server_close();thread.join()
            self.assertEqual(before,{str(p):snapshot(p) for p in [old,new]})
            report={'status':'PASS','fresh_database':True,'database':str(db),'old_runs':240,'new_runs':96,'combined_runs':336,'logical_unique_inputs':48,
                'new_state_counts':dict(states),'new_vehicle_responses':vehicles,'new_replayed_stops':stops,'http_requests':requests,
                'mature_artifacts_hashed':artifact_count,'idempotent':True,'old_fingerprint_unchanged':True,'algorithm_budget_groups':7,
                'new_budget_groups':newgroups,'duplicate_selections_rejected':True,'no_return_is_not_infeasible':True,
                'source_files_unchanged':True,'source_python_executed':False,'new_solver_runs':0,'ui_modified':False,'deployed':False,
                'legacy_receipt':oldreceipt,'mature_receipt':receipt}
            destination=os.environ.get('MATURE_INTEGRATION_REPORT')
            if destination:Path(destination).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':unittest.main()
