"""Tests only the data grammar and artifact integrity. No solver/author execution."""
import ast
import hashlib
import json
import pathlib
import pickletools
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import extract_historical_data as hd


class HistoricalDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = ROOT / 'upstream' / 'historical'
        cls.raw = (cls.base / 'examples/bp_online/evaluation/testingdata/test_dataset_1k.pkl').read_bytes()
        cls.ops = list(pickletools.genops(cls.raw))

    def changed(self, pos, replacement):
        return self.raw[:pos] + replacement + self.raw[pos + len(replacement):]

    def reject(self, raw):
        with self.assertRaises(ValueError):
            hd.decode_numeric_pickle(raw)

    def test_pinned_three_datasets(self):
        expected = {
            '1k': (1000, [40115, 40257, 40038, 40316, 40066], '257d8ea253961a195e0d7addd74271418d662484e08be19b895c22d685e76a72'),
            '5k': (5000, [199556, 200701, 200919, 199952, 201699], '823eede011e20f8a0c39cf20a583fb2e1787918d989851421241b66d3ff75ef8'),
            '10k': (10000, [400376, 403682, 402637, 404298, 403869], '137eb9960b19c2149bc1c631e7b5e056af75abcf53dbb729d82ccd9ddccbdea0'),
        }
        for suffix, (n, sums, digest) in expected.items():
            raw = (self.base / f'examples/bp_online/evaluation/testingdata/test_dataset_{suffix}.pkl').read_bytes()
            data, audit = hd.decode_numeric_pickle_with_audit(raw)
            self.assertEqual(list(data), [n])
            self.assertEqual(len(data[n]), 5)
            self.assertEqual([len(x) for x in data[n]], [n] * 5)
            self.assertTrue(all(type(v) is int and 1 <= v <= 100 for x in data[n] for v in x))
            self.assertEqual([sum(x) for x in data[n]], sums)
            self.assertEqual(hd.hash_json(data[n]), digest)
            self.assertEqual(audit['original_item_dtype'], '<i4')
            self.assertEqual(audit['payload_globals_resolved'], 0)
            self.assertEqual(audit['payload_reducers_invoked'], 0)

    def test_artifact_and_raw_integrity(self):
        prov = json.loads((self.base / 'provenance.json').read_text())
        self.assertEqual(prov['commit'], hd.COMMIT)
        for row in prov['files']:
            raw = (self.base / row['path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
            self.assertEqual(hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest(), row['git_blob_sha1'])
        artifact = json.loads((ROOT / 'data/historical_numeric.json').read_text())
        self.assertEqual(len(artifact['instances']), 15)
        for instance in artifact['instances']:
            self.assertEqual(hd.hash_json(instance['items']), instance['items_sha256'])
            self.assertEqual(instance['source_dtype'], '<i4')

    def test_no_pickle_or_numpy_execution_apis(self):
        tree = ast.parse(pathlib.Path(hd.__file__).read_text())
        prohibited = {'eval', 'exec', '__import__', 'getattr', 'Unpickler', 'import_module'}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ''
                self.assertNotIn(name, prohibited)
                if name in ('load', 'loads'):
                    self.assertTrue(isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                                    and node.func.value.id == 'json')
            if isinstance(node, ast.Import):
                self.assertTrue(all(a.name not in ('pickle', 'numpy') for a in node.names))

    def test_wrong_global_symbol(self):
        self.reject(self.raw.replace(b'numpy.core.multiarray', b'xxxxx.core.multiarray', 1))
        self.reject(self.raw.replace(b'scalar', b'system', 1))

    def test_wrong_dtype(self):
        self.reject(self.raw.replace(b'i4', b'f4', 1))
        pos = next(p for op, arg, p in self.ops if op.name == 'SHORT_BINUNICODE' and arg == '<')
        self.reject(self.changed(pos + 2, b'>'))

    def test_wrong_scalar_range(self):
        pos = next(p for op, _, p in self.ops if op.name == 'SHORT_BINBYTES')
        for value in (-1, 0, 101):
            self.reject(self.changed(pos + 2, value.to_bytes(4, 'little', signed=True)))

    def test_wrong_payload_width(self):
        pos = next(p for op, _, p in self.ops if op.name == 'SHORT_BINBYTES')
        self.reject(self.changed(pos + 1, b'\x08'))

    def test_wrong_memo_reference(self):
        pos = next(p for op, _, p in self.ops if op.name == 'BINGET')
        self.reject(self.changed(pos + 1, b'\x06'))

    def test_wrong_callable_syntax(self):
        pos = next(p for op, _, p in self.ops if op.name == 'STACK_GLOBAL')
        self.reject(self.changed(pos, b'R'))
        pos = next(p for op, _, p in self.ops if op.name == 'BUILD')
        self.reject(self.changed(pos, b'R'))

    def test_wrong_list_assembly(self):
        pos = next(p for op, _, p in self.ops if op.name == 'APPENDS')
        self.reject(self.changed(pos, b'a'))

    def test_wrong_shape(self):
        pos = next(p for op, _, p in self.ops if op.name == 'BININT2')
        self.reject(self.changed(pos + 1, (2000).to_bytes(2, 'little')))

    def test_wrong_protocol(self):
        self.reject(self.changed(1, b'\x05'))

    def test_frame_overflow_or_gap(self):
        self.reject(self.changed(3, (len(self.raw) + 1).to_bytes(8, 'little')))
        size = int.from_bytes(self.raw[3:11], 'little')
        self.reject(self.changed(3, (size - 1).to_bytes(8, 'little')))

    def test_trailing_truncated_and_resource_bounds(self):
        self.reject(self.raw + b'.')
        self.reject(self.raw[:-1])
        self.reject(self.raw[:200])
        self.reject(b'0' * (hd.MAX_BYTES + 1))
        self.reject(bytearray(self.raw))
        self.reject(b'')

    def test_arbitrary_pickle_rejected(self):
        self.reject(b'\x80\x04cos\nsystem\n.')
        self.reject(b'\x80\x04csubprocess\nPopen\n.')

    def test_overlap_and_version_boundary(self):
        audit = json.loads((ROOT / 'data/historical_data_audit.json').read_text())
        pairs = audit['comparisons']
        overlaps = [p for p in pairs if p['exact_matches']]
        self.assertEqual(len(overlaps), 3)
        self.assertTrue(all(p['ordered_equal'] and len(p['exact_matches']) == 5 for p in overlaps))
        self.assertTrue(all(not p['full_shorter_prefix_matches'] for p in pairs))
        for size in ('1k', '5k', '10k'):
            pair = next(p for p in pairs if p['left'] == f'test_dataset_{size}' and p['right'] == f'current_test_dataset_{size}')
            self.assertFalse(pair['ordered_equal'])
            self.assertEqual(pair['exact_matches'], [])


if __name__ == '__main__':
    unittest.main()
