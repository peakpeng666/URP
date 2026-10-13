"""Offline synthetic contract, immutability, path, and real HTTP checks."""
import hashlib
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from backend.routes import RouteReader, import_vrptw
from backend.server import make_server
from backend.store import Store, StoreError
from route_fixture import write_fixture

class RouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.source = write_fixture(self.root/'source')
        self.store = Store(self.root/'independent.sqlite3')
    def load(self):
        import_vrptw(self.store,self.source,'fixture'); return RouteReader(self.store,'fixture')
    def test_idempotent_and_immutable(self):
        a=import_vrptw(self.store,self.source,'fixture'); b=import_vrptw(self.store,self.source,'fixture')
        self.assertFalse(a['reused']); self.assertTrue(b['reused']); self.assertEqual(a['fingerprint'],b['fingerprint'])
        (self.source/'routes.jsonl').write_text('destroyed')
        self.assertEqual(RouteReader(self.store,'fixture').runs()['count'],4)
    def test_solution_states_and_no_solver_errors(self):
        reader=self.load(); runs=reader.index['runs']
        self.assertEqual({r['solution_status'] for r in runs.values()},{'feasible','partial','invalid','infeasible'})
        for r in runs.values():
            self.assertEqual(r['full_service_success'],r['solution_status']=='feasible')
            self.assertIsNone(r['solver_error']); self.assertEqual(r['execution_status'],'completed')
        self.assertEqual(reader.run('fixture_possible.time_window_first')['unserved_task_ids'],[2])
    def test_infeasible_nulls_not_zero(self):
        r=self.load().vehicle('fixture_impossible.oracle_full',0)
        self.assertIsNone(r['vehicle']); self.assertIsNone(r['unserved_task_ids'])
        self.assertEqual(r['checker']['status'],'no_candidate'); self.assertFalse(r['full_service_success'])
        self.assertIsNone(self.load().run('fixture_impossible.oracle_full')['metrics']['full_oracle_objective'])
    def test_vehicle_schedule_load_and_geometry(self):
        r=self.load().vehicle('fixture_possible.distance_first',0); v=r['vehicle']
        self.assertEqual(v['path_node_ids'],[0,1,2,0]); self.assertEqual(v['path_coordinates'],[[0,0],[1,0],[2,0],[0,0]])
        self.assertEqual([s['load_after'] for s in v['stops']],[1,2])
        self.assertEqual([s['service_start'] for s in v['stops']],[1,3])
        self.assertTrue(all(s['onboard_load'] is None for s in v['stops']))
        self.assertFalse(r['semantics']['is_road_network']); self.assertFalse(r['semantics']['is_geographic'])
    def test_hash_provenance(self):
        r=self.load().run('fixture_possible.distance_first'); p=r['provenance']
        self.assertIsNone(p['source_run_id']); self.assertTrue(p['run_hash_source'].startswith('derived:'))
        self.assertEqual(p['run_sha256'],hashlib.sha256((self.source/'routes.jsonl').read_bytes().splitlines()[0]).hexdigest())
        self.assertEqual(p['spec_sha256'],hashlib.sha256((self.source/'protocol.json').read_bytes()).hexdigest())
        self.assertEqual(p['input_file_sha256'],hashlib.sha256((self.source/'inputs.json').read_bytes()).hexdigest())
        self.assertEqual(p['locator'],'line 1'); self.assertEqual(p['input_locator'],'/0')
    def test_version_history(self):
        self.load(); p=self.source/'verification.json'; d=json.loads(p.read_text());d['note']='added audit note';p.write_text(json.dumps(d))
        receipt=import_vrptw(self.store,self.source,'fixture');self.assertEqual(receipt['revision'],2)
        self.assertNotIn('note',RouteReader(self.store,'fixture',1).index['verification']['recorded_report'])
        self.assertIn('note',RouteReader(self.store,'fixture',2).index['verification']['recorded_report'])
    def test_mismatch_atomic_rejection(self):
        p=self.source/'map_backend.json'; d=json.loads(p.read_text()); d['solutions'][0]['routes']=[[2]]; p.write_text(json.dumps(d))
        with self.assertRaisesRegex(StoreError,'不一致'):import_vrptw(self.store,self.source,'fixture')
        self.assertEqual(self.store.list(),[])
    def test_frozen_hash_mismatch_atomic_rejection(self):
        p=self.source/'protocol.json';d=json.loads(p.read_text());d['study_id']='changed';p.write_text(json.dumps(d))
        with self.assertRaisesRegex(StoreError,'冻结哈希'):import_vrptw(self.store,self.source,'fixture')
        self.assertEqual(self.store.list(),[])
    def test_partial_cannot_claim_full_success(self):
        rows=[json.loads(x) for x in (self.source/'routes.jsonl').read_text().splitlines()]
        rows[1]['audit']['full_service_feasible']=True
        (self.source/'routes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        p=self.source/'map_backend.json'; d=json.loads(p.read_text());d['solutions']=rows;p.write_text(json.dumps(d))
        with self.assertRaisesRegex(StoreError,'全服务成功'):import_vrptw(self.store,self.source,'fixture')
        self.assertEqual(self.store.list(),[])
    def test_unknown_source_state_is_not_completed(self):
        rows=[json.loads(x) for x in (self.source/'routes.jsonl').read_text().splitlines()]
        rows[0]['status']='failed'
        (self.source/'routes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        p=self.source/'map_backend.json';d=json.loads(p.read_text());d['solutions']=rows;p.write_text(json.dumps(d))
        with self.assertRaisesRegex(StoreError,'不能推断为已完成'):import_vrptw(self.store,self.source,'fixture')
    def test_units_cannot_be_silently_overridden(self):
        for field,value in [('units','hours; speed=2'),('objective','road duration'),('coordinate_system','WGS84')]:
            write_fixture(self.source)
            p=self.source/'map_backend.json';d=json.loads(p.read_text());d[field]=value;p.write_text(json.dumps(d))
            with self.assertRaisesRegex(StoreError,'仅支持'):import_vrptw(self.store,self.source,'fixture')
        self.assertEqual(self.store.list(),[])
    def test_violations_cannot_claim_passed_checker(self):
        rows=[json.loads(x) for x in (self.source/'routes.jsonl').read_text().splitlines()]
        rows[2]['audit']['route_feasible']=True;rows[2]['audit']['full_service_feasible']=True
        (self.source/'routes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        p=self.source/'map_backend.json';d=json.loads(p.read_text());d['solutions']=rows;p.write_text(json.dumps(d))
        with self.assertRaisesRegex(StoreError,'存在违规'):import_vrptw(self.store,self.source,'fixture')
    def test_invalid_jsonl_has_clean_atomic_error(self):
        (self.source/'routes.jsonl').write_text('{not json}')
        with self.assertRaises(StoreError) as caught:import_vrptw(self.store,self.source,'fixture')
        self.assertEqual(caught.exception.code,'invalid_route_source');self.assertEqual(self.store.list(),[])
    def test_source_symlink_and_secret_rejected(self):
        p=self.source/'checker.py';target=self.root/'outside.py';target.write_bytes(p.read_bytes());p.unlink();p.symlink_to(target)
        with self.assertRaisesRegex(StoreError,'符号链接'):import_vrptw(self.store,self.source,'fixture')
        p.unlink();p.write_bytes(target.read_bytes());p=self.source/'verification.json';p.write_text('{"password":"test-not-a-secret"}')
        with self.assertRaisesRegex(StoreError,'凭据'):import_vrptw(self.store,self.source,'fixture')
    def test_read_only_http_and_basic_parameter_validation(self):
        self.load();server=make_server(self.store,self.root,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def request(path,method='GET'):
            c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5);c.request(method,path);r=c.getresponse();value=json.loads(r.read());status=r.status;c.close();return status,value
        base='/api/experiments/fixture'
        try:
            for suffix in ['/instances','/runs','/runs/fixture_possible.distance_first','/runs/fixture_possible.distance_first/vehicles/0']:
                self.assertEqual(request(base+suffix)[0],200)
                self.assertEqual(request(base+suffix,'POST')[0],405)
            self.assertEqual(request(base+'/runs?solution_status=partial')[1]['count'],1)
            self.assertEqual(request(base+'/runs?instance=fixture_impossible')[1]['count'],1)
            for suffix,expected in [('/runs?solution_status=success',400),('/runs?revision=0',400),('/runs?revision=abc',400),('/runs?revision=999',404),('/runs/absent',404),('/runs/..%2Fx',400),('/runs/fixture_possible.distance_first/vehicles/-1',400),('/runs/fixture_possible.distance_first/vehicles/2',404)]:
                self.assertEqual(request(base+suffix)[0],expected,suffix)
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
