"""The public CLI must not turn a failed solver/checker into shell success."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('baseline_cli', ROOT / 'scripts/baseline.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)


class BaselineExitTests(unittest.TestCase):
    def test_solver_failure_reaches_main_return_value(self):
        with patch.object(baseline, 'solve', return_value={'returncode': 7}), \
             patch('sys.argv', ['baseline.py', 'run', '--case', 'A-n32-k5', '--algorithm', 'savings']), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(baseline.main(), 7)

    def test_checker_failure_or_missing_evidence_cannot_pass(self):
        for score_status, write_evaluation in [(3, True), (0, False), (0, True)]:
            with self.subTest(status=score_status, evidence=write_evaluation), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'run'
                def run(command, **kwargs):
                    if 'run-one' in command:
                        output.mkdir()
                        (output / 'result.json').write_text(json.dumps({'case_manifest_sha256': 'fixture'}))
                        return types.SimpleNamespace(returncode=0)
                    if write_evaluation:
                        (output / 'evaluation.json').write_text('{}')
                    return types.SimpleNamespace(returncode=score_status)
                with patch.object(baseline, 'output_path', return_value=output), \
                     patch.object(baseline.subprocess, 'run', side_effect=run):
                    result = baseline.solve('A-n32-k5', 'savings')
                self.assertEqual(result['returncode'], score_status if score_status else (0 if write_evaluation else 2))
                self.assertEqual(result['score_returncode'], score_status)


if __name__ == '__main__':
    unittest.main()
