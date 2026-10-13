"""Real archives required explicitly. No solver execution or replacement fixture."""
import hashlib
import http.client
import json
import os
import tempfile
import threading
import unittest
from collections import Counter
from pathlib import Path
from backend.store import Store
from backend.routes import RouteReader, import_vrptw
from backend.mature_routes import import_mature, import_route_archive
from backend.public_routes import PUBLIC_FORMAT, PORTFOLIO_FORMAT
from backend.route_comparison import compare_routes
from backend.server import make_server


class RealPublicRoutesTests(unittest.TestCase):
    def test_four_archives_read_only_and_legacy_fingerprints(self):
        paths = {name:Path(os.environ[name]) for name in ('PUBLIC_VRPTW_SOURCE_ROOT','PORTFOLIO_VRPTW_SOURCE_ROOT',
            'VRPTW_SOURCE_ROOT','MATURE_VRPTW_SOURCE_ROOT')}
        def snapshot(path):
            return {str(f.relative_to(path)):hashlib.sha256(f.read_bytes()).hexdigest() for f in path.rglob('*')
                    if f.is_file() and not any(part in {'.venv','__pycache__'} for part in f.parts)}
        before={name:snapshot(path) for name,path in paths.items()}
        inputs=Path(os.environ.get('PUBLIC_VRPTW_INPUT_DIR',str(paths['PUBLIC_VRPTW_SOURCE_ROOT']/'inputs')))
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'fresh.sqlite3')
            old=import_vrptw(store,paths['VRPTW_SOURCE_ROOT'])
            mature=import_mature(store,paths['MATURE_VRPTW_SOURCE_ROOT'])
            self.assertEqual(old['fingerprint'],'b98ff9710eda1bf5bd77997767d8b6d765e780e962e850abdd8ed40eb649393e')
            self.assertEqual(mature['fingerprint'],'45953c1ee15176d67ad366d1f04b4e7738712ee1fc2579d4a240e635d07bf54d')
            legacy_before={receipt['id']:RouteReader(store,receipt['id']).index for receipt in (old,mature)}
            public=import_route_archive(store,paths['PUBLIC_VRPTW_SOURCE_ROOT'],PUBLIC_FORMAT,input_dir=inputs)
            portfolio=import_route_archive(store,paths['PORTFOLIO_VRPTW_SOURCE_ROOT'],PORTFOLIO_FORMAT,input_dir=inputs)
            self.assertTrue(import_route_archive(store,paths['PUBLIC_VRPTW_SOURCE_ROOT'],PUBLIC_FORMAT,input_dir=inputs)['reused'])
            self.assertTrue(import_route_archive(store,paths['PORTFOLIO_VRPTW_SOURCE_ROOT'],PORTFOLIO_FORMAT,input_dir=inputs)['reused'])
            server=make_server(store,paths['PUBLIC_VRPTW_SOURCE_ROOT'],0)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            request_count=0
            def request(path,method='GET'):
                nonlocal request_count
                request_count+=1
                c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=30)
                c.request(method,path);r=c.getresponse();data=r.read();status=r.status;c.close()
                return status,data
            def get(path):
                status,data=request(path);self.assertEqual(status,200,(path,status,data[:200]));return json.loads(data)
            states=Counter();stops=vehicles=0
            try:
                for receipt,source,expected in [(public,paths['PUBLIC_VRPTW_SOURCE_ROOT'],112),(portfolio,paths['PORTFOLIO_VRPTW_SOURCE_ROOT'],224)]:
                    base='/api/experiments/'+receipt['id']
                    listing=get(base+'/runs');self.assertEqual(listing['count'],expected)
                    self.assertEqual(listing['summary']['geometry_group_count'],4)
                    rows=[json.loads(x) for x in (source/'raw/results.jsonl').read_text().splitlines()]
                    for row in rows:
                        run=get(base+'/runs/'+row['run_id']);states[run['solution_status']]+=1
                        self.assertEqual(run['source_routes'],row['routes'])
                        self.assertEqual(run['provenance']['run_sha256'],hashlib.sha256((source/'raw/results.jsonl').read_bytes().splitlines()[row['sequence']]).hexdigest())
                        self.assertEqual(run['budget']['value'],row['budget_ms'])
                        for field in ['solve_cpu_s','solve_wall_s','model_cpu_s','model_wall_s','total_cpu_s','total_wall_s']:
                            self.assertEqual(run['metrics'][field],row[field])
                        self.assertIsNone(run['metrics']['bks_gap_percent'])
                        if row['routes'] is None:
                            self.assertEqual(run['solution_status'],'no_solution');self.assertEqual(run['vehicles'],[])
                            self.assertIsNone(run['routes']);self.assertIsNone(run['checker']['audit'])
                            self.assertEqual(run['problem_feasibility']['status'],'unknown')
                            self.assertIsNone(get(base+'/runs/'+row['run_id']+'/vehicles/0')['vehicle'])
                        else:
                            self.assertEqual(len(run['vehicles']),len(row['routes']))
                            for source_vehicle,vehicle in zip(row['routes'],run['vehicles']):
                                vehicles+=1;stops+=len(vehicle['stops'])
                                self.assertEqual(vehicle['vehicle_id'],source_vehicle['vehicle'])
                                self.assertEqual(vehicle['path_node_ids'],source_vehicle['nodes'])
                                self.assertTrue(all(s['onboard_load'] is None for s in vehicle['stops']))
                                self.assertEqual(vehicle['load'],sum(s['demand'] for s in vehicle['stops']))
                            first=run['vehicles'][0]
                            self.assertEqual(get(base+'/runs/'+row['run_id']+'/vehicles/'+str(first['vehicle_id']))['vehicle'],first)
                    self.assertEqual(request(base+'/runs','POST')[0],405)
                comparison=get('/api/route-comparison?experiments='+public['id']+','+portfolio['id'])
                self.assertEqual(comparison['row_count'],336);self.assertEqual(comparison['unique_input_count'],56)
                self.assertEqual(len(comparison['groups']),6)
                self.assertEqual(len({(r['experiment_id'],r['run_id']) for r in comparison['rows']}),336)
                self.assertEqual(request('/api/route-comparison?experiments='+old['id']+','+public['id'])[0],409)
            finally:
                server.shutdown();server.server_close();thread.join()
            self.assertEqual(states,{'feasible':329,'no_solution':7})
            self.assertEqual(stops,32900)
            self.assertEqual(legacy_before,{receipt['id']:RouteReader(store,receipt['id']).index for receipt in (old,mature)})
            legacy_comparison=compare_routes(store,[{'experiment_id':old['id']},{'experiment_id':mature['id']}])
            self.assertEqual(legacy_comparison['row_count'],336);self.assertEqual(legacy_comparison['unique_input_count'],48)
            self.assertEqual(before,{name:snapshot(path) for name,path in paths.items()})
            report={'status':'PASS','old_runs':336,'old_logical_inputs':48,'new_runs':336,'new_logical_inputs':56,
                'new_status_counts':dict(states),'geometry_groups':4,'replayed_stops':stops,'returned_vehicles':vehicles,
                'http_requests':request_count,'legacy_fingerprints':[old['fingerprint'],mature['fingerprint']],
                'legacy_complete_indexes_unchanged':True,'source_bytes_unchanged':True,'idempotent':True,
                'solver_executions':0,'archive_code_executions':0,'new_receipts':[public,portfolio]}
            if os.environ.get('PUBLIC_INTEGRATION_REPORT'):
                Path(os.environ['PUBLIC_INTEGRATION_REPORT']).write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(report))

if __name__=='__main__':unittest.main()
