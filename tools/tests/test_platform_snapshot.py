"""Publication must preserve measurements, protect credentials and restore safely."""
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('snapshot', Path(__file__).resolve().parents[1] / 'platform_snapshot.py')
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


class SnapshotTests(unittest.TestCase):
    def test_redaction_preserves_measurements_and_failures(self):
        raw = b'{"state":"failed","trajectory":[[1,2.5,3]],"key":"0123456789abcdef0123456789abcdef","risk_cost":1.667}'
        clean, count = snapshot.redact(raw)
        a, b = json.loads(raw), json.loads(clean)
        self.assertEqual(count, 1)
        self.assertEqual(b.pop('key'), '[REDACTED-AUTH]')
        a.pop('key')
        self.assertEqual(a, b)

    def test_scientific_hash_key_is_not_mistaken_for_web_auth(self):
        raw = json.dumps({'key': 'a' * 64, 'state': 'failed'}).encode()
        self.assertEqual(snapshot.redact(raw), (raw, 0))

    def test_xml_credentials_and_private_keys(self):
        self.assertNotIn(b'abcdef', snapshot.redact(b'<authorization_key>abcdef</authorization_key>')[0])
        with self.assertRaises(ValueError):
            snapshot.redact(b'-----BEGIN OPENSSH PRIVATE KEY-----')

    def test_wal_backup_keeps_rows_scrubs_freed_pages_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, dest = root / 'live.sqlite3', root / 'copy.sqlite3'
            with sqlite3.connect(source) as c:
                c.execute('PRAGMA journal_mode=WAL')
                c.execute('CREATE TABLE runs (id INTEGER PRIMARY KEY, data TEXT)')
                value = '{"state":"failed","password":"private-example","path":[1,2,3]}'
                c.execute('INSERT INTO runs(data) VALUES (?)', (value,))
                c.commit()
                stats = snapshot.database_snapshot(source, dest)
                self.assertEqual(c.execute('SELECT data FROM runs').fetchone()[0], value)
            self.assertEqual(stats['tables'], {'runs': 1})
            self.assertEqual(stats['redactions'], 1)
            self.assertNotIn(b'private-example', dest.read_bytes())
            with sqlite3.connect(dest) as c:
                data = json.loads(c.execute('SELECT data FROM runs').fetchone()[0])
                self.assertEqual(data['path'], [1, 2, 3])
                self.assertEqual(data['state'], 'failed')

    def test_unsafe_archive_names_and_links(self):
        for name in ['../escape', '/opt/ros/file', 'project/../../bad', 'project\\bad']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                snapshot.safe_name(name)
        for target in ['/etc/passwd', '../../../outside']:
            with self.assertRaises(ValueError):
                snapshot.safe_link('project/file', target)
        self.assertEqual(snapshot.safe_link('project/link', '../python/bin'), '../python/bin')

    @unittest.skipUnless(shutil.which('zstd'), 'zstd required for archive roundtrip')
    def test_uv_interpreter_alias_resolves_to_pinned_patch_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            interpreter = root / 'cpython-3.12.13'
            interpreter.mkdir()
            (interpreter / 'python').write_text('pinned-interpreter')
            alias = root / 'cpython-3.12'
            alias.symlink_to(interpreter, target_is_directory=True)
            env = root / 'venv'
            env.mkdir()
            (env / 'python').symlink_to(alias / 'python')
            cfg = root / 'spec.json'
            cfg.write_text(json.dumps({'metadata': {}, 'components': [
                {'name': 'python', 'sources': [{'path': str(env), 'prefix': 'project/venv'},
                                              {'path': str(interpreter), 'prefix': 'python/pinned'}]}]}))
            out, dest = root / 'archive', root / 'restored'
            snapshot.create(cfg, out)
            snapshot.verify(out / 'snapshot.json', dest)
            self.assertEqual((dest / 'project/venv/python').read_text(), 'pinned-interpreter')

    @unittest.skipUnless(shutil.which('zstd'), 'zstd required for archive roundtrip')
    def test_archive_roundtrip_and_corruption_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / 'source'
            src.mkdir()
            (src / 'trajectory.json').write_text('{"state":"failed","points":[[1,2],[3,4]]}')
            (src / 'uv.lock').write_text('lock survives')
            (src / 'link').symlink_to('trajectory.json')
            (src / '.env').write_text('SECRET=do-not-publish')
            cfg = root / 'spec.json'
            cfg.write_text(json.dumps({'metadata': {'base_commit': 'test'}, 'components': [
                {'name': 'state', 'sanitize': True, 'sources': [{'path': str(src), 'prefix': 'project'}]}]}))
            out = root / 'archives'
            snapshot.create(cfg, out)
            dest = root / 'restored'
            result = snapshot.verify(out / 'snapshot.json', dest)
            self.assertEqual(result['archive_members'], 3)
            self.assertEqual((dest / 'project/trajectory.json').read_bytes(), (src / 'trajectory.json').read_bytes())
            self.assertTrue((dest / 'project/link').is_symlink())
            self.assertFalse((dest / 'project/.env').exists())
            with self.assertRaises(FileExistsError):
                snapshot.verify(out / 'snapshot.json', dest)
            with (out / 'state.tar.zst').open('ab') as f:
                f.write(b'corruption')
            with self.assertRaises(ValueError):
                snapshot.verify(out / 'snapshot.json')

    @unittest.skipUnless(shutil.which('zstd'), 'zstd required for archive roundtrip')
    def test_immutable_dependency_source_is_not_rewritten_as_a_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); src = root / 'dependency'; src.mkdir()
            code = 'def authenticate(password=None):\n    return password\n'
            (src / 'auth.py').write_text(code)
            cfg = root / 'spec.json'
            cfg.write_text(json.dumps({'metadata': {}, 'components': [{'name': 'deps', 'sanitize': True,
                'sources': [{'path': str(src), 'prefix': 'project/deps', 'sanitize': False}]}]}))
            snapshot.create(cfg, root / 'archive')
            snapshot.verify(root / 'archive/snapshot.json', root / 'restored')
            self.assertEqual((root / 'restored/project/deps/auth.py').read_text(), code)


if __name__ == '__main__':
    unittest.main()
