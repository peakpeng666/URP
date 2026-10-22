import json, os, pathlib, shutil, signal, subprocess, sys, tempfile, time, unittest

class RunnerTests(unittest.TestCase):
    def test_failed_install_cleans_owned_child_and_keeps_output_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp); script=root/'run.py'
            shutil.copyfile(pathlib.Path(__file__).with_name('run.py'),script)
            (root/'install.sh').write_text('#!/bin/bash\necho PRIVATE_TEST_MARKER\nsleep 300 &\nexit 7\n')
            result=subprocess.run([sys.executable,str(script),'--source',str(root),'--harness',str(root),'--private-dir',str(root/'private'),'--harness-sha','a'*40],capture_output=True,text=True,timeout=35)
            self.assertEqual(result.returncode,1)
            self.assertEqual(json.loads(result.stdout),{'stage':'installation','state':'running'});self.assertEqual(result.stderr,'')
            status=json.loads((root/'private/runner-status.json').read_text())
            self.assertEqual(status,{'stage':'installation','exit_code':7,'cleanup_remaining':0,'forced_kill_count':0,'failure_hint':'unknown','installation_step':'unknown','apt_projection':{'status':'not_run','dependencies':[]}})
            self.assertIn('PRIVATE_TEST_MARKER',(root/'private/install.log').read_text())

    def test_successful_task_needing_forced_cleanup_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);script=root/'run.py'
            original=pathlib.Path(__file__).with_name('run.py').read_text()
            # Test-only shortened TERM grace; production keeps twenty seconds.
            self.assertIn('(signal.SIGTERM,20)',original)
            script.write_text(original.replace('(signal.SIGTERM,20)','(signal.SIGTERM,.3)'))
            (root/'install.sh').write_text('#!/bin/bash\nexit 0\n')
            (root/'src/lab/.venv/bin').mkdir(parents=True)
            (root/'src/lab/.venv/bin/python').symlink_to(sys.executable)
            xvfb=root/'Xvfb'
            xvfb.write_text('#!'+sys.executable+'\nimport os,sys,time\nos.write(int(sys.argv[sys.argv.index("-displayfd")+1]),b"99\\n")\ntime.sleep(300)\n')
            xvfb.chmod(0o755)
            child='import signal,pathlib,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);pathlib.Path("ready").touch();time.sleep(300)'
            (root/'acceptance.py').write_text('import subprocess,sys,pathlib,time\nsubprocess.Popen([sys.executable,"-c",'+repr(child)+'])\nwhile not pathlib.Path("ready").exists():time.sleep(.01)\n')
            env=dict(os.environ,PATH=str(root)+':'+os.environ['PATH'])
            result=subprocess.run([sys.executable,str(script),'--source',str(root),'--harness',str(root),'--private-dir',str(root/'private'),'--harness-sha','a'*40],capture_output=True,text=True,timeout=15,env=env)
            self.assertEqual(result.returncode,1)
            self.assertEqual(result.stderr,'')
            status=json.loads((root/'private/runner-status.json').read_text())
            self.assertEqual(status['stage'],'simulation')
            self.assertEqual(status['forced_kill_count'],1)
            self.assertEqual(status['cleanup_remaining'],0)
            self.assertNotEqual(status['exit_code'],0)
            # A normal Xvfb SIGTERM alone does not invalidate a successful task.
            (root/'acceptance.py').write_text('pass\n')
            result=subprocess.run([sys.executable,str(script),'--source',str(root),'--harness',str(root),'--private-dir',str(root/'normal-private'),'--harness-sha','a'*40],capture_output=True,text=True,timeout=15,env=env)
            self.assertEqual(result.returncode,0)
            normal=json.loads((root/'normal-private/runner-status.json').read_text())
            self.assertEqual(normal['forced_kill_count'],0)
            self.assertEqual(normal['cleanup_remaining'],0)

    def test_cancel_during_install_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp); script=root/'run.py'
            shutil.copyfile(pathlib.Path(__file__).with_name('run.py'),script)
            (root/'install.sh').write_text('#!/bin/bash\ntouch "$2/started"\nsleep 300\nexit 0\n')
            process=subprocess.Popen([sys.executable,str(script),'--source',str(root),'--harness',str(root),'--private-dir',str(root/'private'),'--harness-sha','a'*40],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            deadline=time.monotonic()+10
            while not (root/'private/started').exists() and time.monotonic()<deadline:time.sleep(.02)
            self.assertTrue((root/'private/started').exists())
            process.send_signal(signal.SIGTERM)
            stdout,stderr=process.communicate(timeout=35)
            self.assertNotEqual(process.returncode,0)
            status=json.loads((root/'private/runner-status.json').read_text())
            self.assertNotEqual(status['exit_code'],0)
            self.assertEqual(status['cleanup_remaining'],0)
            self.assertEqual(stderr,'')

    def test_bounded_failure_hints(self):
        from runner.run import classify, LIMIT
        with tempfile.TemporaryDirectory() as tmp:
            path=pathlib.Path(tmp)/'private.log'
            cases={'source_identity':'tracked_blob_mismatch','registry_identity':'npm_mirror_identity_mismatch','package_install':'dpkg: error','dependency_fetch':'Failed to download','network':'Could not resolve host','disk_full':'No space left on device','native_build':'CMake Error','unknown':'other error'}
            for hint, marker in cases.items():
                path.write_text(marker+' PRIVATE_PACKAGE_AND_PATH')
                self.assertEqual(classify(path,1),hint)
                self.assertEqual(classify(path,0),'none')
            path.write_bytes(b'No space left on device'+b'x'*LIMIT)
            self.assertEqual(classify(path,1),'unknown')
            self.assertEqual(classify(pathlib.Path(tmp)/'absent',1),'unknown')

    def test_apt_hints_and_trace_steps(self):
        from runner.run import classify, installation_step
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp)/'log'
            cases={'apt_dependency_conflict':'The following packages have unmet dependencies:', 'apt_libunwind_conflict':'libunwind-14-dev : Conflicts: libunwind-dev but it is to be installed', 'apt_signature':'NO_PUBKEY PRIVATE_KEY_ID','apt_source_conflict':'Conflicting values set for option Signed-By PRIVATE_URL','apt_release':'does not have a Release file','apt_hook':'Problem executing scripts APT::Update::Post-Invoke','apt_lock':'Could not get lock PRIVATE_PATH','apt_package_missing':'E: Unable to locate package PRIVATE_NAME'}
            for expected,text in cases.items():
                p.write_text('+URP_SETUP sudo apt-get update\n'+text)
                self.assertEqual(classify(p,100),expected)
                self.assertEqual(installation_step(p),'apt_update')
            p.write_text('+URP_SETUP sudo apt-get update\n+URP_SETUP sudo DEBIAN_FRONTEND=noninteractive apt-get install -y PRIVATE_PACKAGE\n')
            self.assertEqual(installation_step(p),'apt_install')
            p.write_text('libunwind-14-dev libunwind-dev\nUnable to correct problems, you have held broken packages.')
            self.assertEqual(classify(p,100),'apt_dependency_conflict')
            p.write_text('Broken libunwind-14-dev:amd64 Conflicts on libunwind-dev:amd64')
            self.assertEqual(classify(p,100),'apt_libunwind_conflict')
            p.write_text('+URP_SETUP sudo apt-get update\n+URP_SETUP uv sync --locked\n')
            self.assertEqual(installation_step(p),'other')

if __name__=='__main__':unittest.main()
