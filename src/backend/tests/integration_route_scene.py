"""Real loopback HTTP across all four SYNTHETIC archive fixtures, never research data.

The integration schema check requires jsonschema in the test environment only.
The backend and its regular unit-test suite remain standard-library-only.
"""
import hashlib
import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import jsonschema

from backend import public_routes as public
from backend.mature_routes import import_mature
from backend.routes import import_vrptw
from backend.server import make_server
from backend.store import Store, sha
from mature_fixture import write_mature_fixture
from public_fixture import fixture as write_public_fixture
from route_fixture import write_fixture


class RouteSceneFixtureIntegration(unittest.TestCase):
    def test_four_formats_immutable_http_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = Store(root/'independent.sqlite3')
            sources = root/'sources'
            import_vrptw(store, write_fixture(sources/'legacy'), 'legacy')
            _, mature = write_mature_fixture(sources/'mature-fixture')
            import_mature(store, mature, 'mature')
            for experiment, format in [('public', public.PUBLIC_FORMAT), ('portfolio', public.PORTFOLIO_FORMAT)]:
                source = sources/experiment
                digest = write_public_fixture(source, format)
                with patch.dict(public.PROTOCOL_HASHES, {format: digest}), patch.dict(
                        public.PARAMETER_HASHES, {key: sha(b'synthetic no solver\n') for key in public.PARAMETER_HASHES}):
                    public.import_public(store, source, format, experiment)
            def source_hashes():
                return {str(path.relative_to(sources)): sha(path.read_bytes())
                        for path in sources.rglob('*') if path.is_file()}
            def archived_records():
                with store.connect() as db:
                    return (
                        list(map(tuple, db.execute('SELECT * FROM experiments ORDER BY id,revision'))),
                        list(map(tuple, db.execute('SELECT * FROM artifacts ORDER BY experiment_id,revision,id'))),
                    )
            before = source_hashes()
            records_before = archived_records()
            schema = json.loads((Path(__file__).parent.parent/'docs/route_scene_v1.schema.json').read_text())
            jsonschema.Draft202012Validator.check_schema(schema)
            validator = jsonschema.Draft202012Validator(schema)
            server = make_server(store, sources, 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            requests, scenes, points, lines = 0, 0, 0, 0
            states = set()
            def request(path, method='GET', raw=False):
                nonlocal requests
                requests += 1
                connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                connection.request(method, path)
                response = connection.getresponse(); blob = response.read()
                status, headers = response.status, dict(response.getheaders()); connection.close()
                if raw:
                    return status, headers, blob
                def reject_nonfinite(value):
                    raise ValueError('Nonfinite JSON: '+value)
                return status, headers, json.loads(blob, parse_constant=reject_nonfinite)
            def get(path):
                status, _, body = request(path)
                self.assertEqual(status, 200, (path, body))
                return body
            try:
                # Starting the service may create its job tables. It must leave
                # every imported experiment row and attachment byte unchanged.
                self.assertEqual(archived_records(), records_before)
                database_before = store.path.read_bytes()
                for experiment in ('legacy', 'mature', 'public', 'portfolio'):
                    existing = get('/api/experiments/'+experiment+'/runs?revision=1')
                    for run in existing['runs']:
                        run_id = run['run_id']
                        scene_path = f'/api/v1/experiments/{experiment}/runs/{run_id}/route-scene?revision=1'
                        scene = get(scene_path); validator.validate(scene)
                        original = get(scene['provenance']['source_run_url'])
                        self.assertEqual(scene['provenance']['run'], original['provenance'])
                        self.assertEqual(scene['provenance']['input'], original['input']['input_provenance'])
                        self.assertEqual(scene['semantics'], original['semantics'])
                        self.assertEqual(scene['status']['solution_status'], original['solution_status'])
                        self.assertEqual(scene['status']['source_status'], original['source_status'])
                        self.assertEqual(scene['unserved_task_ids'], original['unserved_task_ids'])
                        self.assertEqual(scene['recommendation']['status'], 'not_available')
                        self.assertFalse(scene['simulation_ready'])
                        self.assertIsNone(scene['frame']['meters_per_coordinate_unit'])
                        for exported, vehicle in zip(scene['vehicles'], original['vehicles']):
                            self.assertEqual(exported['vehicle_id'], vehicle['vehicle_id'])
                            self.assertEqual(exported['polyline'], vehicle['path_coordinates'])
                            self.assertEqual(exported['visit_node_ids'], vehicle['path_node_ids'])
                            self.assertEqual(exported['stops'], vehicle['stops'])
                            lines += 1
                        evidence = scene['provenance']['index_artifact']
                        status, headers, blob = request(evidence['url'], raw=True)
                        self.assertEqual(status, 200)
                        self.assertEqual(hashlib.sha256(blob).hexdigest(), evidence['sha256'])
                        self.assertEqual(headers['X-Content-SHA256'], evidence['sha256'])
                        self.assertEqual(request(scene_path, method='POST')[0], 405)
                        points += 1 + len(scene['task_nodes']); scenes += 1
                        states.add(scene['status']['solution_status'])
                self.assertEqual(scenes, 14)
                self.assertEqual(states, {'feasible', 'partial', 'invalid', 'infeasible', 'no_solution'})
                self.assertEqual(source_hashes(), before)
                self.assertEqual(archived_records(), records_before)
                self.assertEqual(store.path.read_bytes(), database_before)
            finally:
                server.shutdown(); server.server_close(); thread.join()
            report = {
                'status': 'PASS', 'evidence_type': 'synthetic_contract_fixture_only',
                'transport': 'actual_loopback_http', 'route_source_formats': 4,
                'scene_exports': scenes, 'http_requests': requests,
                'node_exports': points, 'vehicle_polylines': lines,
                'solution_statuses': sorted(states),
                'json_schema_validation': 'Draft 2020-12, all 14 scenes',
                'nonfinite_json_rejected': True, 'provenance_artifact_sha256_checked': True,
                'source_files_unchanged': True, 'database_unchanged_during_gets_and_rejected_posts': True,
                'solver_executed': False, 'ros_executed': False, 'gazebo_executed': False,
                'real_research_archives_revalidated': False, 'deployed': False,
            }
            report_path = os.environ.get('ROUTE_SCENE_INTEGRATION_REPORT')
            if report_path:
                Path(report_path).write_text(json.dumps(report, indent=2)+'\n')
            print(json.dumps(report))


if __name__ == '__main__':
    unittest.main()
