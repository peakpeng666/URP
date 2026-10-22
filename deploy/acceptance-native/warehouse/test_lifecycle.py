import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from warehouse_lifecycle import drive, physical_evidence
from warehouse_public_summary import project, HASHES, BOOLS
from historical_input import SOURCE

PLAN={'path':[[0,0],[1,0]],'tasks':[{'task':i,'label':str(i),'xy':[i,0]} for i in range(5)],'budget_s':649.6}

class Clock:
    def __init__(self):self.now=0
    def clock(self):return self.now
    def sleep(self,n):self.now+=n

class API:
    def __init__(self,case='success'):
        self.case=case;self.calls=[];self.stopping=False
    def __call__(self,method,path,data=None,timeout=5):
        self.calls.append((method,path,data))
        if method=='DELETE':self.stopping=True;return {'phase':'stopping'}
        if path=='/sim/session':
            if self.case=='start_uncertain':raise TimeoutError('private start error')
            return {'phase':'starting'}
        if path=='/sim/state':
            if self.stopping:return {'phase':'failed' if self.case=='cleanup_failed' else 'stopped','session_id':'sim_other' if self.case=='cleanup_identity_changed' else None,'errors':[]}
            return {'phase':'failed' if self.case=='startup_failed' else 'ready','session_id':'sim_test'}
        if method=='POST' and path=='/sim/runs':
            row={'run_id':'replay_id','session_id':'sim_test','sim_run_id':'sim_run_test','planned':{'path':copy.deepcopy(PLAN['path'])},'tasks':copy.deepcopy(PLAN['tasks'])}
            if self.case=='plan_changed':row['planned']['path'][0][0]=9
            if self.case=='identity_changed':row['run_id']='other'
            return row
        if path=='/sim/runs/sim_run_test':
            if self.case=='timeout':return {'state':'executing'}
            return {'run_id':'replay_id','session_id':'sim_test','sim_run_id':'sim_run_test','state':'failed' if self.case=='sim_failed' else 'succeeded','finished_utc':'now',
                    'planned':{'path':copy.deepcopy(PLAN['path'])},'tasks':[dict(t,state='reached') for t in PLAN['tasks']],
                    'mode':'follow_path','localization':{'mode':'ground_truth'},'world':'warehouse'}
        raise AssertionError('unexpected API path')

class LifecycleTests(unittest.TestCase):
    def run_case(self,case,guard=None):
        api=API(case);clock=Clock();saved={}
        result=drive(api,'replay_id',PLAN,guard or (lambda:None),lambda name,data:saved.update({name:data}),clock.clock,clock.sleep,overall=1000)
        return result,api,saved

    def test_success_uses_original_sim_api_no_solve_and_stops(self):
        result,api,_=self.run_case('success');self.assertTrue(result['passed'])
        paths=[path for _,path,_ in api.calls];self.assertNotIn('/solve',paths)
        self.assertIn(('DELETE','/sim/session',None),api.calls)
        start=next(body for method,path,body in api.calls if path=='/sim/session' and method=='POST')
        self.assertEqual(start['localization'],'ground_truth');self.assertFalse(start['gui']);self.assertFalse(start['rviz'])
        self.assertEqual(start['spawn']['yaw'],1.570796)

    def test_every_failure_attempts_session_cleanup_and_never_passes(self):
        for case in ('start_uncertain','startup_failed','plan_changed','identity_changed','cleanup_identity_changed','timeout','sim_failed','cleanup_failed'):
            result,api,_=self.run_case(case)
            self.assertFalse(result['passed'],case);self.assertIn(('DELETE','/sim/session',None),api.calls,case)

    def test_guard_drift_before_dispatch_stops_without_sim_run(self):
        count=0
        def guard():
            nonlocal count;count+=1
            if count==2:raise ValueError('map drift')
        result,api,_=self.run_case('success',guard)
        self.assertFalse(result['passed']);self.assertNotIn('/sim/runs',[p for _,p,_ in api.calls])
        self.assertTrue(api.stopping)

    def test_success_evidence_requires_motion_and_actual_map_check(self):
        life,_,_=self.run_case('success');sim=life['result'];sim['actual']={'ground_truth':[[0,0,0],[1,1,0]]}
        sim['metrics']={'tasks_total':5,'tasks_reached':5,'actual_length_m':1,'actual_map_check':{'checked':True,'collision_free':True}}
        session={'status':'PASS','remaining_owned_processes':[],'abnormal_exits':[],'errors':[],
                 'assets':{'complete':True},'compatibility':{'tf':'private','gui':'private'},'bridge_runtime':{'mode':'source_shutdown_join'}}
        row=physical_evidence(sim,session,life,PLAN);self.assertTrue(row['trajectory_motion_verified']);self.assertTrue(row['cleanup_pass'])
        sim['actual']['ground_truth']=[[0,0,0],[1,0,0]]
        self.assertFalse(physical_evidence(sim,session,life,PLAN)['trajectory_motion_verified'])
        self.assertTrue(row['execution_mode_verified'])
        sim['localization']={'mode':'amcl'}
        self.assertFalse(physical_evidence(sim,session,life,PLAN)['execution_mode_verified'])
        session['remaining_owned_processes']=[123]
        self.assertFalse(physical_evidence(sim,session,life,PLAN)['cleanup_pass'])

    def good(self):
        return {'state':'PASS','source_sha':SOURCE,'harness_sha':'a'*40,
                **{k:'b'*64 for k in HASHES},**{k:True for k in BOOLS},
                'tasks_total':5,'tasks_reached':5,'trajectory_samples':2,'actual_length_m':1,
                'remaining_owned_process_count':0,'gateway_exit_code':0,'physical_budget_s':649.6,
                'historical_resource_count':45,'current_resource_count':45,'missing_resource_count':0,
                'additional_resource_count':0,'changed_resource_count':0}

    def test_projection_replay_pass_has_no_fake_solver_or_full_loop(self):
        result=project(self.good(),require_runner=False);self.assertEqual(result['state'],'PASS');self.assertFalse(result['solver_executed'])
        self.assertNotIn('full_loop',json.dumps(result));self.assertEqual(result['route_origin'],'historical_fixed_witness')

    def test_private_then_public_projection_needs_runner_receipt(self):
        stage=project(self.good(),require_runner=False)
        self.assertEqual(stage['state'],'PASS')
        self.assertEqual(project(stage)['state'],'FAIL')
        good={'exit_code':0,'cleanup_remaining':0,'forced_kill_count':0}
        self.assertEqual(project(stage,good)['state'],'PASS')
        for key in good:
            bad=dict(good);bad[key]=1
            self.assertEqual(project(stage,bad)['state'],'FAIL')

    def test_all_boolean_evidence_gates_required(self):
        for field in BOOLS:
            row=self.good();row[field]=None;self.assertEqual(project(row,require_runner=False)['state'],'FAIL',field)
        for field in HASHES:
            row=self.good();row[field]=None;self.assertEqual(project(row,require_runner=False)['state'],'FAIL',field)

    def test_missing_resources_and_wrapper_failure_override_pass(self):
        raw=self.good();raw['resources_match_historical']=None
        self.assertEqual(project(raw)['state'],'FAIL')
        self.assertEqual(project(self.good(),{'exit_code':0,'cleanup_remaining':1})['state'],'FAIL')

    def test_projection_drops_raw_strings_and_missing_measurements_stay_null(self):
        raw=self.good();raw.update(error='/private/PATH',current_execution_sha256='SECRET',duration_sim_s=float('nan'))
        result=project(raw);text=json.dumps(result,allow_nan=False)
        self.assertNotIn('SECRET',text);self.assertNotIn('/private',text)
        self.assertIsNone(result['duration_sim_s']);self.assertEqual(result['measurement_availability']['duration_sim_s'],'not_measured')

    def test_missing_summary_keeps_runner_diagnostics(self):
        result=project({}, {'stage':'installation','exit_code':7,'cleanup_remaining':0})
        self.assertEqual(result['runner_exit_code'],7);self.assertEqual(result['runner_stage'],'installation')
        self.assertEqual(result['state'],'FAIL')


class MapBindingTests(unittest.TestCase):
    def test_live_map_snapshot_binds_yaml_and_image(self):
        from warehouse_acceptance import map_snapshot
        class Cached:
            def __call__(self,world):return grid
            def cache_clear(self):self.cleared=True
        with tempfile.TemporaryDirectory() as tmp:
            grid=Mock();grid.yaml=Path(tmp)/'map.yaml';grid.image_path=Path(tmp)/'map.pgm'
            grid.yaml.write_bytes(b'configuration');grid.image_path.write_bytes(b'pixels')
            maps=Mock();maps.load=Cached();maps._SIGNATURES={};maps.fingerprint=lambda _: 'a'*64
            first=map_snapshot(maps)
            grid.image_path.write_bytes(b'changed pixels')
            self.assertNotEqual(map_snapshot(maps)['current_map_bytes_sha256'], first['current_map_bytes_sha256'])
            self.assertTrue(maps.load.cleared)

if __name__=='__main__':unittest.main()
