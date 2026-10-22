import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

R=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('capability_report',R/'report_capability_status.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
CODES={'schema':1,'authentication':{'pass_code':'AUTHENTICATED','codes':['AUTHENTICATED','TOOL_MISSING']},'capability':{'pass_code':'PROVED','codes':['PROVED','MAPPING_UNAVAILABLE']}}
RAW=json.dumps(CODES).encode()

class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.outcomes={s:'success' for s in M.STAGES}
        self.write('capability-preparation-status.json','PASS','AUTHENTICATED')
        self.write('capability-probe-status.json','PASS','PROVED')
    def tearDown(self):self.tmp.cleanup()
    def write(self,name,status,code):
        (self.root/name).write_text(json.dumps({'schema':1,'status':status,'code':code}))
    def project(self,raw=RAW):return M.project(self.root,self.outcomes,raw)
    def test_indexed_code_sets_match_producers(self):
        actual=json.loads((R/'public_codes.json').read_bytes())
        for section,name,attribute,ok in (('authentication','prepare_capability_inputs','PREPARATION_CODES','CAP_INPUTS_VERIFIED'),('capability','probe_namespace_capabilities','PROBE_CODES','OK')):
            spec=importlib.util.spec_from_file_location('codes_'+name,R/(name+'.py'))
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            self.assertEqual(actual[section],{'pass_code':ok,'codes':sorted(getattr(module,attribute))})

    def test_success(self):self.assertEqual(self.project(),'stage=capability status=PASS code=PROVED')
    def test_known_failure(self):
        self.outcomes['capability']='failure';self.write('capability-probe-status.json','FAIL','MAPPING_UNAVAILABLE')
        self.assertEqual(self.project(),'stage=capability status=FAIL code=MAPPING_UNAVAILABLE')
    def test_prior_stage_failure(self):
        self.outcomes['helper_tests']='failure'
        self.assertEqual(self.project(),'stage=helper_tests status=FAIL code=HELPER_TESTS_FAILED')
    def test_private_strings_never_emitted(self):
        self.outcomes['capability']='failure'
        for secret in ('SECRET_TOKEN','/home/private/data','https://private.invalid/token','RuntimeError: password','BAD\nTOKEN'):
            with self.subTest(secret=secret):
                self.write('capability-probe-status.json','FAIL',secret)
                self.assertEqual(self.project(),'stage=capability status=FAIL code=UNKNOWN')
    def test_wrong_schema_unknown_fields_duplicates(self):
        path=self.root/'capability-probe-status.json'
        for raw in (b'{"schema":true,"status":"PASS","code":"PROVED"}',b'{"schema":1,"status":"PASS","code":"PROVED","secret":"x"}',b'{"schema":1,"status":"PASS","code":"PROVED","code":"PROVED"}'):
            path.write_bytes(raw)
            self.assertEqual(self.project(),'stage=report status=FAIL code=UNKNOWN')
    def test_outcome_mismatch(self):
        self.outcomes['capability']='failure'
        self.assertEqual(self.project(),'stage=capability status=FAIL code=UNKNOWN')
    def test_missing_oversize_nonutf8(self):
        path=self.root/'capability-probe-status.json'
        for data in (None,b' '*4097,b'\xff'):
            if data is None:path.unlink()
            else:path.write_bytes(data)
            self.assertEqual(self.project(),'stage=report status=FAIL code=UNKNOWN')
    def test_nonregular_or_link(self):
        path=self.root/'capability-probe-status.json';path.unlink()
        original=self.root/'other';original.write_bytes(b'{}')
        path.symlink_to(original);self.assertEqual(self.project(),'stage=report status=FAIL code=UNKNOWN');path.unlink()
        os.link(original,path);self.assertEqual(self.project(),'stage=report status=FAIL code=UNKNOWN');path.unlink()
        os.mkfifo(path);self.assertEqual(self.project(),'stage=report status=FAIL code=UNKNOWN')
    def test_unverified_or_invalid_code_bytes(self):
        for data in (None,b'{}',b'[]',b'null',b'{"schema":1,"schema":1}',b' '*16385):
            self.assertEqual(self.project(data),'stage=report status=FAIL code=UNKNOWN')
    def test_untrusted_outcomes(self):
        self.outcomes['capability']='https://private.invalid/token'
        self.assertEqual(self.project(),'stage=report status=FAIL code=UNKNOWN')

if __name__=='__main__':unittest.main()
