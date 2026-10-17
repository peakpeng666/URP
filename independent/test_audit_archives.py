import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from audit_archives import extract_main_archives, retry_audit
from validate import sha


class ArchiveBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.output = self.root / 'output'
        self.output.mkdir()

    def archive(self, member_name='run/result.json'):
        path = self.source / 'main-results.tar.xz'
        data = b'{"status":"NO_SOLUTION"}'
        with tarfile.open(path, 'w:xz') as archive:
            entry = tarfile.TarInfo(member_name)
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
        manifest = {'archives': [{'file': path.name, 'bytes': path.stat().st_size,
                                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}]}
        (self.source / 'manifest.json').write_text(json.dumps(manifest))
        return path

    def test_verified_archive_extracts_without_changing_source(self):
        path = self.archive()
        original = path.read_bytes()
        evidence = extract_main_archives(self.source, self.output)
        self.assertEqual(evidence[0]['terminal_results'], 1)
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(json.loads((self.output / 'main-results/run/result.json').read_text())['status'], 'NO_SOLUTION')

    def test_changed_archive_and_escaping_member_are_rejected(self):
        path = self.archive()
        path.write_bytes(path.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            extract_main_archives(self.source, self.output)
        self.archive('../escaped.json')
        with self.assertRaisesRegex(ValueError, 'Unsafe archive member'):
            extract_main_archives(self.source, self.output)
        self.assertFalse((self.output / 'escaped.json').exists())

    def test_retry_is_bound_to_original_claim_not_same_key_in_retry_registry(self):
        raw=self.output
        key=dict(plan_sha256='plan',instance_sha256='instance',algorithm='a',seed=1,budget_seconds=5,
                 contract={'id':'fixed','K':1,'fixed_cost':0},solver_source_sha256='source')
        old=raw/'b03/lane/run-registry/key.json';old.parent.mkdir(parents=True)
        claim=dict(key=key,output='/original/b03/lane/run',claimed_utc='2026-10-15T12:19:38Z')
        old.write_text(json.dumps(claim))
        retry_claim=raw/'b05/lane/run-registry/key.json';retry_claim.parent.mkdir(parents=True)
        retry_claim.write_text(json.dumps(dict(claim,output='/original/b05/lane/run',claimed_utc='2026-10-15T12:34:46Z')))
        (raw/'b03/adjudication.json').write_text(json.dumps(dict(schema='urp-cvrp-interrupted-claims-v1',
                                                              claimed_without_result=[dict(claim,claim='/original/b03/lane/run-registry/key.json')])))
        manifest=raw/'b05/lane/resource-manifest.json'
        manifest.write_text(json.dumps(dict(infrastructure_retries={'1':{'claim_sha256':sha(old)}},
                                            retry_selection_policy='Exactly one retry; no score-dependent selection.')))
        result=raw/'b05/lane/run/result.json';result.parent.mkdir()
        record=dict(key,case_id='c',retry_parent_claim_sha256=sha(old),resource_manifest_sha256=sha(manifest))
        result.write_text(json.dumps(record))
        evidence,errors=retry_audit(raw,{result:record})
        self.assertEqual(errors,[])
        self.assertEqual(len(evidence),1)
        self.assertTrue(evidence[0]['policy_bound_to_retry'])
        original_result=raw/'b03/lane/run/result.json';original_result.parent.mkdir()
        original_result.write_text('{}')
        _,errors=retry_audit(raw,{result:record})
        self.assertEqual(len(errors),1)


if __name__ == '__main__':
    unittest.main()
