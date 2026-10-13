import hashlib
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from backend.mature_routes import import_mature, import_route_archive
from backend.route_comparison import compare_routes
from backend.routes import import_vrptw, RouteReader
from backend.server import make_server
from backend.store import Store,StoreError
from mature_fixture import write_mature_fixture,rewrite_results

class MatureRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.legacy,self.mature=write_mature_fixture(self.root);self.store=Store(self.root/'fresh.sqlite3')
    def both(self):
        import_vrptw(self.store,self.legacy,'legacy');import_mature(self.store,self.mature,'mature')
    def test_coexistence_native_ids_shared_inputs_and_idempotence(self):
        self.both();self.assertEqual(RouteReader(self.store,'legacy').runs()['count'],5);self.assertEqual(RouteReader(self.store,'mature').runs()['count'],4)
        self.assertTrue(import_mature(self.store,self.mature,'mature')['reused']);self.assertEqual(len(self.store.list()),2)
        r=compare_routes(self.store,[{'experiment_id':'legacy'},{'experiment_id':'mature'}]);self.assertEqual(r['row_count'],9);self.assertEqual(r['unique_input_count'],2)
        self.assertFalse(r['same_known_budget']);self.assertEqual(len({x['run_id'] for x in r['rows'] if x['experiment_id']=='mature'}),4)
    def test_fail_is_no_solution_not_infeasible_or_invalid(self):
        self.both();r=RouteReader(self.store,'mature').run('fixture_impossible__250ms')
        self.assertEqual(r['solution_status'],'no_solution');self.assertEqual(r['solver_status']['name'],'ROUTING_FAIL')
        self.assertEqual(r['problem_feasibility']['status'],'infeasible');self.assertIsNone(r['routes']);self.assertIsNone(r['checker']['audit']);self.assertIsNone(r['unserved_task_ids'])
        self.assertFalse(r['checker']['recomputed_at_import']);self.assertIsNone(r['solver_error']);self.assertFalse(r['full_service_success'])
    def test_no_return_on_oracle_feasible_input_remains_no_solution(self):
        def mutate(r):
            if r['run_id']=='fixture_possible__250ms':
                r.update(outcome='no_solution_in_budget',ortools_status=3,ortools_status_name='ROUTING_FAIL',assignment_returned=False,routes=None,audit=None,encoded_cumul_ranges=None,objective_integer=None)
                if 'full_gap_original_percent' in r:r['full_gap_original_percent']=None
        rewrite_results(self.mature,mutate)
        p=self.mature/'verification.json';d=json.loads(p.read_text());d['returned_solutions_independently_replayed']=1;p.write_text(json.dumps(d))
        import_mature(self.store,self.mature,'mature');r=RouteReader(self.store,'mature').run('fixture_possible__250ms')
        self.assertEqual(r['solution_status'],'no_solution');self.assertEqual(r['problem_feasibility']['status'],'feasible')
        self.assertFalse(r['full_service_success']);self.assertIsNone(r['routes'])
    def test_returned_routes_replayed_load_unknown(self):
        self.both();r=RouteReader(self.store,'mature').vehicle('fixture_possible__250ms',0)
        self.assertTrue(r['checker']['recomputed_at_import']);self.assertEqual([s['load_after'] for s in r['vehicle']['stops']],[1,2])
        self.assertTrue(all(s['onboard_load'] is None for s in r['vehicle']['stops']))
        self.assertEqual([s['arrival'] for s in r['vehicle']['stops']],[1,3])
    def test_replay_rejects_consistently_tampered_saved_time(self):
        def mutate(r):
            if r['audit']:r['audit']['schedules'][0]['stops'][0]['arrival']+=1
        rewrite_results(self.mature,mutate)
        with self.assertRaisesRegex(StoreError,'回放数值'):import_mature(self.store,self.mature,'mature')
        self.assertEqual(self.store.list(),[])
    def test_input_identity_mismatch_is_rejected(self):
        p=self.mature/'map_backend.json';d=json.loads(p.read_text());d['source_input_sha256']='0'*64;p.write_text(json.dumps(d))
        with self.assertRaisesRegex(StoreError,'输入身份'):import_mature(self.store,self.mature,'mature')
        self.assertEqual(self.store.list(),[])
    def test_both_formats_cannot_overwrite_each_others_id(self):
        self.both()
        with self.assertRaises(StoreError) as e:import_mature(self.store,self.mature,'legacy')
        self.assertEqual(e.exception.code,'experiment_identity_mismatch')
        with self.assertRaises(StoreError) as e:import_vrptw(self.store,self.legacy,'mature')
        self.assertEqual(e.exception.code,'experiment_identity_mismatch');self.assertEqual(len(self.store.list()),2)
    def test_versions_and_old_artifacts_remain_immutable(self):
        self.both();p=self.mature/'verification.json';d=json.loads(p.read_text());d['note']='new audit observation';p.write_text(json.dumps(d))
        self.assertEqual(import_mature(self.store,self.mature,'mature')['revision'],2)
        old=RouteReader(self.store,'mature',1);new=RouteReader(self.store,'mature',2)
        self.assertNotIn('note',old.index['verification']['recorded_report']);self.assertIn('note',new.index['verification']['recorded_report'])
        self.assertEqual(old.index['runs'],new.index['runs'])
    def test_different_frozen_problem_is_not_compared(self):
        self.both();p=self.legacy/'protocol.json';d=json.loads(p.read_text());d['study_id']='different problem spec';p.write_text(json.dumps(d))
        f=self.legacy/'freeze.json';frozen=json.loads(f.read_text());frozen['sha256']['protocol.json']=hashlib.sha256(p.read_bytes()).hexdigest();f.write_text(json.dumps(frozen))
        import_vrptw(self.store,self.legacy,'other')
        with self.assertRaises(StoreError) as e:compare_routes(self.store,[{'experiment_id':'other'},{'experiment_id':'mature'}])
        self.assertEqual(e.exception.status,409)
    def test_comparison_excludes_partial_and_no_return_from_distance(self):
        self.both();r=compare_routes(self.store,[{'experiment_id':'legacy'},{'experiment_id':'mature'}])
        for row in r['rows']:
            if row['full_service_success']:self.assertIsNotNone(row['full_service_distance'])
            else:self.assertIsNone(row['full_service_distance']);self.assertIsNone(row['distance_minus_best_returned_full'])
    def test_duplicate_resolved_selection_rejected_and_single_experiment_budgets_supported(self):
        self.both()
        with self.assertRaisesRegex(StoreError,'重复选择'):
            compare_routes(self.store,[{'experiment_id':'mature'},{'experiment_id':'mature','revision':1}])
        r=compare_routes(self.store,[{'experiment_id':'mature'}]);self.assertEqual(r['row_count'],4);self.assertEqual(len(r['groups']),2)
    def test_tampered_enriched_gap_rejected(self):
        p=self.mature/'evaluated_results.json';rows=json.loads(p.read_text());rows[0]['full_gap_original_percent']=987654321;p.write_text(json.dumps(rows))
        p=self.mature/'map_backend.json';d=json.loads(p.read_text());d['instances'][0]['runs'][0]['full_gap_original_percent']=987654321;p.write_text(json.dumps(d))
        with self.assertRaisesRegex(StoreError,'full_gap_original_percent'):import_mature(self.store,self.mature,'mature')
        self.assertEqual(self.store.list(),[])
    def test_incompatible_reference_time_semantics_rejected(self):
        p=self.mature/'reference/protocol.json';d=json.loads(p.read_text());d['input']['time_window_semantics']='arrival only';p.write_text(json.dumps(d))
        p=self.mature/'reference/freeze.json';d=json.loads(p.read_text());d['sha256']['protocol.json']=hashlib.sha256((self.mature/'reference/protocol.json').read_bytes()).hexdigest();p.write_text(json.dumps(d))
        with self.assertRaisesRegex(StoreError,'合同'):import_mature(self.store,self.mature,'mature')
    def test_reference_infeasibility_cannot_conflict_with_valid_solution(self):
        p=self.mature/'reference/routes.jsonl';rows=[json.loads(l) for l in p.read_text().splitlines()]
        for row in rows:
            if row['method']=='oracle_full' and row['instance']=='fixture_possible':row.update(status='proven_infeasible',routes=None,audit=None,full_oracle_objective=None)
        p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        p=self.mature/'evaluated_results.json';rows=json.loads(p.read_text())
        for r in rows:
            if r['instance']=='fixture_possible':r.update(reference_oracle_full_feasible=False,full_gap_original_percent=None)
        p.write_text(json.dumps(rows));p=self.mature/'map_backend.json';d=json.loads(p.read_text())
        for item in d['instances']:
            if item['input']['id']=='fixture_possible':
                item['reference_oracle_full_feasible']=False
                for r in item['runs']:r.update(reference_oracle_full_feasible=False,full_gap_original_percent=None)
        p.write_text(json.dumps(d))
        with self.assertRaises(StoreError) as e:import_mature(self.store,self.mature,'mature')
        self.assertEqual(e.exception.code,'reference_conflict');self.assertEqual(self.store.list(),[])
    def test_reference_feasible_requires_witness(self):
        p=self.mature/'reference/routes.jsonl';rows=[json.loads(l) for l in p.read_text().splitlines()]
        for row in rows:
            if row['method']=='oracle_full' and row['instance']=='fixture_possible':row['routes']=None
        p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        with self.assertRaisesRegex(StoreError,'见证'):import_mature(self.store,self.mature,'mature')
    def test_explicit_format_rejects_unknown_without_aliases(self):
        with self.assertRaises(StoreError):import_route_archive(self.store,self.mature,'autodetect')
        with self.assertRaises(StoreError):import_route_archive(self.store,self.legacy,'vrptw-mature-solver-v1')
    def test_read_only_http_comparison_and_native_vehicle(self):
        self.both();server=make_server(self.store,self.root,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def request(path,method='GET'):
            c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5);c.request(method,path);r=c.getresponse();data=json.loads(r.read());status=r.status;c.close();return status,data
        try:
            path='/api/route-comparison?experiments=legacy,mature';status,data=request(path);self.assertEqual(status,200);self.assertEqual(data['row_count'],9)
            self.assertEqual(request(path,'POST')[0],405);self.assertEqual(request(path+'&revisions=1,1')[0],200)
            self.assertEqual(request(path+'&revisions=1')[0],400);self.assertEqual(request(path+'&revisions=1,999')[0],404)
            self.assertEqual(request('/api/experiments/mature/runs?solution_status=no_solution')[1]['count'],2)
            status,data=request('/api/experiments/mature/runs/fixture_impossible__250ms/vehicles/0');self.assertEqual(status,200);self.assertIsNone(data['vehicle']);self.assertEqual(data['solution_status'],'no_solution')
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
