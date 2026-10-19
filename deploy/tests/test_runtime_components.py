"""Offline deployment guards; no sudo, package installation or experiments."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


fetch = module('fetch_f2c', ROOT / 'deploy/fetch-fields2cover.py')
cohort = module('check_cohort', ROOT / 'deploy/check-cohort.py')
runtime = module('check_runtime', ROOT / 'deploy/check-runtime.py')
WHEEL = 'vendor/wheels/fields2cover-2.1.0-cp312-cp312-linux_x86_64.whl'
MEMBER = 'project/src/lab/' + WHEEL
PAYLOAD = b'unit test wheel payload; never installed'


class WheelRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'src/lab/vendor').mkdir(parents=True)
        (self.root / 'setup').mkdir()
        self.target = self.root / 'src/lab' / WHEEL
        self.manifest = dict(wheel=WHEEL, wheel_sha256=hashlib.sha256(PAYLOAD).hexdigest())
        self.write_manifest()

    def write_manifest(self):
        (self.root / 'src/lab/vendor/fields2cover-manifest.json').write_text(json.dumps(self.manifest))

    def archive(self, entries):
        if not shutil.which('zstd'):
            self.skipTest('zstd unavailable; archive tests require zstd')
        raw = self.root / 'fixture.tar'
        with tarfile.open(raw, 'w') as tar:
            for name, kind, content in entries:
                entry = tarfile.TarInfo(name)
                if kind == 'link':
                    entry.type = tarfile.SYMTYPE
                    entry.linkname = content
                    tar.addfile(entry)
                else:
                    entry.size = len(content)
                    tar.addfile(entry, io.BytesIO(content))
        archive = self.root / fetch.ASSET
        subprocess.run(['zstd', '-q', '-f', str(raw), '-o', str(archive)], check=True)
        snapshot = dict(repository='peakpeng666/URP', release_tag='test',
                        assets=[dict(name=fetch.ASSET, sha256=fetch.sha256(archive), bytes=archive.stat().st_size)])
        (self.root / 'setup/platform-snapshot.json').write_text(json.dumps(snapshot))
        return archive

    def test_valid_archive_restores_only_wheel(self):
        archive = self.archive([('../../outside', 'file', b'bad'), (MEMBER, 'file', PAYLOAD)])
        self.assertEqual(fetch.obtain(self.root, archive), self.target)
        self.assertEqual(self.target.read_bytes(), PAYLOAD)
        self.assertFalse((self.root.parent / 'outside').exists())
        self.assertFalse((self.root / 'project').exists())

    def test_archive_hash_mismatch_leaves_no_wheel(self):
        archive = self.archive([(MEMBER, 'file', PAYLOAD)])
        archive.write_bytes(archive.read_bytes()[:-1] + b'x')
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            fetch.obtain(self.root, archive)
        self.assertFalse(self.target.exists())

    def test_wheel_hash_mismatch_leaves_no_wheel(self):
        archive = self.archive([(MEMBER, 'file', b'wrong')])
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            fetch.obtain(self.root, archive)
        self.assertFalse(self.target.exists())

    def test_symlink_member_rejected(self):
        archive = self.archive([(MEMBER, 'link', '/tmp/anything')])
        with self.assertRaisesRegex(ValueError, 'non-regular'):
            fetch.obtain(self.root, archive)
        self.assertFalse(self.target.exists())

    def test_duplicate_member_rejected(self):
        archive = self.archive([(MEMBER, 'file', PAYLOAD), (MEMBER, 'file', PAYLOAD)])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            fetch.obtain(self.root, archive)
        self.assertFalse(self.target.exists())

    def test_missing_wheel_rejected(self):
        archive = self.archive([('project/unused', 'file', PAYLOAD)])
        with self.assertRaisesRegex(ValueError, 'not present'):
            fetch.obtain(self.root, archive)

    def test_existing_wrong_wheel_is_not_overwritten(self):
        archive = self.archive([(MEMBER, 'file', PAYLOAD)])
        self.target.parent.mkdir(parents=True)
        self.target.write_bytes(b'user local bytes')
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            fetch.obtain(self.root, archive)
        self.assertEqual(self.target.read_bytes(), b'user local bytes')

    def test_check_only_never_downloads(self):
        self.archive([(MEMBER, 'file', PAYLOAD)])
        with self.assertRaisesRegex(ValueError, 'absent'):
            fetch.obtain(self.root, check_only=True)
        self.assertFalse((self.root / '.local-state').exists())

    def test_manifest_traversal_rejected(self):
        self.archive([(MEMBER, 'file', PAYLOAD)])
        self.manifest['wheel'] = '../outside.whl'
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'Unsafe'):
            fetch.obtain(self.root, check_only=True)

    def test_destination_parent_symlink_rejected(self):
        archive = self.archive([(MEMBER, 'file', PAYLOAD)])
        outside = self.root / 'outside'
        outside.mkdir()
        self.target.parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            fetch.obtain(self.root, archive)
        self.assertEqual(list(outside.iterdir()), [])


class CohortCheckerTests(unittest.TestCase):
    problem = dict(coordinates=[[0, 0], [3, 0], [3, 4]], demands=[0, 1, 1], capacity=2, K=2)

    def test_valid(self):
        self.assertTrue(cohort.check_incumbent(self.problem, dict(routes=[[0, 1, 2, 0]], cost=12)))

    def test_wrong_cost_or_duplicate_or_capacity(self):
        for incumbent in (dict(routes=[[0, 1, 2, 0]], cost=11),
                          dict(routes=[[0, 1, 1, 0]], cost=6),
                          dict(routes=[[0, True, 2, 0]], cost=12), None):
            self.assertFalse(cohort.check_incumbent(self.problem, incumbent))
        p = dict(self.problem, capacity=1)
        self.assertFalse(cohort.check_incumbent(p, dict(routes=[[0, 1, 2, 0]], cost=12)))


class EntryGuardTests(unittest.TestCase):
    def test_runtime_missing_executable_is_failure(self):
        result = runtime.command_check('missing', ['/does-not-exist/urp-python'])
        self.assertFalse(result['passed'])
        self.assertIn('FileNotFoundError', result['error'])

    def test_runtime_command_failure_preserves_exit_and_stderr(self):
        result = runtime.command_check('failure', ['bash', '-c', 'echo exact-error >&2; exit 17'])
        self.assertFalse(result['passed'])
        self.assertEqual(result['returncode'], 17)
        self.assertIn('exact-error', result['stderr'])

    def test_setup_help_and_invalid_combinations_do_not_install(self):
        script = str(ROOT / 'setup/ubuntu/setup.sh')
        self.assertEqual(subprocess.run(['bash', script, '--help'], capture_output=True).returncode, 0)
        for args in (['--components', 'bad'], ['--components'], ['--unknown'],
                     ['--components', 'full', '--fields2cover', 'skip']):
            result = subprocess.run(['bash', script, *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)

    def test_run_lab_missing_files_never_invokes_setup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dest = root / 'setup/ubuntu'
            dest.mkdir(parents=True)
            for name in ('run-lab.sh', 'env.sh'):
                shutil.copyfile(ROOT / 'setup/ubuntu' / name, dest / name)
            (dest / 'setup.sh').write_text('touch SHOULD_NOT_EXIST\n')
            result = subprocess.run(['bash', str(dest / 'run-lab.sh')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('--components full', result.stderr)
            self.assertFalse((root / 'SHOULD_NOT_EXIST').exists())


if __name__ == '__main__':
    unittest.main()
