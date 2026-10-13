import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from backend import public_routes as p
from backend.store import Store, StoreError, canonical, sha
from backend.routes import RouteReader
from backend.mature_routes import import_route_archive
from backend.route_comparison import compare_routes
from public_fixture import fixture, load_blobs


class PublicRoutesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)/'source'
        self.format = p.PUBLIC_FORMAT
        self.digest = fixture(self.root,self.format)
        self.pins = patch.dict(p.PROTOCOL_HASHES,{self.format:self.digest})
        self.pins.start()
        self.addCleanup(self.pins.stop)
        parameters = patch.dict(p.PARAMETER_HASHES,{key:sha(b'synthetic no solver\n') for key in p.PARAMETER_HASHES})
        parameters.start();self.addCleanup(parameters.stop)
        self.store = Store(Path(self.tmp.name)/'db.sqlite3')

    def normalize(self, mutate=None):
        blobs, inputs = load_blobs(self.root)
        if mutate:
            mutate(blobs,inputs)
        return p.normalize_public(blobs,inputs,self.format)

    def test_two_budgets_native_ids_and_sparse_vehicle_identity(self):
        receipt = import_route_archive(self.store,self.root,self.format)
        self.assertTrue(import_route_archive(self.store,self.root,self.format)['reused'])
        reader = RouteReader(self.store,receipt['id'])
        self.assertEqual(set(reader.index['runs']),{'c101__250ms','c101__1000ms'})
        run = reader.run('c101__250ms')
        self.assertEqual(run['budget']['value'],250)
        self.assertEqual(run['metrics']['solve_cpu_s'],0.2)
        self.assertEqual(run['metrics']['solve_wall_s'],0.3)
        self.assertEqual(run['vehicles'][0]['vehicle_id'],2)
        self.assertIsNone(reader.vehicle(run['run_id'],0)['vehicle'])
        self.assertEqual(reader.vehicle(run['run_id'],2)['vehicle']['stops'][0]['node'],1)
        self.assertTrue(all(s['onboard_load'] is None for s in run['vehicles'][0]['stops']))
        self.assertEqual(run['vehicles'][0]['stops'][-1]['load_after'],100)
        self.assertIsNone(run['metrics']['bks_gap_percent'])
        self.assertEqual(run['input']['input_provenance']['official_byte_identity'],'unverified')
        self.assertFalse(any(a['filename']=='c101.txt' for a in self.store.get(receipt['id'])['artifacts']))

    def test_portfolio_timeout_has_no_fake_route(self):
        root = Path(self.tmp.name)/'portfolio'
        digest = fixture(root,p.PORTFOLIO_FORMAT)
        blobs, inputs = load_blobs(root)
        raw = [json.loads(x) for x in blobs['raw/results.jsonl'].splitlines()]
        timeout = raw[1]
        timeout.update(assignment_returned=False,routes=None,objective_integer=None,outcome='TIMEOUT',
            ortools_status=4,ortools_status_name='ROUTING_FAIL_TIMEOUT')
        timeout.pop('check_summary');timeout.pop('vehicles_used')
        blobs['raw/results.jsonl'] = ''.join(canonical(r)+'\n' for r in raw).encode()
        blobs['reports/evaluated_results.json'] = canonical(raw).encode()
        checks = [json.loads(x) for x in blobs['raw/continuous_checks.jsonl'].splitlines()]
        blobs['raw/continuous_checks.jsonl'] = ''.join(canonical(r)+'\n' for r in checks if r['run_id']!=timeout['run_id']).encode()
        v = json.loads(blobs['evidence/verification.json']);v['checker_success_count']=3
        blobs['evidence/verification.json'] = canonical(v).encode()
        with patch.dict(p.PROTOCOL_HASHES,{p.PORTFOLIO_FORMAT:digest}):
            index = p.normalize_public(blobs,inputs,p.PORTFOLIO_FORMAT)
        run = index['runs']['c101__pca250']
        self.assertEqual(run['solution_status'],'no_solution')
        self.assertEqual(run['problem_feasibility']['status'],'unknown')
        self.assertIsNone(run['routes']);self.assertEqual(run['vehicles'],[])
        self.assertIsNone(run['unserved_task_ids']);self.assertIsNone(run['checker']['audit'])
        self.assertIsNone(run['metrics']['full_service_distance'])

    def test_partial_invalid_and_complete_are_distinct(self):
        instance = self.normalize()['instances']['c101']
        original = {'fleet':3,'capacity':100,'nodes':{n['id']:[n[k] for k in ('x','y','demand','ready','due','service')] for n in instance['nodes']}}
        for nodes, expected in [([0,1,0],'partial'),([0,1,1,0],'invalid'),([0,*range(1,101),0],'feasible')]:
            routes = [{'vehicle':2,'nodes':nodes}]
            audit = p.check(original,routes)
            state, vehicles, normalized = p.normalize_witness(instance,routes,audit)
            self.assertEqual(state,expected)
            self.assertEqual(normalized['full_service_feasible'],expected=='feasible')

    def test_invalid_structure_does_not_shift_vehicle_id(self):
        instance = self.normalize()['instances']['c101']
        original = {'fleet':3,'capacity':100,'nodes':{n['id']:[n[k] for k in ('x','y','demand','ready','due','service')] for n in instance['nodes']}}
        routes = [{'vehicle':0,'nodes':[0,0]},{'vehicle':2,'nodes':[0,1,0]}]
        state, vehicles, _ = p.normalize_witness(instance,routes,p.check(original,routes))
        self.assertEqual(state,'invalid');self.assertEqual([v['vehicle_id'] for v in vehicles],[2])

    def test_wrong_protocol_even_with_refrozen_hash_rejected(self):
        def mutate(blobs, inputs):
            protocol=json.loads(blobs['protocol/protocol.json']);protocol['objective']='vehicles first'
            blobs['protocol/protocol.json']=canonical(protocol).encode()
            freeze=json.loads(blobs['protocol/freeze.json']);freeze['sha256']['protocol/protocol.json']=sha(blobs['protocol/protocol.json'])
            blobs['protocol/freeze.json']=canonical(freeze).encode()
        with self.assertRaisesRegex(StoreError,'已审阅固定协议'):
            self.normalize(mutate)

    def test_input_byte_mismatch_rejected(self):
        with self.assertRaises(StoreError):
            self.normalize(lambda blobs,inputs:inputs.update({'c101.txt':inputs['c101.txt']+b'\n'}))

    def test_duplicate_run_id_rejected(self):
        def mutate(blobs, inputs):
            rows=[json.loads(x) for x in blobs['raw/results.jsonl'].splitlines()]
            rows[1]['run_id']=rows[0]['run_id']
            blobs['raw/results.jsonl']=''.join(canonical(r)+'\n' for r in rows).encode()
        with self.assertRaises(StoreError):self.normalize(mutate)

    def test_corrupted_timetable_rejected(self):
        def mutate(blobs, inputs):
            rows=json.loads(blobs['reports/evaluated_results.json'])
            rows[0]['continuous_check']['route_audits'][0]['steps'][0]['arrival']+=1
            blobs['reports/evaluated_results.json']=canonical(rows).encode()
        with self.assertRaises(StoreError):self.normalize(mutate)

    def test_false_success_rejected(self):
        def mutate(blobs, inputs):
            rows=json.loads(blobs['reports/evaluated_results.json']);rows[0]['outcome']='FAIL'
            blobs['reports/evaluated_results.json']=canonical(rows).encode()
        with self.assertRaises(StoreError):self.normalize(mutate)

    def test_refrozen_parameter_change_rejected(self):
        def mutate(blobs, inputs):
            name='protocol/parameters_250ms.textproto';blobs[name]=b'time_limit: 2000'
            freeze=json.loads(blobs['protocol/freeze.json']);freeze['sha256'][name]=sha(blobs[name])
            blobs['protocol/freeze.json']=canonical(freeze).encode()
        with self.assertRaises(StoreError):self.normalize(mutate)

    def test_refrozen_encoded_input_claim_rejected(self):
        def mutate(blobs, inputs):
            name='protocol/input_manifest.json';m=json.loads(blobs[name]);m[0]['encoded_sha256']='0'*64
            blobs[name]=canonical(m).encode()
            freeze=json.loads(blobs['protocol/freeze.json']);freeze['sha256'][name]=sha(blobs[name])
            blobs['protocol/freeze.json']=canonical(freeze).encode()
        with self.assertRaises(StoreError):self.normalize(mutate)

    def test_negative_or_boolean_actual_timing_rejected(self):
        for value in (-1, True, float('inf')):
            def mutate(blobs, inputs):
                raw=[json.loads(x) for x in blobs['raw/results.jsonl'].splitlines()]
                evaluated=json.loads(blobs['reports/evaluated_results.json'])
                raw[0]['solve_cpu_s']=value;evaluated[0]['solve_cpu_s']=value
                blobs['raw/results.jsonl']=''.join(json.dumps(r)+'\n' for r in raw).encode()
                blobs['reports/evaluated_results.json']=json.dumps(evaluated).encode()
            with self.subTest(value=value), self.assertRaises(StoreError):self.normalize(mutate)

    def test_wrong_format_and_frozen_file_rejected_atomically(self):
        with self.assertRaises(StoreError):p.import_public(self.store,self.root,p.PORTFOLIO_FORMAT)
        (self.root/'source/checker.py').write_text('raise Exception("never execute")')
        with self.assertRaises(StoreError):p.import_public(self.store,self.root,self.format)
        self.assertEqual(self.store.list(),[])

    def test_two_formats_compare_same_inputs_without_collision(self):
        a=p.import_public(self.store,self.root,self.format)
        root=Path(self.tmp.name)/'portfolio';digest=fixture(root,p.PORTFOLIO_FORMAT)
        with patch.dict(p.PROTOCOL_HASHES,{p.PORTFOLIO_FORMAT:digest}):
            b=p.import_public(self.store,root,p.PORTFOLIO_FORMAT)
        compared=compare_routes(self.store,[{'experiment_id':a['id']},{'experiment_id':b['id']}])
        self.assertEqual(compared['row_count'],6);self.assertEqual(compared['unique_input_count'],1)
        self.assertEqual(len({(r['experiment_id'],r['run_id']) for r in compared['rows']}),6)
        self.assertFalse(compared['same_known_budget'])
        with self.assertRaises(StoreError):p.import_public(self.store,self.root,self.format,b['id'])

    def test_original_checker_copy_byte_identity_and_eight_tests(self):
        self.assertEqual(sha(Path(p.__file__).with_name('archived_solomon_checker.py').read_bytes()),p.CHECKER_SHA256)
        from backend.archived_solomon_checker import tests
        self.assertEqual(len(tests()),8)

if __name__=='__main__':unittest.main()
