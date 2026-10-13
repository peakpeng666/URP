"""Offline tests: the only spawned process is this file's fake CLI, with env={}.

The fake inspects effective argv/config/stdin but performs no network activity.
These tests do not prove that OpenCode or GLM applies the requested settings.
"""
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import runner

FAKE = r'''
import hashlib, json, os, sys, time
from pathlib import Path
mode = sys.argv[1]
prompt = sys.stdin.buffer.read()
config = json.loads(Path(os.environ['OPENCODE_CONFIG']).read_text())
observed = {'argv': sys.argv[2:], 'prompt_sha256': hashlib.sha256(prompt).hexdigest(),
 'configuration': config, 'output_cap_env': os.environ.get('OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX'),
 'cwd': str(Path.cwd()), 'cwd_entries_before': [p.name for p in Path.cwd().iterdir()],
 'home': os.environ['HOME'], 'xdg': {k: os.environ[k] for k in ['XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME']},
 'credential_env_present_in_fixture': 'ZHIPU_API_KEY' in os.environ}
Path('fake_observed.json').write_text(json.dumps(observed))
print(json.dumps({'type': 'reasoning', 'part': {'text': 'DO_NOT_SAVE_REASONING'}}), flush=True)
print('DO_NOT_SAVE_STDERR', file=sys.stderr, flush=True)
print(json.dumps({'type': 'text', 'part': {'id': 'p1', 'text': '{fixture only}\n```python\ndef score(item, bins):\n    return bins * 0\n```'}}), flush=True)
if mode == 'timeout':
 time.sleep(20)
if mode == 'error':
 print(json.dumps({'type': 'error', 'error': {'headers': {'Authorization': 'DO_NOT_SAVE_AUTH'}}}), flush=True)
elif mode != 'unknown_usage':
 print(json.dumps({'type': 'step_finish', 'part': {'reason': 'stop', 'tokens': {'input': 11, 'output': 7, 'reasoning': 3}}}), flush=True)
sys.exit(7 if mode == 'nonzero' else 0)
'''


class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = runner.load_inputs()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='minimal-runner-fake-')
        self.root = Path(self.temp.name)
        self.fake = self.root / 'fake_cli.py'
        self.fake.write_text(FAKE)
        self.ledger = self.root / 'fixture_ledger'
        self.slot = self.data['slots'][0]['pack']['slot_id']

    def tearDown(self):
        self.temp.cleanup()

    def run_fake(self, mode='normal', position=1, timeout=None):
        return runner.run_one(self.data, self.ledger, position,
            [sys.executable, str(self.fake), mode], fixture=True, test_timeout=timeout)

    def test_normal_exit_and_exact_parameters_at_fake_process(self):
        result = self.run_fake()
        folder = self.ledger / self.slot
        observed = json.loads((folder / 'work/fake_observed.json').read_bytes())
        config = observed['configuration']
        model = config['provider']['zhipuai-coding-plan']['models']['glm-5.3']
        self.assertEqual((result['client_state'], result['exit_code']), ('exited', 0))
        self.assertEqual(model['limit']['output'], 64000)
        self.assertEqual(model['options']['reasoningEffort'], 'high')
        self.assertEqual(observed['output_cap_env'], '64000')
        self.assertEqual(config['agent']['candidate']['temperature'], .7)
        self.assertEqual(config['agent']['candidate']['top_p'], .9)
        self.assertEqual(config['agent']['candidate']['tools'], {'*': False})
        self.assertEqual(config['agent']['candidate']['steps'], 2)
        self.assertEqual(config['provider']['zhipuai-coding-plan']['options']['timeout'], 900000)
        self.assertEqual(config['enabled_providers'], ['zhipuai-coding-plan'])
        self.assertEqual(config['provider']['zhipuai-coding-plan']['options']['baseURL'], 'https://open.bigmodel.cn/api/coding/paas/v4')
        self.assertEqual(observed['prompt_sha256'], self.data['slots'][0]['pack']['prompt_sha256'])
        self.assertEqual(observed['argv'], ['--log-level', 'ERROR', '--pure', 'run', '--dir', str(folder / 'work'), '--agent', 'candidate', '--model', runner.MODEL, '--title', self.slot, '--format', 'json'])
        self.assertEqual(result['requested_timeout_seconds'], 900)
        self.assertEqual(result['cli_reported_tokens'], {'input': 11, 'output': 7, 'reasoning': 3})
        self.assertIsNone(result['provider_usage'])
        self.assertIsNone(result['physical_http_attempts'])

    def test_timeout_is_terminal_client_state_and_never_reruns(self):
        result = self.run_fake('timeout', timeout=.15)
        self.assertEqual(result['client_state'], 'timeout')
        self.assertEqual(result['exit_code'], -9)
        self.assertGreater(result['answer_bytes'], 0)
        self.assertLess(result['wall_seconds'], 2)
        with self.assertRaisesRegex(ValueError, 'never be rerun'):
            self.run_fake()

    def test_dispatched_slot_rejected_without_overwriting(self):
        self.run_fake()
        before = (self.ledger / self.slot / 'dispatch.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'never be rerun'):
            self.run_fake()
        self.assertEqual(before, (self.ledger / self.slot / 'dispatch.json').read_bytes())

    def test_residual_unknown_stays_unknown_and_stops_sequence(self):
        (self.ledger / self.slot).mkdir(parents=True)
        (self.ledger / self.slot / 'dispatch.json').write_text('{"state":"may_have_started_once"}')
        self.assertEqual(runner.state(self.ledger, self.slot), 'unknown')
        with self.assertRaisesRegex(ValueError, 'never be rerun'):
            self.run_fake()
        with self.assertRaisesRegex(ValueError, 'Earlier slot'):
            self.run_fake(position=2)
        self.assertFalse((self.ledger / self.data['slots'][1]['pack']['slot_id']).exists())

    def test_partial_or_missing_dispatch_also_unknown(self):
        (self.ledger / self.slot).mkdir(parents=True)
        (self.ledger / self.slot / 'result.pending.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'never be rerun'):
            self.run_fake()
        self.assertEqual(runner.state(self.ledger, self.slot), 'unknown')

    def test_unknown_usage_is_null_never_zero(self):
        result = self.run_fake('unknown_usage')
        self.assertEqual(result['cli_reported_tokens'], {'input': None, 'output': None, 'reasoning': None})
        self.assertIsNone(result['provider_cost'])
        self.assertIsNone(result['provider_usage'])
        self.assertEqual(result['provider_outcome'], 'unknown')

    def test_nonzero_exit_retained_not_retried(self):
        result = self.run_fake('nonzero')
        self.assertEqual((result['client_state'], result['exit_code']), ('exited', 7))
        with self.assertRaises(ValueError):
            self.run_fake()

    def test_only_answer_and_safe_metadata_are_saved(self):
        result = self.run_fake('error')
        content = b''.join(p.read_bytes() for p in (self.ledger / self.slot).rglob('*') if p.is_file())
        for marker in (b'DO_NOT_SAVE_AUTH', b'DO_NOT_SAVE_STDERR', b'DO_NOT_SAVE_REASONING'):
            self.assertNotIn(marker, content)
        self.assertIn('cli_error_event', result['capture_issues'])

    def test_sequential_slots_have_distinct_empty_runtime(self):
        self.run_fake()
        self.run_fake(position=2)
        for item in self.data['slots'][:2]:
            folder = self.ledger / item['pack']['slot_id']
            observed = json.loads((folder / 'work/fake_observed.json').read_bytes())
            self.assertEqual(observed['cwd'], str(folder / 'work'))
            self.assertEqual(observed['cwd_entries_before'], [])
            self.assertEqual(observed['home'], str(folder / 'home'))
            self.assertFalse(observed['credential_env_present_in_fixture'])
            for value in observed['xdg'].values():
                self.assertTrue(Path(value).is_relative_to(folder))

    def test_no_skip_and_competing_runner_cannot_dispatch(self):
        with self.assertRaisesRegex(ValueError, 'Earlier slot'):
            self.run_fake(position=2)
        with (self.ledger / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.run_fake()
        self.assertFalse((self.ledger / self.slot).exists())

    def test_unapproved_binary_rejected_before_dispatch(self):
        with self.assertRaisesRegex(ValueError, 'official OpenCode'):
            runner.run_one(self.data, self.ledger, 1, [str(self.fake)])
        self.assertFalse((self.ledger / self.slot).exists())

    def test_frozen_sequence_and_all_prompt_hashes(self):
        slots = self.data['slots']
        self.assertEqual([s['record']['order'] for s in slots], list(range(73, 133)))
        self.assertEqual(sum(s['record']['arm'] == 'EOH_TC' for s in slots), 30)
        self.assertEqual(sum(s['record']['arm'] == 'IID_TC' for s in slots), 30)
        for s in slots:
            self.assertEqual(hashlib.sha256(s['pack']['prompt'].encode()).hexdigest(), s['record']['prompt_sha256'])
            self.assertEqual(s['pack']['parents'], s['record']['parents'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
