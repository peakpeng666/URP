"""Closed-schema package diagnostics; fixtures never disclose private strings."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
R = Path(__file__).resolve().parents[1]
S = importlib.util.spec_from_file_location('structured_projector', R / 'project_failure_code.py')
M = importlib.util.module_from_spec(S)
S.loader.exec_module(M)

def receipt():
    return dict(schema=1, code='APT_HTTP_ERROR', operation='index-download', exception_class='HTTPError', http_status=404, errno=None, returncode=None, suite='jammy', component='main')

class StructuredProjectionTests(unittest.TestCase):
    def test_package_producer_and_projector_share_closed_enums(self):
        spec = importlib.util.spec_from_file_location('package_receipt_contract', R / 'prepare_jammy_packages.py')
        producer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(producer)
        for producer_name, consumer_name in (
            ('DIAGNOSTIC_CODES', 'PACKAGE_CODES'),
            ('DIAGNOSTIC_OPERATIONS', 'PACKAGE_OPERATIONS'),
            ('DIAGNOSTIC_CLASSES', 'PACKAGE_CLASSES'),
            ('DIAGNOSTIC_ERRNOS', 'PACKAGE_ERRNOS'),
        ):
            self.assertEqual(getattr(producer, producer_name), getattr(M, consumer_name))
        producer.phase('native-solver')
        emitted = producer.failure_diagnostic(AttributeError('PRIVATE_SENTINEL /private/path'))
        self.assertEqual(M.validated_package_receipt(json.dumps(emitted)), emitted)
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(emitted))

    def test_accepts_exact_public_receipt(self):
        d = receipt()
        self.assertEqual(M.validated_package_receipt(json.dumps(d)), d)

    def test_rejects_unknown_or_private_strings_in_every_field(self):
        for key in receipt():
            with self.subTest(key=key):
                d = receipt(); d[key] = 'PRIVATE_SENTINEL /private/path https://private.invalid/token'
                self.assertIsNone(M.validated_package_receipt(json.dumps(d)))

    def test_rejects_added_private_field(self):
        d = receipt(); d['url'] = 'https://private.invalid/token'
        self.assertIsNone(M.validated_package_receipt(json.dumps(d)))

    def test_rejects_missing_fields(self):
        for key in receipt():
            d = receipt(); del d[key]
            self.assertIsNone(M.validated_package_receipt(json.dumps(d)))

    def test_rejects_boolean_numbers(self):
        for key in ('schema','http_status','returncode','errno'):
            d = receipt(); d[key] = True
            self.assertIsNone(M.validated_package_receipt(json.dumps(d)))

    def test_rejects_unbounded_numbers(self):
        for key,value in [('http_status',600),('http_status',99),('returncode',256),('returncode',-256),('errno',999999)]:
            d = receipt(); d[key] = value
            self.assertIsNone(M.validated_package_receipt(json.dumps(d)))

    def test_rejects_duplicate_keys_and_large_or_nested_input(self):
        raw = json.dumps(receipt())
        self.assertIsNone(M.validated_package_receipt(raw[:-1]+',"code":"APT_HTTP_ERROR"}'))
        for value in (' '*4097, '[]', '{"code": []}', '{'):
            self.assertIsNone(M.validated_package_receipt(value))

    def test_invalid_latest_receipt_does_not_reveal_previous_data(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'private.log'
            p.write_text(M.PACKAGE_MARKER+json.dumps(receipt())+'\n'+M.PACKAGE_MARKER+'{"url":"https://private.invalid/token"}\n')
            self.assertEqual(M.project_details('packages',str(p)), {'code':'UNKNOWN'})

    def test_json_cli_projects_only_safe_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'private.log'
            p.write_text('URLError: PRIVATE_SENTINEL /private/path https://private.invalid/token\n'+M.PACKAGE_MARKER+json.dumps(receipt())+'\n')
            result = subprocess.run([sys.executable,'-I','-B',str(R/'project_failure_code.py'),'--json','--stage','packages','--log',str(p)],capture_output=True,text=True,check=True)
            self.assertEqual(json.loads(result.stdout),receipt())
            self.assertEqual(result.stderr,'')
            for forbidden in ('PRIVATE_SENTINEL','/private/path','https://private.invalid','token'):
                self.assertNotIn(forbidden,result.stdout)

    def test_other_stage_does_not_adopt_package_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'private.log';p.write_text(M.PACKAGE_MARKER+json.dumps(receipt()))
            self.assertEqual(M.project_details('native_validation',str(p)),{'code':'UNKNOWN'})

if __name__ == '__main__': unittest.main()
