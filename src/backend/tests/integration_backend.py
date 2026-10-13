"""Opt-in checks against the five real packages from the pinned private Drive archive.

Missing packages fail explicitly; synthetic data is never substituted.
"""
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from backend.store import Store

class RealPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name) / 'store.sqlite3')
        self.package_root = Path(os.environ.get('RESEARCH_CONSOLE_PACKAGE_ROOT', 'packages')).resolve()

    def test_real_selector_budget_and_no_source_changes(self):
        for name in ['selector','budget','fleet','turns','bpp-history']:
            p=self.package_root/name
            self.assertTrue((p/'experiment.json').is_file(), f'Missing real package: {p}; restore the pinned Drive package first')
            before={f.relative_to(p).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()}
            receipt=self.store.import_package(p);d=self.store.get(receipt['id']);self.assertEqual(d['status'],'completed')
            self.assertEqual(before,{f.relative_to(p).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()})
        selector=self.store.get('selector');counts={(c['unit'],c['scope']):c['value'] for c in selector['counts']};self.assertEqual(counts[('fit','offline_training')],560);self.assertEqual(counts[('run','new_policy')],0)
        r=self.store.compare([dict(experiment_id='selector',metric_id=f'family_holdout-{n}-delta_vs_subset_sbs') for n in [5,40]])
        self.assertAlmostEqual(r['items'][0]['value'],-13.512962962962963);self.assertAlmostEqual(r['items'][1]['value'],30.518518518518512)
        budget=self.store.get('budget');self.assertEqual(next(c['value'] for c in budget['counts'] if c['unit']=='trajectory' and c['scope']=='formal'),288)
        self.assertTrue(any(a['filename']=='ANALYSIS_LAUNCH_ATTEMPT_1.json' for a in budget['artifacts']))
        self.assertEqual(budget['failures'][0]['status'],'recovered')
        self.assertIn('/usr/bin/time',budget['failures'][0]['reason'])
        self.assertEqual(budget['status'],'completed')
        self.assertIsNone(self.store.get('bpp-history')['failures'])


if __name__ == '__main__':
    unittest.main()
