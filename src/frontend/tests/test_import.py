"""Small adversarial archive fixtures; never modify research data."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from import_data import import_archive, safe_name

class ImportTests(unittest.TestCase):
    def test_paths(self):
        for name in ['../escape', '/abs', 'C:/windows', 'x\\y', 'a/../../x']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_name(name)
        self.assertEqual(str(safe_name('raw/record.json')), 'raw/record.json')

    def test_validation_precedes_writes_and_existing_data_is_immutable(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            archive = root / 'test.zip'
            entry = {'bytes': 4, 'sha256': hashlib.sha256(b'test').hexdigest()}
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('a.txt', b'test')
                z.writestr('MANIFEST.json', json.dumps({'files': {'a.txt': entry}}))
            expected = hashlib.sha256(archive.read_bytes()).hexdigest()
            report = root / 'report.json'
            target = root / 'research'
            import_archive(archive, target, report, expected)
            import_archive(archive, target, report, expected)
            (target / 'a.txt').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'refusing overwrite'):
                import_archive(archive, target, report, expected)
            self.assertEqual((target / 'a.txt').read_text(), 'changed')

    def test_corruption_refuses_import(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            archive = root / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('a.txt', 'bad')
                z.writestr('MANIFEST.json', json.dumps({'files': {'a.txt': {'bytes': 3, 'sha256': '0'*64}}}))
            with self.assertRaisesRegex(ValueError, 'MANIFEST mismatch'):
                import_archive(archive, root/'research', root/'report.json', hashlib.sha256(archive.read_bytes()).hexdigest())
            self.assertFalse((root/'research').exists())

if __name__ == '__main__':
    unittest.main()
