"""Provenance/fail-closed tests use isolated development fixtures only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from convert_data import verified_sources, sha
from import_data import EXPECTED_SHA256

class SourceTrustTests(unittest.TestCase):
    def fixture(self, root):
        research = root/'research'; research.mkdir()
        artifacts = root/'artifacts'; artifacts.mkdir()
        manifest = {}
        for name in ['FREEZE.json','MODEL.json','MODEL_FREEZE.json','PROTOCOL.json']:
            p = research/name;p.write_text('{}')
            manifest[name] = {'sha256':sha(p),'bytes':2}
        (research/'MANIFEST.json').write_text(json.dumps({'files':manifest}))
        (artifacts/'import_report.json').write_text(json.dumps({'status':'PASS','archive_sha256':EXPECTED_SHA256}))
        return research, artifacts, sha(research/'MANIFEST.json')

    def test_pending_and_bound_pass(self):
        with tempfile.TemporaryDirectory() as d:
            r,a,h=self.fixture(Path(d))
            self.assertEqual(verified_sources(r,a,h)[2]['status'],'PENDING')
            report={'status':'PASS','passed':True,'sourceHashes':{p.name:sha(p) for p in r.iterdir()}}
            (a/'validation_report.json').write_text(json.dumps(report))
            self.assertEqual(verified_sources(r,a,h)[2]['status'],'PASS')
            report['sourceHashes']['MODEL.json']='0'*64
            (a/'validation_report.json').write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError,'Stale validation'):
                verified_sources(r,a,h)

    def test_fail_and_unmanifested_data_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r,a,h=self.fixture(Path(d))
            (a/'validation_report.json').write_text('{"status":"FAIL"}')
            with self.assertRaisesRegex(ValueError,'Scientific validation failed'):
                verified_sources(r,a,h)
            (a/'validation_report.json').unlink()
            (r/'rogue.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'membership differs'):
                verified_sources(r,a,h)

    def test_modified_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r,a,h=self.fixture(Path(d))
            (r/'MANIFEST.json').write_text('{"files":{}}')
            with self.assertRaisesRegex(ValueError,'MANIFEST hash'):
                verified_sources(r,a,h)

if __name__ == '__main__':
    unittest.main()
