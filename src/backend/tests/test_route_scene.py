"""Route-scene contract checks using synthetic evidence only; no robot/solver."""
import copy
import hashlib
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import public_routes as public
from backend.mature_routes import import_mature
from backend.route_scene import route_scene, scene_from_reader
from backend.routes import RouteReader, import_vrptw
from backend.server import make_server
from backend.store import Store, StoreError, sha
from mature_fixture import write_mature_fixture
from public_fixture import fixture as write_public_fixture
from route_fixture import write_fixture


class RouteSceneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = write_fixture(self.root/'source')
        self.store = Store(self.root/'fixture.sqlite3')
        import_vrptw(self.store, self.source, 'fixture')

    def scene(self, suffix='distance_first', instance='fixture_possible', revision=None):
        return route_scene(self.store, 'fixture', instance+'.'+suffix, revision)

    def test_frozen_example_is_exact_export(self):
        expected = json.loads((Path(__file__).parent/'fixtures/route_scene_v1.json').read_text())
        self.assertEqual(self.scene(), expected)

    def test_xy_coordinates_visit_order_and_units_are_source_exact(self):
        scene = self.scene()
        self.assertEqual(scene['schema_version'], 1)
        self.assertEqual(scene['geometry_kind'], 'visit_order_polyline')
        self.assertEqual(scene['depot']['node_id'], 0)
        self.assertEqual([p['node_id'] for p in scene['task_nodes']], [1, 2])
        self.assertEqual(scene['vehicles'][0]['visit_node_ids'], [0, 1, 2, 0])
        self.assertEqual(scene['vehicles'][0]['polyline'], [[0, 0], [1, 0], [2, 0], [0, 0]])
        self.assertEqual(scene['units']['distance'], 'arbitrary_distance_units')
        self.assertEqual(scene['units']['schedule_time'], 'arbitrary_time_units')
        self.assertEqual(scene['units']['compute_time'], 'seconds')
        self.assertIsNone(scene['units']['demand'])
        self.assertEqual(scene['task_nodes'][0]['time_window'], [0, 2])
        self.assertEqual(scene['vehicles'][0]['stops'][0]['service_start'], 1)
        self.assertIsNone(scene['vehicles'][0]['stops'][0]['onboard_load'])

    def test_simulation_and_recommendation_are_never_inferred(self):
        for scene in (self.scene(), self.scene('time_window_first'),
                      self.scene('capacity_only_diagnostic'),
                      self.scene('oracle_full', 'fixture_impossible')):
            self.assertFalse(scene['simulation_ready'])
            self.assertIsNone(scene['frame']['physical_frame_id'])
            self.assertIsNone(scene['frame']['meters_per_coordinate_unit'])
            self.assertEqual(scene['recommendation']['status'], 'not_available')
            self.assertIsNone(scene['recommendation']['selected_run_id'])
            self.assertIsNone(scene['recommendation']['evidence'])
            self.assertNotIn('cmd_vel', json.dumps(scene))

    def test_partial_and_invalid_keep_geometry_without_full_success(self):
        partial = self.scene('time_window_first')
        invalid = self.scene('capacity_only_diagnostic')
        self.assertEqual(partial['status']['solution_status'], 'partial')
        self.assertEqual(partial['unserved_task_ids'], [2])
        self.assertEqual(partial['metrics']['served_task_count'], 1)
        self.assertEqual(partial['metrics']['total_distance'], 2)
        self.assertIsNone(partial['metrics']['full_service_distance'])
        self.assertEqual(invalid['status']['solution_status'], 'invalid')
        self.assertFalse(invalid['status']['full_service_success'])
        self.assertEqual(invalid['vehicles'][0]['visit_node_ids'], [0, 2, 1, 0])
        self.assertGreater(invalid['vehicles'][0]['stops'][1]['lateness'], 0)
        self.assertIsNone(invalid['metrics']['full_service_distance'])

    def test_no_candidate_keeps_null_metrics_not_fake_zero_route(self):
        scene = self.scene('oracle_full', 'fixture_impossible')
        self.assertEqual(scene['status']['solution_status'], 'infeasible')
        self.assertFalse(scene['status']['has_candidate'])
        self.assertEqual(scene['vehicles'], [])
        self.assertIsNone(scene['unserved_task_ids'])
        self.assertIsNone(scene['metrics']['total_distance'])
        self.assertIsNone(scene['metrics']['served_task_count'])
        self.assertIsNone(scene['metrics']['recorded']['full_oracle_objective'])
        self.assertEqual(scene['metrics']['task_count'], 2)

    def test_metrics_missing_units_and_recommendations_are_not_filled_in(self):
        reader = RouteReader(self.store, 'fixture')
        run = reader.get_run('fixture_possible.distance_first')
        run['metrics'] = {'unexpected_metric': 7}
        run['recommendation'] = {'status': 'recommended', 'confidence': 1}
        reader.index['semantics'].pop('time_unit')
        scene = scene_from_reader(reader, run['run_id'])
        self.assertEqual(scene['metrics']['recorded'], {})
        self.assertIsNone(scene['units']['compute_time'])
        self.assertIsNone(scene['units']['schedule_time'])
        self.assertEqual(scene['recommendation']['status'], 'not_available')

    def test_no_input_mutation_and_output_has_no_live_aliases(self):
        reader = RouteReader(self.store, 'fixture')
        before = copy.deepcopy(reader.index)
        scene = scene_from_reader(reader, 'fixture_possible.distance_first')
        scene['vehicles'][0]['stops'][0]['service_start'] = 999
        scene['provenance']['run']['run_sha256'] = 'changed'
        scene['semantics']['speed'] = 100
        scene['task_nodes'][0]['time_window'][0] = 777
        self.assertEqual(reader.index, before)

    def test_provenance_hashes_and_revision_are_pinned(self):
        one = self.scene(revision=1)
        index = one['provenance']['index_artifact']
        ref, blob = self.store.artifact('fixture', index['id'], 1)
        self.assertEqual(index['sha256'], hashlib.sha256(blob).hexdigest())
        self.assertEqual(index['sha256'], ref['sha256'])
        self.assertTrue(index['url'].endswith('?revision=1'))
        self.assertTrue(one['provenance']['source_run_url'].endswith('?revision=1'))
        verification = self.source/'verification.json'
        value = json.loads(verification.read_text()); value['note'] = 'second revision'
        verification.write_text(json.dumps(value))
        import_vrptw(self.store, self.source, 'fixture')
        self.assertEqual(self.scene(revision=1), one)
        two = self.scene()
        self.assertEqual(two['revision'], 2)
        self.assertNotEqual(two['experiment_fingerprint'], one['experiment_fingerprint'])

    def test_source_files_can_disappear_after_import(self):
        expected = self.scene()
        for path in self.source.iterdir():
            path.unlink()
        self.assertEqual(self.scene(), expected)

    def test_bad_geometry_and_nonfinite_values_fail_closed(self):
        for mutate in (
            lambda r: r.index['instances']['fixture_possible']['nodes'][1].update(x=float('nan')),
            lambda r: r.get_run('fixture_possible.distance_first')['vehicles'][0]['path_coordinates'][1].__setitem__(0, 100),
            lambda r: r.get_run('fixture_possible.distance_first')['metrics'].update(cpu_seconds=float('inf')),
        ):
            reader = RouteReader(self.store, 'fixture'); mutate(reader)
            with self.assertRaises(StoreError) as caught:
                scene_from_reader(reader, 'fixture_possible.distance_first')
            self.assertEqual(caught.exception.code, 'invalid_route_scene')

    def test_importable_malformed_metrics_fail_closed_over_http(self):
        server = make_server(self.store, self.root, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        scene_path = '/api/v1/experiments/fixture/runs/fixture_possible.distance_first/route-scene'
        source_path = '/api/experiments/fixture/runs/fixture_possible.distance_first'
        def request(path):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            connection.request('GET', path)
            response = connection.getresponse(); value = json.loads(response.read())
            status = response.status; connection.close()
            return status, value
        try:
            for malformed in ('not_recorded', True, [0], {'value': 0}, 10**400):
                with self.subTest(value=malformed):
                    rows = [json.loads(line) for line in (self.source/'routes.jsonl').read_text().splitlines()]
                    rows[0]['cpu_seconds'] = malformed
                    (self.source/'routes.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
                    source_map = json.loads((self.source/'map_backend.json').read_text())
                    source_map['solutions'] = rows
                    (self.source/'map_backend.json').write_text(json.dumps(source_map))
                    import_vrptw(self.store, self.source, 'fixture')
                    before = self.store.path.read_bytes()
                    status, scene = request(scene_path)
                    self.assertEqual(status, 409)
                    self.assertEqual(scene['error'], 'invalid_route_scene')
                    status, original = request(source_path)
                    self.assertEqual(status, 200)
                    self.assertEqual(original['metrics']['cpu_seconds'], malformed)
                    self.assertEqual(self.store.path.read_bytes(), before)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_invalid_public_candidate_retains_unverified_source_coverage(self):
        source = self.root/'malformed-public'
        digest = write_public_fixture(source, public.PUBLIC_FORMAT)
        rows = [json.loads(line) for line in (source/'raw/results.jsonl').read_text().splitlines()]
        results = json.loads((source/'reports/evaluated_results.json').read_text())
        original = {'fleet': 3, 'capacity': 100,
                    'nodes': {i: [i, 0, int(i > 0), 0, 1000, 0] for i in range(101)}}
        rows[0]['routes'] = [{'vehicle': 2, 'nodes': [0, 1, 0, 0]}]
        rows[0]['objective_integer'] = None
        audit = public.check(original, rows[0]['routes'])
        results[0] = {**rows[0], 'outcome': 'FAIL', 'continuous_check': audit,
                      'original_distance': audit['distance'], 'encoding_cost_error': None,
                      'encoding_cost_error_bound': None}
        (source/'raw/results.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
        (source/'reports/evaluated_results.json').write_text(json.dumps(results))
        verification = json.loads((source/'evidence/verification.json').read_text())
        verification['checker_passed_count'] = 1
        (source/'evidence/verification.json').write_text(json.dumps(verification))
        with patch.dict(public.PROTOCOL_HASHES, {public.PUBLIC_FORMAT: digest}), patch.dict(
                public.PARAMETER_HASHES, {key: sha(b'synthetic no solver\n') for key in public.PARAMETER_HASHES}):
            public.import_public(self.store, source, public.PUBLIC_FORMAT, 'malformed-public')
        scene = route_scene(self.store, 'malformed-public', 'c101__250ms')
        source_run = RouteReader(self.store, 'malformed-public').get_run('c101__250ms')
        self.assertEqual(scene['status']['solution_status'], 'invalid')
        self.assertTrue(scene['status']['has_candidate'])
        self.assertFalse(scene['status']['full_service_success'])
        self.assertEqual(scene['vehicles'], [])
        self.assertIsNone(scene['metrics']['full_service_distance'])
        self.assertEqual(scene['metrics']['served_task_count'], 0)
        self.assertEqual(scene['unserved_task_ids'], source_run['unserved_task_ids'])
        self.assertEqual(len(scene['unserved_task_ids']), 99)
        self.assertNotIn(1, scene['unserved_task_ids'])
        self.assertTrue(any('not validated coverage' in note for note in scene['limitations']))

    def test_mature_no_solution_is_not_problem_infeasibility(self):
        _, source = write_mature_fixture(self.root/'mature-fixture')
        import_mature(self.store, source, 'mature')
        scene = route_scene(self.store, 'mature', 'fixture_impossible__250ms')
        self.assertEqual(scene['status']['solution_status'], 'no_solution')
        self.assertEqual(scene['status']['source_status'], 'no_solution_in_budget')
        self.assertFalse(scene['status']['has_candidate'])
        self.assertIsNone(scene['metrics']['total_distance'])

    def test_public_native_sparse_vehicle_id_is_preserved(self):
        source = self.root/'public'
        digest = write_public_fixture(source, public.PUBLIC_FORMAT)
        with patch.dict(public.PROTOCOL_HASHES, {public.PUBLIC_FORMAT: digest}), patch.dict(
                public.PARAMETER_HASHES, {key: sha(b'synthetic no solver\n') for key in public.PARAMETER_HASHES}):
            public.import_public(self.store, source, public.PUBLIC_FORMAT, 'public')
        scene = route_scene(self.store, 'public', 'c101__250ms')
        self.assertEqual([v['vehicle_id'] for v in scene['vehicles']], [2])
        self.assertEqual(scene['metrics']['task_count'], 100)
        self.assertEqual(scene['frame']['coordinate_system'], 'archived_benchmark_cartesian')
        self.assertEqual(scene['metrics']['recorded']['solve_wall_s'], 0.3)
        self.assertIsNone(scene['metrics']['recorded']['bks_gap_percent'])

    def test_actual_http_is_read_only_and_rejects_override_queries(self):
        server = make_server(self.store, self.root, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        path = '/api/v1/experiments/fixture/runs/fixture_possible.distance_first/route-scene'
        def request(url, method='GET'):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            connection.request(method, url)
            response = connection.getresponse(); data = json.loads(response.read())
            status = response.status; connection.close()
            return status, data
        try:
            before = self.store.path.read_bytes()
            self.assertEqual(request(path), (200, self.scene()))
            self.assertEqual(request(path+'?revision=1'), (200, self.scene()))
            self.assertEqual(request(path, 'POST')[0], 405)
            for query in ('revision=0', 'revision=abc', 'revision=', 'revision=1&revision=2',
                          'units=meters', 'simulation_ready=true', 'simulation_ready', 'frame=map'):
                self.assertEqual(request(path+'?'+query)[0], 400, query)
            self.assertEqual(request(path+'?revision=999')[0], 404)
            self.assertEqual(request(path.replace('distance_first', 'absent'))[0], 404)
            self.assertEqual(request(path.replace('fixture_possible.distance_first', '..%2Fx'))[0], 400)
            self.assertEqual(self.store.path.read_bytes(), before)
            self.assertEqual(request('/api/experiments/fixture/runs/fixture_possible.distance_first')[0], 200)
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    unittest.main()
