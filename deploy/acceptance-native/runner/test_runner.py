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
            self.assertEqual(status,{'stage':'installation','exit_code':7,'cleanup_remaining':0,'failure_hint':'unknown'})
            self.assertIn('PRIVATE_TEST_MARKER',(root/'private/install.log').read_text())

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
            cases={'source_identity':'tracked_blob_mismatch','registry_identity':'npm_mirror_identity_mismatch','package_install':'E: Unable to locate package','dependency_fetch':'Failed to download','network':'Could not resolve host','disk_full':'No space left on device','native_build':'CMake Error','unknown':'other error'}
            for hint, marker in cases.items():
                path.write_text(marker+' PRIVATE_PACKAGE_AND_PATH')
                self.assertEqual(classify(path,1),hint)
                self.assertEqual(classify(path,0),'none')
            path.write_bytes(b'No space left on device'+b'x'*LIMIT)
            self.assertEqual(classify(path,1),'unknown')
            self.assertEqual(classify(pathlib.Path(tmp)/'absent',1),'unknown')

if __name__=='__main__':unittest.main()
