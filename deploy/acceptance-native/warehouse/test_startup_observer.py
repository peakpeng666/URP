"""Pure fixtures and owned local Python children only, never ROS or Ignition."""
import copy
import ast
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

from startup_observer import Observer, ENABLE, HARD_WALL_S
from startup_observer_child import Measurements, ECHO, INFO, MAX_BYTES, main as child_main
from startup_observation_schema import sanitize


class Clock:
    value = 100.0
    def __call__(self):return self.value


def row(phase='starting', sid='sim_fixture', count=26):
    return {'phase': phase, 'session_id': sid, 'world': 'warehouse', 'errors': [],
            'telemetry': {'counts': {'clock': count, 'cmd_vel': 0}, 'age_s': {'clock': 4.0}}}


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.temp = tempfile.TemporaryDirectory()
        self.obs = Observer({ENABLE: '1', 'URP_ACCEPTANCE_OWNER': 'PRIVATE'}, self.temp.name,
                            '/known/source', clock=self.clock)
        self.obs.bind('sim_fixture')

    def tearDown(self):
        self.obs.safe('close')
        self.temp.cleanup()

    def test_disabled_has_no_mutation_or_side_effect(self):
        self.obs = Observer({}, self.temp.name, '/known/source', popen=lambda *a, **k:self.fail())
        value = row()
        seen = []
        api = self.obs.wrap(lambda *args:seen.append(args) or value)
        self.obs.bind('sim_fixture')
        self.assertIs(api('GET', '/sim/state', timeout=3), value)
        self.assertEqual(seen, [('GET', '/sim/state', None, 3)])
        self.assertEqual(self.obs.close()['status'], 'disabled')

    def test_wrapper_preserves_response_identity_content_and_call_count(self):
        value = row(); original = copy.deepcopy(value); calls = []
        api = self.obs.wrap(lambda *args:calls.append(args) or value)
        self.assertIs(api('GET', '/sim/state', timeout=2), value)
        self.assertEqual(value, original)
        self.assertEqual(calls, [('GET', '/sim/state', None, 2)])

    def test_original_exception_is_unchanged_no_retry(self):
        for exc in (TimeoutError('PRIVATE'), KeyboardInterrupt('PRIVATE')):
            calls = []
            def api(*args):calls.append(args);raise exc
            wrapped = self.obs.wrap(api)
            try:wrapped('POST', '/sim/session', {}, timeout=60)
            except BaseException as caught:self.assertIs(caught, exc)
            else:self.fail('exception swallowed')
            self.assertEqual(len(calls), 1)

    def test_observer_error_never_changes_original_result(self):
        value = row()
        with patch.object(self.obs, 'observe', side_effect=OSError()):
            self.assertIs(self.obs.wrap(lambda *args:value)('GET', '/sim/state'), value)
        self.assertEqual(self.obs.raw['status'], 'unavailable')

    def test_safe_preserves_real_cancellation_kinds(self):
        for exc in (KeyboardInterrupt(),SystemExit(2),RuntimeError('interrupted')):
            with patch.object(self.obs,'observe',side_effect=exc):
                with self.assertRaises(type(exc)) as caught:self.obs.safe('observe',row())
                self.assertIs(caught.exception,exc)

    def test_original_api_exception_wins_over_cutoff_cancellation(self):
        original=TimeoutError('original')
        def api(*args):raise original
        with patch.object(self.obs,'cutoff',side_effect=KeyboardInterrupt()):
            with self.assertRaises(TimeoutError) as caught:self.obs.wrap(api)('GET','/sim/state')
        self.assertIs(caught.exception,original)

    def test_delete_attempted_once_despite_observer_cancellation(self):
        calls=[];exc=RuntimeError('interrupted')
        with patch.object(self.obs,'before_cleanup',side_effect=exc):
            with self.assertRaises(RuntimeError) as caught:
                self.obs.wrap(lambda *args:calls.append(args) or row('stopped'))('DELETE','/sim/session',None,17)
        self.assertIs(caught.exception,exc)
        self.assertEqual(calls,[('DELETE','/sim/session',None,17)])

    def test_delete_api_error_primary_over_observer_cancellation(self):
        original=TimeoutError();calls=[]
        def api(*args):calls.append(args);raise original
        with patch.object(self.obs,'before_cleanup',side_effect=KeyboardInterrupt()):
            with self.assertRaises(TimeoutError) as caught:self.obs.wrap(api)('DELETE','/sim/session')
        self.assertIs(caught.exception,original);self.assertEqual(len(calls),1)

    def test_constructor_wrapper_preserves_control_cancellation(self):
        tree=ast.parse(Path(__file__).with_name('warehouse_acceptance.py').read_text())
        block=next(n for n in ast.walk(tree) if isinstance(n,ast.Try) and isinstance(n.body[0],ast.Assign)
                   and isinstance(n.body[0].value,ast.Call) and isinstance(n.body[0].value.func,ast.Name)
                   and n.body[0].value.func.id=='Observer')
        module=ast.Module(body=[block],type_ignores=[])
        from startup_observer import is_cancellation
        for exc in (KeyboardInterrupt(),SystemExit(2),RuntimeError('interrupted')):
            def constructor(*args):raise exc
            with self.assertRaises(type(exc)) as caught:
                exec(compile(module,'production-constructor-guard','exec'),{'Observer':constructor,'is_cancellation':is_cancellation,
                     'env':{},'private':self.temp.name,'source':'/fixture','raw':{}})
            self.assertIs(caught.exception,exc)

    def test_sigterm_during_observation_is_not_swallowed(self):
        previous=signal.getsignal(signal.SIGTERM)
        def stop(signum,frame):raise RuntimeError('interrupted')
        signal.signal(signal.SIGTERM,stop)
        try:
            self.obs.clock=lambda:os.kill(os.getpid(),signal.SIGTERM)
            with self.assertRaisesRegex(RuntimeError,'interrupted'):
                self.obs.wrap(lambda *args:row())('GET','/sim/state')
        finally:
            self.obs.clock=self.clock
            signal.signal(signal.SIGTERM,previous)

    def test_no_probe_before_validated_binding(self):
        self.obs.sid = None
        with patch.object(self.obs, 'start') as start:
            self.clock.value += 10
            self.obs.observe(row())
            start.assert_not_called()

    def test_invalid_or_changed_id_permanently_disables(self):
        for value in ('../sim_bad', 'sim_x/../../bad', 'sim_other', 'sim_'+'a'*125, None):
            obs = Observer({ENABLE:'1'}, self.temp.name, '/known/source', clock=self.clock)
            obs.bind('sim_fixture');obs.bind(value)
            self.assertTrue(obs.closed)
            obs.bind('sim_fixture')
            self.assertTrue(obs.closed)

    def test_foreign_response_never_captured_or_rebound(self):
        self.obs.observe(row(sid='sim_foreign'))
        self.assertEqual(self.obs.sid, 'sim_fixture')
        self.assertEqual(self.obs.raw['ros_api']['samples'], 0)
        self.assertEqual(self.obs.raw['ros_api']['availability'], 'identity_mismatch')

    def test_foreign_world_never_captured(self):
        value=row();value['world']='maze';self.obs.observe(value)
        self.assertTrue(self.obs.closed)
        self.assertEqual(self.obs.raw['ros_api']['samples'],0)

    def test_cleanup_response_and_settle_counts_excluded(self):
        self.obs.observe(row())
        before = copy.deepcopy(self.obs.raw['ros_api'])
        calls = []
        def api(*args):
            self.assertTrue(self.obs.closed)
            calls.append(args)
            return row('stopping', count=900)
        wrapped = self.obs.wrap(api)
        wrapped('DELETE', '/sim/session', timeout=180)
        wrapped('GET', '/sim/state')
        self.assertEqual(self.obs.raw['ros_api'], before)
        self.assertEqual(len(calls), 2)

    def test_leave_startup_before_delete_cuts_off(self):
        for phase in ('stopping','failed','stopped','ready','undocking','localizing'):
            obs = Observer({ENABLE:'1'}, self.temp.name, '/known/source', clock=self.clock)
            obs.bind('sim_fixture');obs.observe(row());obs.observe(row(phase,count=876));obs.observe(row(count=999))
            self.assertEqual(obs.raw['ros_api']['last']['counts']['clock'],26)
            self.assertTrue(obs.closed)

    def test_errors_in_cached_startup_cut_off(self):
        value=row();value['errors']=['PRIVATE'];self.obs.observe(value)
        self.assertTrue(self.obs.closed)
        self.assertNotIn('PRIVATE',json.dumps(sanitize(self.obs.raw)))

    def test_api_sample_count_and_fields_bounded(self):
        for i in range(1000):self.obs.observe(row(count=i))
        self.assertEqual(self.obs.raw['ros_api']['samples'],128)
        self.assertEqual(self.obs.raw['ros_api']['last']['counts']['clock'],999)

    def start_fake(self, code):
        calls=[]
        def spawn(command, **kwargs):
            calls.append((command,kwargs))
            return subprocess.Popen([sys.executable,'-c',code], **kwargs)
        self.obs.popen=spawn
        self.clock.value=105
        self.obs.observe(row())
        return calls

    def await_exit(self):
        end=time.monotonic()+3
        while not self.obs.exited() and time.monotonic()<end:time.sleep(.005)
        self.assertTrue(self.obs.exited())

    def test_owned_group_exact_partition_and_profile(self):
        calls=self.start_fake('import time;time.sleep(30)')
        command,kw=calls[0]
        self.assertEqual(kw['env']['IGN_PARTITION'],'urp_sim_fixture')
        self.assertNotIn('URP_ACCEPTANCE_OWNER',kw['env'])
        self.assertTrue(kw['start_new_session'])
        self.assertIn('/known/source/setup/profile.sh',command)
        self.assertNotIn('sim_fixture',str(command))
        self.assertEqual(os.getpgid(self.obs.proc.pid),self.obs.proc.pid)
        self.obs.close()
        self.assertIn(self.obs.proc.returncode,(-signal.SIGTERM,-signal.SIGKILL))
        self.assertTrue(self.obs.raw['observer_leader_reaped']);self.assertIsNone(self.obs.raw['observer_cleanup_complete'])

    def test_unreaped_leader_is_kept_until_group_cleanup(self):
        self.start_fake('pass');self.await_exit()
        self.assertIsNone(self.obs.proc.returncode)
        self.obs.close()
        self.assertEqual(self.obs.proc.returncode,0)

    def test_expiry_kills_owned_group(self):
        self.start_fake('import time;time.sleep(30)')
        self.obs.expire();self.await_exit();self.obs.close()
        self.assertTrue(self.obs.raw['observer_watchdog_expired'])
        self.assertEqual(self.obs.raw['status'],'bounded_stop')

    def test_valid_finished_window_requires_starting_confirmation(self):
        payload=sanitize({'status':'complete','native_stats':{'availability':'no_messages'},'ros_clock':{'availability':'no_messages'}})
        self.start_fake('print('+repr(json.dumps(payload))+')');self.await_exit()
        self.obs.observe(row(count=100))
        self.assertTrue(self.obs.confirmed)
        self.assertEqual(self.obs.raw['status'],'complete')
        self.obs.observe(row(count=200));self.obs.observe(row('failed'))
        self.assertEqual(self.obs.raw['status'],'complete')
        self.assertEqual(self.obs.raw['ros_api']['observer_window_first']['counts']['clock'],26)
        self.assertEqual(self.obs.raw['ros_api']['observer_window_last']['counts']['clock'],100)
        self.assertEqual(self.obs.raw['ros_api']['last']['counts']['clock'],200)

    def test_unconfirmed_window_discarded_on_failed_response(self):
        self.start_fake('print("{}")');self.await_exit()
        self.obs.observe(row('failed'))
        self.assertFalse(self.obs.confirmed)
        self.assertEqual(sanitize(self.obs.raw)['native_stats']['availability'],'unavailable')

    def test_bad_child_output_is_unavailable_and_cleaned(self):
        self.start_fake('print("PRIVATE RAW PATH")');self.await_exit()
        self.obs.safe('observe',row())
        self.assertEqual(self.obs.raw['status'],'unavailable')
        self.assertTrue(self.obs.raw['observer_leader_reaped']);self.assertIsNone(self.obs.raw['observer_cleanup_complete'])
        self.assertNotIn('PRIVATE',json.dumps(sanitize(self.obs.raw)))

    def test_probe_spawn_failure_no_retry(self):
        self.clock.value=105
        with patch.object(self.obs,'popen',side_effect=OSError()) as spawn:
            self.obs.safe('observe',row());self.obs.safe('observe',row())
            self.assertEqual(spawn.call_count,1)

    def test_owned_group_descendant_killed_after_leader_exits(self):
        code='import subprocess,sys,os; p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"]);print(p.pid,flush=True);os._exit(0)'
        self.start_fake(code);self.await_exit()
        self.obs.drain();pid=int(self.obs.buffer)
        self.obs.close()
        end=time.monotonic()+1
        while time.monotonic()<end:
            try:state=Path('/proc/'+str(pid)+'/stat').read_text().split(') ',1)[1].split()[0]
            except (FileNotFoundError,ProcessLookupError):break
            if state=='Z':break
            time.sleep(.005)
        else:self.fail('owned descendant still running')

    def test_timer_failure_still_kills_started_child(self):
        with patch('startup_observer.threading.Timer.start',side_effect=RuntimeError()):
            self.obs.popen=lambda cmd,**kw:subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],**kw)
            self.clock.value=105;self.obs.safe('observe',row())
        self.await_exit();self.obs.close()
        self.assertTrue(self.obs.raw['observer_leader_reaped']);self.assertIsNone(self.obs.raw['observer_cleanup_complete'])

    def test_actual_finalizer_keeps_application_cleanup_after_observer_cancel(self):
        # Compile the production finalizer AST unchanged into a mock-only test
        # function. This executes no application/ROS setup or native commands.
        tree=ast.parse(Path(__file__).with_name('warehouse_acceptance.py').read_text())
        execute=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='execute')
        body=[ast.Global(names=['forced','diagnostic'])]+next(n for n in execute.body if isinstance(n,ast.Try)).finalbody
        module=ast.Module(body=[ast.FunctionDef(name='finalize',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=body,decorator_list=[])],type_ignores=[])
        ast.fix_missing_locations(module)
        for initial in ('PASS','FAIL'):
            calls=[];exc=RuntimeError('interrupted')
            def cancel(*args):raise exc
            class Gateway:
                returncode=None
                def poll(self):return None
                def wait(self,timeout):calls.append(('wait',timeout));self.returncode=0
            raw={'state':initial,'cleanup_pass':True};diagnostic={'harness':{},'lifecycle':{'failure_code':'api_timeout'}}
            namespace={'observer':types.SimpleNamespace(safe=cancel,raw={}), 'raw':raw,'base':'http://127.0.0.1:1',
                       'gateway':Gateway(),'api':lambda *args,**kw:calls.append(('api',args)),
                       'diagnostic':diagnostic,'describe_failure':lambda exc:{'exception_kind':'interrupted'},
                       'owned':lambda token:[], 'token':'fixture','forced':False,'subprocess':subprocess,
                       'signal':signal,'time':time,'collect':lambda *args:calls.append(('collect',)) or {},
                       'runtime':Path(self.temp.name),'sid':'sim_fixture','project':lambda raw,**kw:dict(raw),
                       'a':types.SimpleNamespace(summary=Path(self.temp.name)/'summary.json'),'json':json}
            exec(compile(module,'production-finalizer','exec'),namespace)
            with self.assertRaises(RuntimeError) as caught:namespace['finalize']()
            self.assertIs(caught.exception,exc)
            self.assertTrue(any(c[0]=='api' and c[1][1:] == ('POST','/shutdown',{}) for c in calls))
            self.assertIn(('wait',240),calls);self.assertIn(('wait',5),calls);self.assertIn(('collect',),calls)
            self.assertEqual(raw['state'],'ERROR' if initial=='PASS' else 'FAIL')
            self.assertEqual(diagnostic['lifecycle']['failure_code'],'api_timeout')


class MeasurementTests(unittest.TestCase):
    def setUp(self):self.clock=Clock();self.m=Measurements(95,self.clock)

    def stat(self, iterations=24, stamp=72000000):
        return json.dumps({'simTime':{'nsec':stamp},'realTime':{'sec':'1'},'iterations':str(iterations)}).encode()+b'\n'

    def info(self):self.m.feed('info',b'Publishers [Address, Message Type]:\n  tcp://PRIVATE:123, ignition.msgs.WorldStatistics\n')

    def test_valid_bytes_incremental_and_defaults(self):
        value=self.stat()
        for chunk in (value[:7],value[7:]):self.assertTrue(self.m.feed('echo',chunk))
        self.info();self.clock.value+=1;out=self.m.finish(0,0)
        self.assertEqual(out['native_stats']['samples'],1)
        self.assertEqual(out['native_stats']['first']['sim_time_s'],.072)
        self.assertFalse(out['native_stats']['first']['paused'])
        self.assertIsNone(out['native_stats']['sim_time_advanced'])
        self.assertEqual(out['native_stats']['last_receipt_age_at_window_end_s'],1)
        self.assertNotIn('PRIVATE',json.dumps(out))

    def test_missing_messages_not_fabricated_stall(self):
        self.info();out=self.m.finish(0,0)
        self.assertEqual(out['native_stats']['availability'],'no_messages')
        self.assertEqual(out['native_stats']['samples'],0)
        self.assertIsNone(out['native_stats']['sim_time_advanced'])
        self.assertIsNone(out['ros_clock']['first'])

    def test_wrong_type_disables_native_values(self):
        self.m.feed('echo',self.stat());self.m.feed('info',b'Publishers [Address, Message Type]:\n  x, arbitrary.Type\n')
        out=self.m.finish(0,0)
        self.assertEqual(out['native_stats']['availability'],'type_mismatch')
        self.assertIsNone(out['native_stats']['first'])

    def test_ros_clock_is_direct_and_receipt_timing_separate(self):
        self.m.ros(0,72000000);self.clock.value+=1;self.m.ros(0,75000000)
        out=self.m.finish(1,1)['ros_clock']
        self.assertEqual(out['messages'],2)
        self.assertTrue(out['sim_time_advanced'])
        self.assertEqual(out['last']['receipt_wall_s'],6)
        self.assertEqual(out['last']['sim_time_s'],.075)

    def test_sampling_end_age_excludes_later_cleanup(self):
        self.m.ros(0,72000000);self.clock.value=120
        out=self.m.finish(1,1,sampling_ended=101)
        self.assertEqual(out['ros_clock']['last_receipt_age_at_window_end_s'],1)

    def test_native_samples_bound(self):
        for _ in range(128):self.assertTrue(self.m.feed('echo',self.stat()))
        self.assertFalse(self.m.feed('echo',self.stat()))
        self.assertEqual(self.m.raw['native_stats']['samples'],128)

    def test_byte_and_line_bounds(self):
        self.assertFalse(self.m.feed('echo',b'x'*(MAX_BYTES+1)))
        self.assertLessEqual(self.m.raw['output_bytes'],MAX_BYTES)
        self.assertFalse(Measurements(95,self.clock).feed('echo',b'x'*16385))

    def test_invalid_ros_and_json_not_measurements(self):
        for pair in ((True,0),(0,1000000000),(-1,0),(86400,1)):
            self.m.ros(*pair)
        self.m.feed('echo',b'\xff\n{"simTime": NaN}\n')
        self.assertEqual(self.m.raw['ros_clock']['messages'],0)
        self.assertEqual(self.m.raw['ros_clock']['invalid_messages'],4)
        self.assertEqual(self.m.raw['native_stats']['invalid_samples'],2)

    def test_commands_only_fixed_topic_read_operations(self):
        self.assertEqual(ECHO,('/usr/bin/ign','topic','-e','-t','/world/warehouse/stats','--json-output','-d','8','--force-version','11'))
        self.assertEqual(INFO,('/usr/bin/ign','topic','-i','-t','/world/warehouse/stats','--force-version','11'))
        for command in (ECHO,INFO):
            self.assertNotIn('-p',command);self.assertNotIn('service',command)

    def test_child_main_with_fake_ros_and_pipe_fixtures_only(self):
        import io
        callback=[];commands=[];tick=[0]
        node=types.SimpleNamespace(create_subscription=lambda typ,topic,cb,qos:callback.append(cb),destroy_node=lambda:None)
        def create_node(name,**kwargs):
            self.assertEqual(kwargs,{'enable_rosout':False,'start_parameter_services':False})
            return node
        def spin(node,timeout_sec):
            tick[0]+=1;callback[0](types.SimpleNamespace(clock=types.SimpleNamespace(sec=0,nanosec=tick[0]*3000000)))
        fake_ros=types.SimpleNamespace(init=lambda **kw:None,create_node=create_node,spin_once=spin,shutdown=lambda:None)
        class Process:
            def __init__(self, command, **kwargs):
                commands.append(command);read,write=os.pipe()
                value=(b'Publishers [Address, Message Type]:\n  private, ignition.msgs.WorldStatistics\n' if command==INFO else self_stat)
                os.write(write,value);os.close(write);self.stdout=os.fdopen(read,'rb');self.returncode=0
            def poll(self):return 0
            def wait(self,timeout):return 0
        self_stat=self.stat()+self.stat(25,75000000)
        modules={'rclpy':fake_ros,'rclpy.qos':types.SimpleNamespace(qos_profile_sensor_data=object()),
                 'rclpy.signals':types.SimpleNamespace(SignalHandlerOptions=types.SimpleNamespace(NO=0)),
                 'rosgraph_msgs':types.SimpleNamespace(),'rosgraph_msgs.msg':types.SimpleNamespace(Clock=object())}
        output=io.StringIO()
        with patch.dict(sys.modules,modules),patch('startup_observer_child.subprocess.Popen',Process),patch('startup_observer_child.WINDOW_S',.03),patch('startup_observer_child.signal.signal'),patch('sys.stdout',output):
            self.assertEqual(child_main(['--origin',str(time.monotonic()-5)]),0)
        result=json.loads(output.getvalue())
        self.assertEqual(commands,[ECHO,INFO])
        self.assertEqual(result['native_stats']['samples'],2)
        self.assertTrue(result['native_stats']['sim_time_advanced'])
        self.assertTrue(result['ros_clock']['sim_time_advanced'])
        self.assertNotIn('private',output.getvalue())


if __name__=='__main__':unittest.main()
