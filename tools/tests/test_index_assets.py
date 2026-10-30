"""Asset indexes must retain verified copies and reject a copy for different source bytes."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('index_assets', Path(__file__).resolve().parents[1] / 'index_assets.py')
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class AssetCopyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.payload = self.repo / 'experiment.zip'
        self.payload.write_bytes(b'controlled archive bytes')
        for command in [ ['init', '-q'], ['add', '.'],
                         ['-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture'] ]:
            subprocess.run(['git', *command], cwd=self.repo, check=True)
        self.oid = subprocess.check_output(['git', 'rev-parse', 'HEAD:experiment.zip'], cwd=self.repo, text=True).strip()
        self.registry = self.root / 'copies.json'
        self.copy = {'asset_path': 'experiment.zip', 'state': 'restore-verified',
                     'url': 'https://drive.example/verified', 'git_blob_sha1': self.oid,
                     'sha256': hashlib.sha256(self.payload.read_bytes()).hexdigest(), 'restore_evidence': 'fixture roundtrip'}

    def generate(self, copy):
        self.registry.write_text(json.dumps({'copies': [copy]}))
        output = self.root / 'index'
        with patch.object(assets, 'ROOT', self.repo):
            assets.index('HEAD', output, self.registry)
        with (output / 'assets.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        return rows, json.loads((output / 'inventory.json').read_text())

    def test_reindex_retains_verified_copy_without_calling_it_migrated(self):
        rows, summary = self.generate(self.copy)
        self.assertEqual(rows[0]['external_copy'], self.copy['url'])
        self.assertEqual(rows[0]['external_sha256'], self.copy['sha256'])
        self.assertEqual(summary['verified_external_copies'], 1)
        self.assertEqual(summary['migrated_assets'], 0)
        self.assertEqual(summary['third_party_directories'], 0)

    def test_metadata_only_copy_is_not_promoted_to_verified(self):
        rows, summary = self.generate({**self.copy, 'state': 'uploaded-not-restored'})
        self.assertEqual(rows[0]['external_copy'], '')
        self.assertEqual(summary['external_copy_candidates'], 1)
        self.assertEqual(summary['verified_external_copies'], 0)

    def test_wrong_source_or_missing_restore_evidence_is_rejected(self):
        for field, value in [('git_blob_sha1', '0' * 40), ('restore_evidence', '')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.generate({**self.copy, field: value})
            output = self.root / 'index'
            if output.exists():
                self.assertEqual(list(output.iterdir()), [])
                output.rmdir()


if __name__ == '__main__':
    unittest.main()
