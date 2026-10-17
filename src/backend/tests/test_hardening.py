"""Boundary and concurrency regressions for the local data API."""
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from backend.server import make_server
from backend.store import Store, StoreError, safe_path
from test_backend import fixture


class StoreBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.package = self.root / 'package'
        self.package.mkdir()
        self.store = Store(self.root / 'data.sqlite3')
        (self.package / 'report.json').write_text('{"a":2.5,"b":1.0}')

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, descriptor):
        (self.package / 'experiment.json').write_text(json.dumps(descriptor))

    def test_malformed_nested_containers_have_atomic_validation_errors(self):
        bad_values = [('counts', [None]), ('artifacts', [None]),
                      ('metrics', [None]), ('counts', {}),
                      ('metrics', None), ('artifacts', 'report')]
        for key, value in bad_values:
            with self.subTest(key=key, value=value):
                descriptor = fixture()
                descriptor[key] = value
                self.write(descriptor)
                with self.assertRaises(StoreError):
                    self.store.import_package(self.package)
                self.assertEqual(self.store.list(), [])

    def test_bad_metric_objects_and_oversized_numbers_are_rejected(self):
        for field, value in [('source', []), ('comparison', []),
                             ('value', 10 ** 400)]:
            with self.subTest(field=field):
                descriptor = fixture()
                descriptor['metrics'][0][field] = value
                self.write(descriptor)
                with self.assertRaises(StoreError):
                    self.store.import_package(self.package)

    def test_artifact_response_headers_are_validated_before_import(self):
        for media in ['text/plain\r\nX-Injected: yes', 'text/plain\x00',
                      'application/中文', {}, '']:
            with self.subTest(media=media):
                descriptor = fixture()
                descriptor['artifacts'][0]['media_type'] = media
                self.write(descriptor)
                with self.assertRaises(StoreError):
                    self.store.import_package(self.package)
        self.assertEqual(self.store.list(), [])

    def test_path_dot_segments_nul_and_symlinks_are_rejected(self):
        for relative in ['report/../report.json', './report.json',
                         'dir/./report.json', 'report.json\x00']:
            with self.subTest(relative=relative), self.assertRaises(StoreError):
                safe_path(self.package, relative)
        (self.package / 'linked.json').symlink_to(self.package / 'report.json')
        with self.assertRaises(StoreError):
            safe_path(self.package, 'linked.json')

    def test_boolean_schema_and_invalid_revision_are_not_integer_ids(self):
        descriptor = fixture()
        descriptor['schema_version'] = True
        self.write(descriptor)
        with self.assertRaises(StoreError):
            self.store.import_package(self.package)
        self.write(fixture())
        self.store.import_package(self.package)
        for revision in [True, 0, -1, 1.0, '1']:
            with self.subTest(revision=revision), self.assertRaises(StoreError):
                self.store.get('model-fixture', revision)

    def test_concurrent_repeated_import_has_one_immutable_revision(self):
        self.write(fixture())
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.store.import_package(self.package), range(16)))
        self.assertEqual({row['revision'] for row in results}, {1})
        self.assertEqual(sum(not row['reused'] for row in results), 1)
        self.assertEqual(len(self.store.list()), 1)

    def test_concurrent_routing_identity_changes_cannot_create_a_second_revision(self):
        packages = []
        for index in range(2):
            package = self.root / ('identity-'+str(index))
            package.mkdir()
            descriptor = fixture()
            descriptor['routing'] = {'source_format':'test-format'}
            descriptor['provenance']['input_sha256'] = str(index)*64
            (package/'experiment.json').write_text(json.dumps(descriptor))
            (package/'report.json').write_text('{"a":2.5,"b":1.0}')
            packages.append(package)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.store.import_package, package) for package in packages]
            accepted, rejected = [], []
            for future in futures:
                try:
                    accepted.append(future.result())
                except StoreError as exc:
                    rejected.append(exc.code)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(rejected, ['experiment_identity_mismatch'])
        self.assertEqual(self.store.get('model-fixture')['revision'], 1)


class HTTPBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        package = self.root / 'package'
        package.mkdir()
        (package / 'experiment.json').write_text(json.dumps(fixture()))
        (package / 'report.json').write_text('{"a":2.5,"b":1.0}')
        self.store = Store(self.root / 'data.sqlite3')
        self.store.import_package(package)
        self.server = make_server(self.store, self.root, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            conn.request(method, path, body, headers or {})
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def test_nonloopback_host_is_rejected_even_without_origin(self):
        status, _, _ = self.request('GET', '/api/experiments', headers={'Host': 'untrusted.example'})
        self.assertEqual(status, 403)

    def test_ambiguous_query_and_json_keys_are_rejected(self):
        for path in ['/api/experiments/model-fixture?revision=1&revision=2',
                     '/api/experiments/model-fixture?revision=',
                     '/api/experiments?rev=1']:
            with self.subTest(path=path):
                self.assertEqual(self.request('GET', path)[0], 400)
        status, _, _ = self.request('POST', '/api/import',
            '{"package":"package","package":"other"}', {'Content-Type': 'application/json'})
        self.assertEqual(status, 400)

    def test_wrong_body_shape_does_not_drop_connection(self):
        for body in ['null', '[]', '{"items":[null,null]}']:
            with self.subTest(body=body):
                status, _, data = self.request('POST', '/api/compare', body,
                    {'Content-Type': 'application/json'})
                self.assertEqual(status, 400)
                self.assertIn('error', json.loads(data))

    def test_transfer_encoding_is_rejected_instead_of_misreading_body(self):
        status, _, _ = self.request('POST', '/api/import', '{"package":"package"}',
            {'Content-Type': 'application/json', 'Transfer-Encoding': 'chunked'})
        self.assertEqual(status, 400)


if __name__ == '__main__':
    unittest.main()
