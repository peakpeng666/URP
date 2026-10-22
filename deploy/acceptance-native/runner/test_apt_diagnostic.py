import pathlib, tempfile, unittest
from unittest.mock import patch, Mock
from runner.apt_diagnostic import TARGET, BASE, solver_command, diagnose

class AptDiagnosticTests(unittest.TestCase):
    def test_fixed_manifest_command_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'deploy').mkdir()
            raw=b'# pinned manifest\nlibunwind-dev\ng++\n'
            (root/'deploy/ros-packages.txt').write_bytes(raw)
            with patch('runner.apt_diagnostic.subprocess.check_output',side_effect=[(TARGET+'\n').encode(),raw]):cmd=solver_command(root)
            self.assertEqual(cmd,['apt-get','--simulate','-o','Debug::pkgProblemResolver=yes','install','--no-install-recommends',*BASE,'libunwind-dev','g++'])
            self.assertNotIn('sudo',cmd)
    def test_changed_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);(root/'deploy').mkdir();(root/'deploy/ros-packages.txt').write_text('unexpected\n')
            with patch('runner.apt_diagnostic.subprocess.check_output',side_effect=[TARGET.encode(),b'original\n']):
                with self.assertRaisesRegex(ValueError,'tracked_blob_mismatch'):solver_command(root)
    def test_diagnostic_never_executes_real_apt_in_test(self):
        with patch('runner.apt_diagnostic.solver_command',return_value=['apt-get','--simulate']) as command, patch('runner.apt_diagnostic.subprocess.run',return_value=Mock(returncode=100)) as run, patch('builtins.print') as output:
            diagnose('/isolated')
            self.assertEqual(run.call_args.kwargs['timeout'],90)
            self.assertFalse(run.call_args.kwargs['check'])
            self.assertEqual(run.call_args.kwargs['env']['LC_ALL'],'C')
            output.assert_called_once_with('URP_APT_SOLVER_EXIT_100',flush=True)

if __name__=='__main__':unittest.main()
