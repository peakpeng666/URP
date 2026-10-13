
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
