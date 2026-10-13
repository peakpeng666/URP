"""Synthetic lifecycle checks for the copied real supervisor; standard library only."""
import hashlib
import io
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
from types import SimpleNamespace
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
ORIGINAL_SUPERVISOR=BASE/'tests/fixtures/original_supervise.py'
SUPERVISOR=BASE/'supervise.py'
spec=importlib.util.spec_from_file_location('candidate_supervise',SUPERVISOR)
supervise=importlib.util.module_from_spec(spec)
spec.loader.exec_module(supervise)
EVIDENCE=[]

LEAF="""import os,signal,sys,time
from pathlib import Path
signal.signal(signal.SIGTERM,signal.SIG_IGN)
Path(sys.argv[1]).write_text(str(os.getpid()))
time.sleep(30)
"""
DESCENDANT="""import json,os,signal,subprocess,sys,time
from pathlib import Path
signal.signal(signal.SIGTERM,signal.SIG_IGN)
leaf_ready=Path(sys.argv[1]+'.leaf')
leaf=subprocess.Popen([sys.executable,'-B','-c',sys.argv[2],str(leaf_ready)])
while not leaf_ready.exists():time.sleep(.005)
Path(sys.argv[1]).write_text(json.dumps([os.getpid(),int(leaf_ready.read_text())]))
time.sleep(30)
"""
WORKER="""import json,os,signal,subprocess,sys,time
from pathlib import Path
req=json.loads(sys.argv[1]); mode=req['mode']; info=Path(req['info'])
signal.signal(signal.SIGTERM,signal.SIG_DFL if mode=='term' else signal.SIG_IGN)
pids=[os.getpid()]
if mode in {'timeout_tree','success_tree','error_tree'}:
    ready=Path(str(info)+'.descendant')
    child=subprocess.Popen([sys.executable,'-B','-c',req['descendant'],str(ready),req['leaf']])
    while not ready.exists():time.sleep(.005)
    pids+=json.loads(ready.read_text())
info.write_text(json.dumps({'pids':pids,'pgid':os.getpgid(0),'sid':os.getsid(0)}))
if mode in {'timeout','timeout_tree','term'}:time.sleep(30)
elif mode in {'exception','error_tree'}:raise RuntimeError('synthetic worker exception')
elif mode=='valid_result':
    result={'internal_before_serialization_cpu_s':0.,'internal_before_serialization_wall_s':0.,'outcome':'synthetic_valid'}
    (Path(__file__).parent/'raw'/f"{req['run_id']}.result.json").write_text(json.dumps(result))
elif mode=='bad_result':
    (Path(__file__).parent/'raw'/f"{req['run_id']}.result.json").write_text('{invalid json')
"""

class SupervisorLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        supervise.enable_subreaper()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='supervise-synthetic-')
        self.root=Path(self.temp.name)
        self.worker=self.root/'worker.py'
        self.worker.write_text(WORKER,encoding='utf-8')
        self.processes=[]
        self.previous_alarm=signal.signal(signal.SIGALRM,self.wall_limit)
        signal.setitimer(signal.ITIMER_REAL,4.)

    @staticmethod
    def wall_limit(signum,frame):
        raise TimeoutError('Independent four-second test wall limit')

    def tearDown(self):
        signal.setitimer(signal.ITIMER_REAL,0.)
        # Fixed fixture: at most two descendant spawns, or four processes in
        # the baseline/unrelated-child comparisons. Never generate a fork loop.
        deadline=time.monotonic()+2
        try:
            for proc in self.processes:
                try:
                    os.waitid(os.P_PGID,proc.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
                except ChildProcessError:continue
                try:os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError:pass
            for proc in self.processes:
                while time.monotonic()<deadline:
                    try:pid,status,_=os.wait4(-proc.pid,os.WNOHANG)
                    except ChildProcessError:break
                    if pid==proc.pid:proc.returncode=os.waitstatus_to_exitcode(status)
                    if not pid:time.sleep(.01)
                with self.assertRaises(ChildProcessError):os.wait4(-proc.pid,os.WNOHANG)
        finally:
            signal.signal(signal.SIGALRM,self.previous_alarm)
            self.temp.cleanup()

    def request(self,mode,index=0):
        return {'run_id':f'synthetic_{index}','mode':mode,'info':str(self.root/f'pids_{index}.json'),
                'descendant':DESCENDANT,'leaf':LEAF}

    def spawn(self,req):
        proc=subprocess.Popen([sys.executable,'-B',str(self.worker),json.dumps(req)],
                              start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.processes.append(proc)
        self.assertLessEqual(len(self.processes),8,'Finite task launch cap')
        return proc

    def assert_gone(self,pids):
        for pid in pids:
            with self.assertRaises(ProcessLookupError,msg=f'PID {pid} still exists, possibly as a zombie'):
                os.kill(pid,0)

    def observe(self,proc,req,record):
        info=json.loads(Path(req['info']).read_text())
        self.assertLessEqual(len(info['pids']),3,'Fixed fixture process cap')
        self.assertEqual(info['pgid'],proc.pid)
        self.assertEqual(info['sid'],proc.pid)
        self.assertTrue(record['reaped'])
        self.assertTrue(record['process_group_reaped'])
        self.assertEqual(record['returncode'],proc.returncode)
        self.assert_gone(info['pids'])
        with self.assertRaises(ChildProcessError):os.wait4(proc.pid,os.WNOHANG)
        EVIDENCE.append({'test':self.id(),'mode':req['mode'],'all_observed_pids_gone':True,
                         'observed_pids':info['pids'],'exit_record':record})
        return info

    def run_mode(self,mode,index=0,reason='child_wall_limit'):
        req=self.request(mode,index);proc=self.spawn(req);start=time.monotonic()
        record=supervise.wait_for_worker(proc,lambda:reason if time.monotonic()-start>.35 else None)
        info=self.observe(proc,req,record)
        return record,info

    def test_normal_completion(self):
        record,_=self.run_mode('normal')
        self.assertEqual(record['returncode'],0)
        self.assertFalse(record['watchdog_killed'])

    def test_worker_exception_records_nonzero_exit(self):
        record,_=self.run_mode('exception')
        self.assertEqual(record['returncode'],1)
        self.assertFalse(record['watchdog_killed'])

    def test_timeout_ignoring_sigterm_escalates_to_sigkill(self):
        record,_=self.run_mode('timeout')
        self.assertEqual(record['returncode'],-signal.SIGKILL)
        self.assertTrue(record['watchdog_killed'])
        self.assertTrue(record['cleanup_sigkill_sent'])
        self.assertEqual(record['kill_reason'],'child_wall_limit')

    def test_timeout_reaps_two_descendant_generations(self):
        record,info=self.run_mode('timeout_tree')
        self.assertEqual(record['returncode'],-signal.SIGKILL)
        self.assertEqual(len(info['pids']),3)
        self.assertEqual({item['pid'] for item in record['adopted_descendants']},set(info['pids'][1:]))
        self.assertTrue(all(item['returncode']==-signal.SIGKILL for item in record['adopted_descendants']))

    def test_successful_leader_cannot_leave_descendants(self):
        record,_=self.run_mode('success_tree')
        self.assertEqual(record['returncode'],0)
        self.assertFalse(record['watchdog_killed'])
        self.assertTrue(record['cleanup_sigkill_sent'])
        self.assertEqual(len(record['adopted_descendants']),2)

    def test_exception_leader_cannot_leave_descendants(self):
        record,_=self.run_mode('error_tree')
        self.assertEqual(record['returncode'],1)
        self.assertEqual(len(record['adopted_descendants']),2)

    def test_supervisor_exception_cleans_then_propagates(self):
        req=self.request('timeout_tree');proc=self.spawn(req);start=time.monotonic()
        def failure():
            if Path(req['info']).exists():raise ValueError('synthetic supervisor error')
            if time.monotonic()-start>2:return 'fixture_startup_timeout'
        with self.assertRaisesRegex(ValueError,'synthetic supervisor error'):
            supervise.wait_for_worker(proc,failure)
        record=proc.supervisor_exit_record
        self.observe(proc,req,record)
        self.assertEqual(record['supervisor_error']['type'],'ValueError')

    def test_global_limit_reason_is_preserved(self):
        record,_=self.run_mode('timeout',reason='global_resource_limit')
        self.assertEqual(record['kill_reason'],'global_resource_limit')

    def test_repeated_runs_leave_no_processes(self):
        all_pids=[]
        for index,mode in enumerate(['normal','timeout_tree','exception','success_tree']*2):
            _,info=self.run_mode(mode,index)
            all_pids.extend(info['pids'])
        self.assert_gone(all_pids)

    def test_cleanup_does_not_reap_unrelated_child(self):
        other=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(.05);raise SystemExit(23)'])
        try:
            self.run_mode('timeout_tree')
            self.assertEqual(other.wait(timeout=2),23)
        finally:
            if other.returncode is None:other.kill();other.wait(timeout=2)

    @unittest.skipUnless((ORIGINAL_SUPERVISOR).is_file(),'original supervisor required for comparison')
    def test_original_supervisor_reaps_leader_but_leaves_descendants(self):
        requests=self.prepare_batch(['success_tree'])
        script=self.root/'baseline_supervise.py'
        script.write_bytes((ORIGINAL_SUPERVISOR).read_bytes())
        proc=subprocess.Popen([sys.executable,'-B',str(script)],cwd=self.root,start_new_session=True,
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.processes.append(proc)
        info=None
        try:
            self.assertEqual(proc.wait(timeout=3),0)
            info=json.loads(Path(requests[0]['info']).read_text())
            record=json.loads((self.root/'raw/synthetic_0.resource.json').read_text())
            self.assertTrue(record['reaped'])
            self.assertEqual(record['returncode'],0)
            alive=[]
            for pid in info['pids'][1:]:
                try:os.kill(pid,0);alive.append(pid)
                except ProcessLookupError:pass
            self.assertEqual(set(alive),set(info['pids'][1:]))
            EVIDENCE.append({'test':self.id(),'baseline_leader_reaped':True,
                             'baseline_descendants_still_present':alive,
                             'scope':'synthetic worker only, cleaned by the test harness'})
        finally:
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            deadline=time.monotonic()+2
            while time.monotonic()<deadline:
                try:pid,status,_=os.wait4(-proc.pid,os.WNOHANG)
                except ChildProcessError:break
                if pid==proc.pid:proc.returncode=os.waitstatus_to_exitcode(status)
                if not pid:time.sleep(.01)
            if info:self.assert_gone(info['pids'])

    def prepare_batch(self,modes):
        (self.root/'raw').mkdir()
        requests=[self.request(mode,index) for index,mode in enumerate(modes)]
        (self.root/'requests.json').write_text(json.dumps(requests),encoding='utf-8')
        freeze={'sha256':{'worker.py':hashlib.sha256(self.worker.read_bytes()).hexdigest()}}
        (self.root/'freeze.json').write_text(json.dumps(freeze),encoding='utf-8')
        return requests

    def invoke_batch(self):
        previous=supervise.P
        try:
            supervise.P=self.root
            supervise.main()
        finally:supervise.P=previous

    def test_real_main_preserves_exit_records_and_refuses_rerun(self):
        requests=self.prepare_batch(['normal','exception','success_tree'])
        self.invoke_batch()
        records=json.loads((self.root/'process_resources.json').read_text())
        self.assertEqual([rec['returncode'] for rec in records],[0,1,0])
        for req,record in zip(requests,records):
            self.assertTrue(record['reaped'] and record['process_group_reaped'])
            self.assertFalse(record['result_exists'])
            self.assertFalse((self.root/'raw'/f"{req['run_id']}.result.json").exists())
            self.assert_gone(json.loads(Path(req['info']).read_text())['pids'])
            persisted=json.loads((self.root/'raw'/f"{req['run_id']}.resource.json").read_text())
            self.assertEqual(record,persisted)
        before={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        with self.assertRaisesRegex(AssertionError,'Refuse second benchmark run'):self.invoke_batch()
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()})
        self.assertTrue((self.root/'output_seal.json').is_file())
        EVIDENCE.append({'test':self.id(),'synthetic_batch_requests':3,'exit_codes':[0,1,0],
                         'resource_records_persisted':True,'rerun_refused_without_mutation':True})

    def test_bad_result_keeps_exit_record_before_failing(self):
        self.prepare_batch(['bad_result'])
        with self.assertRaisesRegex(RuntimeError,'exit record preserved'):self.invoke_batch()
        record=json.loads((self.root/'raw/synthetic_0.resource.json').read_text())
        self.assertEqual(record['returncode'],0)
        self.assertEqual(record['result_read_error']['type'],'JSONDecodeError')
        self.assertTrue(record['reaped'] and record['process_group_reaped'])
        self.assert_gone(json.loads((self.root/'pids_0.json').read_text())['pids'])
        self.assertFalse((self.root/'output_seal.json').exists())

    def test_real_main_supervisor_failure_keeps_exit_record(self):
        requests=self.prepare_batch(['timeout_tree'])
        original=supervise.wait_for_worker
        def failing_wait(proc,unused_reason):
            began=time.monotonic()
            def reason():
                if Path(requests[0]['info']).exists():raise ValueError('synthetic main supervisor error')
                if time.monotonic()-began>2:return 'fixture_startup_timeout'
            return original(proc,reason)
        try:
            supervise.wait_for_worker=failing_wait
            with self.assertRaisesRegex(ValueError,'synthetic main supervisor error'):self.invoke_batch()
        finally:supervise.wait_for_worker=original
        record=json.loads((self.root/'raw/synthetic_0.resource.json').read_text())
        self.assertTrue(record['reaped'] and record['process_group_reaped'])
        self.assertEqual(record['supervisor_error']['type'],'ValueError')
        self.assert_gone(json.loads((self.root/'pids_0.json').read_text())['pids'])

class ControlledClock:
    def __init__(self,step=.01):self.value=0.;self.step=step
    def __call__(self):
        self.value+=self.step
        return self.value


class SupervisorV2BranchTests(SupervisorLifecycleTests):
    # Do not inherit and rerun the original methods: the suite loads the
    # original class once and only this class's own branch methods below.
    def fake_usage(self):
        return SimpleNamespace(ru_utime=.01,ru_stime=.02,ru_maxrss=10,
            ru_minflt=0,ru_majflt=0,ru_nvcsw=0,ru_nivcsw=0)

    def test_v2_continuously_ready_wait4_cannot_defer_deadline(self):
        proc=SimpleNamespace(pid=900001,returncode=None)
        clock=ControlledClock();waits=[];signals=[]
        def ready_wait4(pid,flags):
            child=proc.pid if not waits else proc.pid+len(waits)
            waits.append(child)
            return child,0,self.fake_usage()
        def send(pid,sig):signals.append((sig,len(waits)))
        with mock.patch.object(supervise.os,'getpgid',return_value=proc.pid), \
             mock.patch.object(supervise.os,'getsid',return_value=proc.pid), \
             mock.patch.object(supervise.os,'waitid',return_value=SimpleNamespace(si_pid=proc.pid)), \
             mock.patch.object(supervise.os,'wait4',side_effect=ready_wait4), \
             mock.patch.object(supervise.os,'killpg',side_effect=send), \
             mock.patch.object(supervise.time,'monotonic',side_effect=clock), \
             mock.patch.object(supervise.time,'sleep'):
            with self.assertRaises(TimeoutError):
                supervise.wait_for_worker(proc,lambda:None,termination_grace_s=.05,cleanup_timeout_s=.05)
        self.assertEqual([s for s,n in signals],[signal.SIGTERM,signal.SIGKILL])
        self.assertLessEqual(signals[1][1],6)
        self.assertLessEqual(len(waits),12)
        self.assertTrue(proc.supervisor_exit_record['reaped'])
        self.assertFalse(proc.supervisor_exit_record['process_group_reaped'])
        EVIDENCE.append({'test':self.id(),'simulated':True,'wait4_success_count':len(waits),
                         'signals_at_wait_counts':signals,'exit_record':proc.supervisor_exit_record})

    def test_v2_no_sigkill_after_owned_group_children_disappear(self):
        proc=SimpleNamespace(pid=900002,returncode=None)
        clock=ControlledClock();collected=False;signals=[]
        def waitid(kind,pid,flags):
            if kind==os.P_PGID and collected:raise ChildProcessError()
            return SimpleNamespace(si_pid=proc.pid)
        def wait4(pid,flags):
            nonlocal collected
            if collected:raise ChildProcessError()
            collected=True
            return proc.pid,0,self.fake_usage()
        with mock.patch.object(supervise.os,'getpgid',return_value=proc.pid), \
             mock.patch.object(supervise.os,'getsid',return_value=proc.pid), \
             mock.patch.object(supervise.os,'waitid',side_effect=waitid), \
             mock.patch.object(supervise.os,'wait4',side_effect=wait4), \
             mock.patch.object(supervise.os,'killpg',side_effect=lambda pid,sig:signals.append(sig)), \
             mock.patch.object(supervise.time,'monotonic',side_effect=clock), \
             mock.patch.object(supervise.time,'sleep'):
            record=supervise.wait_for_worker(proc,lambda:None,termination_grace_s=.015,cleanup_timeout_s=.1)
        self.assertEqual(signals,[signal.SIGTERM])
        self.assertTrue(record['reaped'] and record['process_group_reaped'])
        EVIDENCE.append({'test':self.id(),'simulated':True,'signals':signals,'exit_record':record})

    def test_v2_record_update_interrupt_preserves_primary_chain(self):
        proc=SimpleNamespace(pid=900003,returncode=None)
        collected=False
        def waitid(kind,pid,flags):return None
        def wait4(pid,flags):
            nonlocal collected
            if collected:raise ChildProcessError()
            collected=True
            return proc.pid,0,self.fake_usage()
        def clock():
            if collected:raise KeyboardInterrupt('record publication interrupt')
            return 0.
        def primary():raise ValueError('primary before record update')
        with mock.patch.object(supervise.os,'getpgid',return_value=proc.pid), \
             mock.patch.object(supervise.os,'getsid',return_value=proc.pid), \
             mock.patch.object(supervise.os,'waitid',side_effect=waitid), \
             mock.patch.object(supervise.os,'wait4',side_effect=wait4), \
             mock.patch.object(supervise.os,'killpg'), \
             mock.patch.object(supervise.time,'perf_counter',side_effect=clock):
            with self.assertRaisesRegex(ValueError,'primary before record update') as caught:
                supervise.wait_for_worker(proc,primary)
        self.assertIsInstance(caught.exception.__cause__,KeyboardInterrupt)
        record=proc.supervisor_exit_record
        self.assertTrue(record['reaped'])
        self.assertFalse(record['process_group_reaped'] or record['usage_complete'])
        self.assertEqual(record['cleanup_error']['phase'],'record_update')
        EVIDENCE.append({'test':self.id(),'simulated':True,'injected':'record update interrupt',
                         'exception_type':'ValueError','cause_type':'KeyboardInterrupt','exit_record':record})

    def tracked_main(self):
        real_popen=subprocess.Popen
        def track(*args,**kwargs):
            proc=real_popen(*args,**kwargs);self.processes.append(proc)
            return proc
        return mock.patch.object(supervise.subprocess,'Popen',side_effect=track)

    def fault_record(self):
        return json.loads((self.root/'raw/synthetic_0.resource.json').read_text())

    def test_v2_validation_oserror_is_recorded_before_cleanup(self):
        self.prepare_batch(['timeout'])
        with self.tracked_main(),mock.patch.object(supervise.os,'getpgid',side_effect=OSError('validation fault')):
            with self.assertRaisesRegex(OSError,'validation fault'):self.invoke_batch()
        record=self.fault_record()
        self.assertFalse(record['reaped'] or record['process_group_reaped'])
        self.assertEqual(record['supervisor_error']['type'],'OSError')
        self.assertEqual(record['cleanup_error']['type'],'OwnershipNotVerified')
        EVIDENCE.append({'test':self.id(),'injected':'ownership validation OSError','exit_record':record})

    def test_v2_cleanup_send_oserror_is_recorded(self):
        self.prepare_batch(['normal'])
        with self.tracked_main(),mock.patch.object(supervise.os,'killpg',side_effect=PermissionError('send denied')):
            with self.assertRaisesRegex(PermissionError,'send denied'):self.invoke_batch()
        record=self.fault_record()
        self.assertFalse(record['reaped'] or record['process_group_reaped'])
        self.assertEqual(record['cleanup_error']['type'],'PermissionError')
        self.assertEqual(record['cleanup_error']['phase'],'SIGTERM')
        EVIDENCE.append({'test':self.id(),'injected':'cleanup send PermissionError','exit_record':record})

    def test_v2_cleanup_keyboardinterrupt_is_recorded(self):
        self.prepare_batch(['normal'])
        with self.tracked_main(),mock.patch.object(supervise.os,'killpg',side_effect=KeyboardInterrupt('cleanup interrupt')):
            with self.assertRaisesRegex(KeyboardInterrupt,'cleanup interrupt'):self.invoke_batch()
        record=self.fault_record()
        self.assertFalse(record['reaped'] or record['process_group_reaped'])
        self.assertEqual(record['cleanup_error']['type'],'KeyboardInterrupt')
        EVIDENCE.append({'test':self.id(),'injected':'cleanup KeyboardInterrupt','exit_record':record})

    def test_v2_partial_drain_failure_retains_collected_leader(self):
        self.prepare_batch(['success_tree'])
        real_wait4=os.wait4;collected=[]
        def partial(pid,flags):
            if collected:raise OSError('drain failed after collection')
            item=real_wait4(pid,flags)
            if item[0]:collected.append(item[0])
            return item
        with self.tracked_main(),mock.patch.object(supervise.os,'wait4',side_effect=partial):
            with self.assertRaisesRegex(OSError,'after collection'):self.invoke_batch()
        record=self.fault_record()
        self.assertTrue(record['reaped'])
        self.assertEqual(record['returncode'],0)
        self.assertFalse(record['process_group_reaped'] or record['usage_complete'])
        self.assertEqual(record['cleanup_error']['phase'],'TERM_drain')
        EVIDENCE.append({'test':self.id(),'injected':'partial drain OSError','exit_record':record})

    def test_v2_original_error_chain_survives_cleanup_and_bad_json(self):
        self.prepare_batch(['timeout'])
        (self.root/'raw/synthetic_0.result.json').write_text('{bad json')
        original=supervise.wait_for_worker
        def failing(proc,reason):
            def primary():raise ValueError('primary supervision fault')
            return original(proc,primary)
        with self.tracked_main(),mock.patch.object(supervise,'wait_for_worker',side_effect=failing), \
             mock.patch.object(supervise.os,'killpg',side_effect=OSError('cleanup fault')):
            with self.assertRaisesRegex(ValueError,'primary supervision fault') as caught:self.invoke_batch()
        self.assertIsInstance(caught.exception.__cause__,OSError)
        self.assertIn('cleanup fault',str(caught.exception.__cause__))
        record=self.fault_record()
        self.assertFalse(record['reaped'] or record['process_group_reaped'])
        self.assertEqual(record['supervisor_error']['type'],'ValueError')
        self.assertEqual(record['cleanup_error']['type'],'OSError')
        self.assertEqual(record['result_read_error']['type'],'JSONDecodeError')
        EVIDENCE.append({'test':self.id(),'injected':'primary + cleanup + malformed JSON',
                         'exception_type':'ValueError','cause_type':'OSError','exit_record':record})

    def test_v2_main_missing_attribute_falls_back_to_conservative_record(self):
        self.prepare_batch(['timeout'])
        def failure(proc,reason):
            del proc.supervisor_exit_record
            raise OSError('failure before lifecycle publication')
        with self.tracked_main(),mock.patch.object(supervise,'wait_for_worker',side_effect=failure):
            with self.assertRaisesRegex(OSError,'before lifecycle publication'):self.invoke_batch()
        record=self.fault_record()
        self.assertFalse(record['reaped'] or record['process_group_reaped'])
        self.assertEqual(record['supervisor_error']['type'],'OSError')
        EVIDENCE.append({'test':self.id(),'injected':'missing exit attribute','exit_record':record})

    def test_v2_term_normally_exits_without_sigkill(self):
        record,info=self.run_mode('term')
        self.assertEqual(record['returncode'],-signal.SIGTERM)
        self.assertFalse(record['cleanup_sigkill_sent'])
        self.assertEqual(len(info['pids']),1)

    def test_v2_valid_result_json_is_processed_and_sealed(self):
        self.prepare_batch(['valid_result'])
        self.invoke_batch()
        record=self.fault_record()
        path=self.root/'raw/synthetic_0.result.json'
        self.assertTrue(record['result_exists'])
        self.assertEqual(record['result_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertGreaterEqual(record['startup_serialization_exit_and_unattributed_cpu_s'],0)
        self.assertGreaterEqual(record['startup_serialization_exit_and_reap_wall_s'],0)
        seal=json.loads((self.root/'output_seal.json').read_text())
        self.assertEqual(seal['sha256']['raw/synthetic_0.result.json'],record['result_sha256'])
        self.assert_gone(json.loads((self.root/'pids_0.json').read_text())['pids'])
        EVIDENCE.append({'test':self.id(),'valid_json_processed':True,'exit_record':record})


def load_tests(loader,tests,pattern):
    suite=loader.loadTestsFromTestCase(SupervisorLifecycleTests)
    for name in sorted(SupervisorV2BranchTests.__dict__):
        if name.startswith('test_'):suite.addTest(SupervisorV2BranchTests(name))
    return suite


class PerCaseResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.case_results=[]
    def startTest(self,test):
        super().startTest(test)
        self.case_start=time.perf_counter()
    def save_case(self,test,status,detail=None):
        item={'test_id':test.id(),'status':status,
              'duration_s':time.perf_counter()-self.case_start,
              'original_v1_case':not test._testMethodName.startswith('test_v2_'),
              'evidence':[entry for entry in EVIDENCE if entry['test']==test.id()]}
        if detail is not None:item['detail']=detail
        self.case_results.append(item)
    def addSuccess(self,test):
        super().addSuccess(test);self.save_case(test,'passed')
    def addFailure(self,test,err):
        super().addFailure(test,err);self.save_case(test,'failed',self._exc_info_to_string(err,test))
    def addError(self,test,err):
        super().addError(test,err);self.save_case(test,'error',self._exc_info_to_string(err,test))
    def addSkip(self,test,reason):
        super().addSkip(test,reason);self.save_case(test,'skipped',reason)


def run_and_record():
    stream=io.StringIO()
    suite=load_tests(unittest.defaultTestLoader,None,None)
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=PerCaseResult).run(suite)
    report={'version':'v2','tests_run':result.testsRun,'failures':len(result.failures),
            'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful(),
            'original_v1_cases':sum(row['original_v1_case'] for row in result.case_results),
            'new_v2_cases':sum(not row['original_v1_case'] for row in result.case_results),
            'cases':result.case_results,'log':stream.getvalue(),
            'candidate_sha256':hashlib.sha256(SUPERVISOR.read_bytes()).hexdigest(),
            'test_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'safety_bounds':{'independent_test_wall_limit_s':4,'test_cleanup_wall_limit_s':2,
                             'fixed_max_processes_per_worker':3,'fixed_max_concurrent_fixture_processes':4,
                             'finite_max_worker_launches_per_test':8,'infinite_fork_tests':False},
            'scope':'Linux one-shot CLI, same-group non-escaping fixtures; standard library only'}
    (BASE/'test-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (BASE/'test-results.txt').write_text(stream.getvalue(),encoding='utf-8')
    print(stream.getvalue())
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__=='__main__':
    if sys.argv[1:]==['--record']:run_and_record()
    else:unittest.main()
