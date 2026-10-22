import copy
import json
import math
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from acceptance import derive, owned, signal_owned, verify_source
from public_summary import SOURCE, project

class AcceptanceTests(unittest.TestCase):
    def evidence(self):
        report = {'status':'PASS','shutdown':{'verified': True}}
        sim = {'run_id':'test','state':'succeeded','finished_utc':'private',
               'actual':{'ground_truth':[[0,0,0],[1,1,0]]},
               'metrics':{'tasks_total':5,'tasks_reached':5,'actual_length_m':1,
                          'duration_wall_s':2,'duration_sim_s':1,
                          'actual_map_check':{'collision_free':True,'checked':True}}}
        solution = {'run_id':'test','map_check':{'collision_free':True,'checked':True},
                    'process':{'source_identity_verified':True}, 'scenario_snapshot':{'id':'maze'},
                    'reproducibility':{'execution_sha256':'b'*64,'worker_environment_verified':True}}
        session = {'status':'PASS','remaining_owned_processes':[], 'abnormal_exits':[], 'assets':{'complete':True},'bridge_runtime':{'mode':'source_shutdown_join'},'compatibility':{'tf':'private','gui':'private'}}
        raw = {'source_sha': SOURCE,'harness_sha':'a'*40,'stage':'maze',
               'overlay_source_sha256':'c'*64,'overlay_binary_sha256':'d'*64,
               'remaining_owned_process_count':0,'process_exit_codes':{'gateway':0,'full_loop':0}}
        return report,sim,[solution],session,raw

    def valid(self): return derive(*self.evidence())

    def test_complete_physical_evidence_passes(self):
        self.assertEqual(project(self.valid(),{'exit_code':0,'cleanup_remaining':0,'forced_kill_count':0})['state'],'PASS')

    def test_ready_only_fails(self):
        raw=self.valid();raw['state']='PASS';raw['trajectory_samples']=None
        self.assertEqual(project(raw)['state'],'FAIL')

    def test_missing_diagnostics_are_null_not_zero(self):
        x=project(self.valid())
        for key in ('clock_gap_max_s','clock_backwards_count','odom_age_max_s','future_tf_error_count'):
            self.assertIsNone(x[key]);self.assertEqual(x['measurement_availability'][key],'not_measured')

    def test_success_requires_all_gates(self):
        from public_summary import BOOLS
        for key in BOOLS:
            for value in (None, False, 'true', 1):
                raw=self.valid();raw[key]=value
                self.assertEqual(project(raw)['state'],'FAIL',key)
        for key,value in [('tasks_reached',4),('tasks_total',0),('actual_length_m',0),('remaining_owned_process_count',1),('harness_sha',None)]:
            raw=self.valid();raw[key]=value;self.assertEqual(project(raw)['state'],'FAIL',key)

    def test_planned_map_unchecked_fails(self):
        for checked in (None, False, 1, 'true'):
            args = list(self.evidence())
            args[2][0]['map_check']['checked'] = checked
            self.assertEqual(project(derive(*args))['state'], 'FAIL')

    def test_bad_trajectory_fails(self):
        for points in ([], [[0,0,0],[1,0,0]], [[0,0,0],[1,float('nan'),0]], 'PRIVATE_MARKER'):
            args=list(self.evidence());args[1]['actual']['ground_truth']=points
            self.assertEqual(project(derive(*args))['state'],'FAIL')

    def test_projection_drops_raw_and_nonfinite(self):
        raw=self.valid();raw.update(error='/absolute/PRIVATE_MARKER',extra={'url':'SECRET'},state='PRIVATE_MARKER',
                                    actual_length_m=float('inf'),source_sha='PRIVATE_MARKER',clock_backwards_count=True)
        raw['process_exit_codes']['unknown']='SECRET'
        result=project(raw);text=json.dumps(result,allow_nan=False)
        self.assertNotIn('PRIVATE_MARKER',text);self.assertNotIn('SECRET',text);self.assertNotIn('/absolute',text)
        self.assertIsNone(result['actual_length_m']);self.assertIsNone(result['clock_backwards_count'])

    def test_wrapper_failure_overrides_simulation_pass(self):
        for runner in ({},{'exit_code':1,'cleanup_remaining':0},{'exit_code':0,'cleanup_remaining':1}):
            self.assertEqual(project(self.valid(),runner)['state'],'FAIL')
        self.assertEqual(project(self.valid(),{'exit_code':0,'cleanup_remaining':0,'forced_kill_count':0})['state'],'PASS')

    def test_source_wrong_commit_stops(self):
        with patch('runner.verify_worktree.subprocess.check_output',return_value=b'0'*40):
            with self.assertRaises(ValueError): verify_source(Path('/not-executed'))

    def test_public_cli_error_is_redacted(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'in.json';p.write_text('PRIVATE_MARKER malformed')
            run=subprocess.run([sys.executable,str(Path(__file__).with_name('public_summary.py')),'--input',str(p)],capture_output=True,text=True)
            self.assertEqual(run.returncode,1);self.assertNotIn('PRIVATE_MARKER',run.stdout+run.stderr)
            self.assertEqual(json.loads(run.stdout)['state'],'ERROR')

    def test_install_failure_without_summary_retains_supervisor_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = Path(tmp) / 'runner-status.json'
            status.write_text(json.dumps({'stage': 'installation', 'exit_code': 7,
                                         'cleanup_remaining': 0, 'error': '/PRIVATE_MARKER'}))
            run = subprocess.run([sys.executable, str(Path(__file__).with_name('public_summary.py')),
                                  '--input', str(Path(tmp) / 'absent-summary.json'),
                                  '--runner-status', str(status)], capture_output=True, text=True)
            result = json.loads(run.stdout)
            self.assertEqual(run.returncode, 1)
            self.assertEqual(result['state'], 'FAIL')
            self.assertEqual(result['runner_stage'], 'installation')
            self.assertEqual(result['runner_exit_code'], 7)
            self.assertEqual(result['runner_cleanup_remaining'], 0)
            self.assertIsNone(result['tasks_total'])
            self.assertNotIn('PRIVATE_MARKER', run.stdout + run.stderr)

    def test_runner_stage_is_fixed_enum(self):
        for stage, expected in [('installation', 'installation'), ('simulation', 'simulation'),
                                ('/PRIVATE_MARKER', 'unknown'), (None, 'unknown'), ({}, 'unknown')]:
            self.assertEqual(project({}, {'stage': stage})['runner_stage'], expected)

    def test_real_process_marker_cleanup(self):
        token=secrets.token_hex(24)
        p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],env=dict(os.environ,URP_ACCEPTANCE_OWNER=token))
        try:
            self.assertIn(p.pid,[pid for pid,_ in owned(token)])
            self.assertEqual(owned('unrelated-'+token),[])
            signal_owned(token,signal.SIGTERM);p.wait(timeout=5)
            self.assertEqual(owned(token),[])
        finally:
            if p.poll() is None: p.kill();p.wait()




class AptPublicProjectionTests(unittest.TestCase):
    def test_public_apt_projection_is_strict(self):
        from public_summary import apt_projection
        edge={'package':'root','package_version':'1.0','relation':'depends','dependency':'lib-a','version_relation':'ge','dependency_version':'2.0'}
        self.assertEqual(apt_projection({'status':'verified','dependencies':[edge]}),('verified',[edge]))
        for bad in [dict(edge,url='PRIVATE_URL'),dict(edge,package='PRIVATE/PATH'),dict(edge,relation='PRIVATE'),dict(edge,dependency_version='http://private'),dict(edge,version_relation='any')]:
            result=apt_projection({'status':'verified','dependencies':[bad]})
            self.assertEqual(result,('invalid_projection',[]))
            self.assertNotIn('PRIVATE',json.dumps(result))
        self.assertEqual(apt_projection({'status':'verified','dependencies':[edge]*21}),('invalid_projection',[]))
    def test_missing_or_nonzero_forced_kill_cannot_pass(self):
        # Even a nominal PASS input cannot bypass missing supervisor evidence.
        raw={'state':'PASS'}
        for runner in (None,{}, {'exit_code':0,'cleanup_remaining':0}, {'exit_code':0,'cleanup_remaining':0,'forced_kill_count':1}):
            self.assertEqual(project(raw,runner)['state'],'FAIL')

if __name__ == '__main__': unittest.main()
