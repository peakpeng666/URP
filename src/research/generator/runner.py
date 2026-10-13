#!/usr/bin/env python3
"""A local, once-only CLI runner. Default operation is read-only inspection.

No Library transactions, retries, resume, model HTTP client, or secret handling.
A slot directory is permanent evidence that launch may have happened, even when
its dispatch/result file is missing. Never delete one to make a slot runnable.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time

REVISION = 'minimal-local-execution-r1'
INPUT_SHA256 = '52f1505c9bab0ef6a821be8a28564b8ee601a66d20bbe17e918226bb5719865f'
ROOT = Path(__file__).resolve().parent
MODEL = 'zhipuai-coding-plan/glm-5.3'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_inputs():
    raw = (ROOT / 'frozen_inputs.json').read_bytes()
    if digest(raw) != INPUT_SHA256:
        raise ValueError('Frozen inputs changed; do not launch.')
    return json.loads(raw)


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_bytes(path, raw):
    with path.open('xb') as file:
        file.write(raw)
        file.flush()
        os.fsync(file.fileno())
    sync_dir(path.parent)


def write_json(path, value):
    write_bytes(path, (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode())


def state(ledger, slot_id):
    folder = ledger / slot_id
    if not folder.exists():
        return 'not_dispatched'
    try:
        return json.loads((folder / 'result.json').read_bytes())['client_state']
    except (OSError, ValueError, KeyError):
        return 'unknown'


def command_for(binary, folder, slot_id):
    # Use the frozen official CLI route, plus a clean HOME for stronger isolation.
    overrides = {key: str(folder / name) for key, name in (
        ('HOME', 'home'), ('XDG_CONFIG_HOME', 'xdg-config'),
        ('XDG_DATA_HOME', 'xdg-data'), ('XDG_CACHE_HOME', 'xdg-cache'),
        ('XDG_STATE_HOME', 'xdg-state'), ('OPENCODE_CONFIG_DIR', 'config'), ('PWD', 'work'))}
    overrides['OPENCODE_CONFIG'] = str(folder / 'config/opencode.json')
    overrides['OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX'] = '64000'
    for name in ('OPENCODE_DISABLE_AUTOUPDATE', 'OPENCODE_DISABLE_MODELS_FETCH',
                 'OPENCODE_DISABLE_DEFAULT_PLUGINS', 'OPENCODE_DISABLE_CLAUDE_CODE',
                 'OPENCODE_DISABLE_PROJECT_CONFIG', 'OPENCODE_DISABLE_AUTOCOMPACT',
                 'OPENCODE_DISABLE_LSP_DOWNLOAD', 'OPENCODE_EXPERIMENTAL_DISABLE_FILEWATCHER'):
        overrides[name] = 'true'
    # Iterate names only. Inherit the existing credential through the OS, without
    # reading, printing, copying, validating, or saving its value in Python.
    cleared = [arg for name in sorted(os.environ) if name.startswith('OPENCODE_') for arg in ('-u', name)]
    args = ['--log-level', 'ERROR', '--pure', 'run', '--dir', str(folder / 'work'),
            '--agent', 'candidate', '--model', MODEL, '--title', slot_id, '--format', 'json']
    command = ['/usr/bin/env', *cleared, *(f'{k}={v}' for k, v in overrides.items()), *binary, *args]
    return command, overrides


def capture(command, folder, timeout, fixture):
    """Keep literal model text and numeric usage; discard reasoning/error bodies.

    Raw stderr and complete event objects are deliberately not stored: they can
    contain credentials or unrelated tool contents. This is raw answer capture,
    not a raw network/CLI transcript or proof of the provider's final outcome.
    """
    started = time.monotonic()
    process, code, client_state = None, None, 'launch_failed'
    texts, usage, finishes, issues, pending = {}, [], [], [], b''
    selected = selectors.DefaultSelector()
    try:
        with (folder / 'prompt.txt').open('rb') as stdin:
            process = subprocess.Popen(command, cwd=folder / 'work', stdin=stdin,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env={} if fixture else None, start_new_session=True)
        client_state = 'unknown'
        selected.register(process.stdout, selectors.EVENT_READ)
        eof = False
        while not eof:
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                client_state = 'timeout'
                break
            for key, _ in selected.select(min(remaining, 0.1)):
                chunk = os.read(key.fd, 65536)
                if not chunk:
                    eof = True
                    break
                pending += chunk
                if len(pending) > 8 * 1024 * 1024:
                    raise ValueError('Oversize event')
                while b'\n' in pending:
                    line, pending = pending.split(b'\n', 1)
                    try:
                        event = json.loads(line)
                        part = event.get('part') or {}
                        kind = event.get('type')
                        if kind == 'text' and isinstance(part.get('text'), str):
                            texts[part.get('id', str(len(texts)))] = part['text']
                            # Replace only our own partial answer file, never the ledger.
                            temporary = folder / 'answer.partial'
                            temporary.write_text(''.join(texts.values()), encoding='utf-8')
                            os.replace(temporary, folder / 'answer.txt')
                        elif kind == 'step_finish':
                            tokens = part.get('tokens') or {}
                            usage.append({k: tokens.get(k) if type(tokens.get(k)) is int and tokens[k] >= 0 else None
                                          for k in ('input', 'output', 'reasoning')})
                            finishes.append(part.get('reason') if part.get('reason') in ('stop', 'length', 'tool-calls') else None)
                        elif kind in ('error', 'tool_use'):
                            issues.append('cli_error_event' if kind == 'error' else 'unexpected_tool_event')
                            if kind == 'tool_use':
                                raise RuntimeError('Tools are disabled')
                    except (ValueError, TypeError, AttributeError):
                        issues.append('unparsed_event')  # Never log the event/error body.
        if pending:
            issues.append('incomplete_final_event')
        if client_state != 'timeout':
            code = process.wait(timeout=max(0.001, timeout - (time.monotonic() - started)))
            client_state = 'exited'
    except subprocess.TimeoutExpired:
        client_state = 'timeout'
    except KeyboardInterrupt:
        client_state = 'interrupted'
    except (OSError, RuntimeError, ValueError):
        client_state = 'launch_failed' if process is None else 'capture_failed'
    finally:
        selected.close()
        if process is not None:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            code = process.wait()
            process.stdout.close()
    if not (folder / 'answer.txt').exists():
        write_bytes(folder / 'answer.txt', b'')
    answer = (folder / 'answer.txt').read_bytes()
    with (folder / 'answer.txt').open('rb') as file:
        os.fsync(file.fileno())
    reported = {k: sum(row[k] for row in usage) if usage and all(row[k] is not None for row in usage) else None
                for k in ('input', 'output', 'reasoning')}
    return {'client_state': client_state, 'exit_code': code, 'cli_process_started': process is not None,
            'wall_seconds': round(time.monotonic() - started, 6), 'requested_timeout_seconds': timeout,
            'answer_bytes': len(answer), 'answer_sha256': digest(answer), 'finish_reasons': finishes,
            'capture_issues': sorted(set(issues)), 'cli_reported_tokens': reported,
            'cli_reported_usage_records': usage,
            'provider_usage': None, 'provider_cost': None, 'physical_http_attempts': None,
            'provider_outcome': 'unknown', 'fixture_only': fixture,
            'scientific_validity': 'not_evaluated'}


def run_one(data, ledger, position, binary, *, fixture=False, test_timeout=None):
    if not 1 <= position <= 60:
        raise ValueError('Position must be 1..60.')
    ledger = ledger.resolve()
    ledger.mkdir(parents=True, exist_ok=True)
    with (ledger / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        item = data['slots'][position - 1]
        slot_id = item['pack']['slot_id']
        if state(ledger, slot_id) != 'not_dispatched':
            raise ValueError('Already dispatched or unknown; this slot can never be rerun.')
        for earlier in data['slots'][:position - 1]:
            if state(ledger, earlier['pack']['slot_id']) in ('not_dispatched', 'unknown'):
                raise ValueError('Earlier slot is unattempted or unknown; preserve frozen order and stop.')
        if not fixture:
            if len(binary) != 1 or digest(Path(binary[0]).read_bytes()) != data['freeze']['cli_binary_sha256']:
                raise ValueError('Use the frozen official OpenCode 1.18.34 binary.')
            if test_timeout is not None:
                raise ValueError('Test timeout is fixture-only.')
        # A single atomic mkdir is the once-only ledger claim. It is never undone.
        folder = ledger / slot_id
        folder.mkdir()
        sync_dir(ledger)
        for name in ('work', 'home', 'config', 'xdg-config', 'xdg-data', 'xdg-cache', 'xdg-state'):
            (folder / name).mkdir()
        write_bytes(folder / 'config/opencode.json', data['config_raw'].encode())
        write_bytes(folder / 'prompt.txt', item['pack']['prompt'].encode())
        command, overrides = command_for(binary, folder, slot_id)
        dispatch = {'revision': REVISION, 'frozen_inputs_sha256': INPUT_SHA256,
                    'position': position, 'order': item['record']['order'], 'slot_id': slot_id,
                    'arm': item['record']['arm'], 'prompt_sha256': item['pack']['prompt_sha256'],
                    'configuration': item['pack']['configuration'], 'config_sha256': digest(data['config_raw'].encode()),
                    'cli_version': data['freeze']['cli_version'], 'binary_sha256': None if fixture else data['freeze']['cli_binary_sha256'],
                    'command': command, 'safe_environment_overrides': overrides,
                    'stdin_file': 'prompt.txt', 'credential_value_observed_or_saved': False,
                    'dispatch_boundary_utc_seconds': time.time(), 'state': 'may_have_started_once',
                    'fixture_only': fixture}
        write_json(folder / 'dispatch.json', dispatch)  # Durable BEFORE Popen.
        timeout = test_timeout if fixture and test_timeout is not None else item['pack']['configuration']['wall_seconds']
        result = capture(command, folder, timeout, fixture)
        result.update({'revision': REVISION, 'slot_id': slot_id, 'position': position})
        write_json(folder / 'result.pending.json', result)
        os.replace(folder / 'result.pending.json', folder / 'result.json')
        sync_dir(folder)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['inspect', 'status', 'run-one'], nargs='?', default='inspect')
    parser.add_argument('--ledger', type=Path)
    parser.add_argument('--position', type=int)
    parser.add_argument('--opencode', type=Path)
    args = parser.parse_args()
    data = load_inputs()
    if args.action == 'inspect':
        print(json.dumps({'revision': REVISION, 'slots': 60, 'EOH_TC': 30, 'IID_TC': 30,
                          'configuration': data['freeze']['configuration'], 'dispatch_performed': False}, indent=2))
    elif args.action == 'status' and args.ledger:
        print(json.dumps([{'position': i + 1, 'slot_id': s['pack']['slot_id'],
                           'state': state(args.ledger, s['pack']['slot_id'])} for i, s in enumerate(data['slots'])], indent=2))
    elif args.action == 'run-one' and args.ledger and args.position and args.opencode:
        print(json.dumps(run_one(data, args.ledger, args.position, [str(args.opencode.resolve())]), indent=2))
    else:
        parser.error('status needs --ledger; run-one needs --ledger, --position and --opencode.')


if __name__ == '__main__':
    main()
