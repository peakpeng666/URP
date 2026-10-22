import json,pathlib,tempfile,unittest
from startup_diagnostics import session_id,project,collect,sanitize
from public_summary import project as public_project
SID='sim_20261022T080000_abcdef'

class StartupDiagnosticsTests(unittest.TestCase):
    def test_exact_start_step_recovers_id_before_ready_failure(self):
        report={'status':'FAIL','steps':[{'name':'start simulation session','ok':True,'response':{'session_id':SID}},{'name':'session ready','ok':False}]}
        self.assertEqual(session_id(report),SID)
        self.assertEqual(report['status'],'FAIL')
        for bad in ('../x',SID+'/x','sim_private',SID+'\\x'):
            report['steps'][0]['response']['session_id']=bad;self.assertIsNone(session_id(report))
    def test_ambiguous_or_wrong_step_rejected(self):
        report={'steps':[{'name':'session ready','ok':True,'response':{'session_id':SID}}]}
        self.assertIsNone(session_id(report))
        report={'steps':[{'name':'start simulation session','ok':True,'response':{'session_id':SID}},{'name':'start simulation session','ok':True,'response':{'session_id':SID[:-1]+'1'}}]}
        self.assertIsNone(session_id(report))
    def test_private_projection_drops_all_raw_strings(self):
        report={'errors':['RuntimeError: 控制器/传感器未就绪 PRIVATE_PATH','关键服务 sim 意外退出，状态 1 PRIVATE_URL'],'counts':{'clock':2,'odom':3,'PRIVATE':999},'stages':[{'name':'starting','wall_s':0},{'name':'failed','wall_s':80}], 'assets':{'complete':False,'missing':['PRIVATE_ASSET']}}
        logs={'sim':'PRIVATE_PID PRIVATE_CMD process has died exit code -11 PRIVATE_URL'}
        result=project(report,logs);text=json.dumps(result)
        self.assertNotIn('PRIVATE',text);self.assertIn('sensors_not_ready',result['error_codes'])
        self.assertEqual(result['counts']['clock'],2);self.assertEqual(result['counts']['scan'],0)
        self.assertEqual(result['assets_missing_count'],1)
        self.assertEqual(result['component_exits'],[{'component':'sim','exit_code':-11}])
        raw={'state':'FAIL','startup_diagnostics':result}
        self.assertEqual(public_project(raw,require_runner=False)['state'],'FAIL')
    def test_bounded_private_files_and_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp)/'sim'/SID;root.mkdir(parents=True);(root/'logs').mkdir()
            (root/'session-report.json').write_text(json.dumps({'counts':{'clock':7},'errors':['AMCL 初始定位超时']}))
            self.assertEqual(collect(tmp,SID)['counts']['clock'],7)
            (root/'logs/sim.log').symlink_to('/etc/passwd')
            self.assertEqual(collect(tmp,SID)['component_exits'],[])
            self.assertFalse(collect(tmp,'../bad')['report_available'])
    def test_untrusted_diagnostic_shape_is_sanitized(self):
        result=sanitize({'phase':'PRIVATE','error_codes':['PRIVATE'],'counts':{'clock':True},'stages':[{'phase':'starting','wall_s':float('inf')}],'component_exits':[{'component':'PRIVATE','exit_code':4}]})
        self.assertNotIn('PRIVATE',json.dumps(result));self.assertEqual(result['stages'],[])
        self.assertIsNone(result['counts']['clock'])
        self.assertIsNone(sanitize({'counts':{'clock':10**1000}})['counts']['clock'])
        self.assertEqual(project({'stages':None},{})['stages'],[])
        self.assertIn('python_module_missing',project({}, {'session':'ModuleNotFoundError: PRIVATE_MODULE'})['error_codes'])
    def test_install_progress_is_fixed_enum(self):
        from runner.run import installation_progress
        with tempfile.TemporaryDirectory() as tmp:
            log=pathlib.Path(tmp)/'install'
            for line,expected in [('sudo apt-get install PRIVATE','apt'),('uv sync PRIVATE','uv'),('npm ci PRIVATE','npm'),('bash src/lab/ros/native/install-ros-extras.sh PRIVATE','native')]:
                log.write_text('+URP_SETUP '+line+'\n')
                self.assertEqual(installation_progress(log),expected)

if __name__=='__main__':unittest.main()
