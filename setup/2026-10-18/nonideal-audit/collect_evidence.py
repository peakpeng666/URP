"""Collect compact audit evidence without changing original simulation records.

Run from the repository root with src/lab/.venv/bin/python. Full runtime data
stays local. Session keys are redacted only in copied reports/logs, and both the
original and copied bytes are hashed. This is packaging, not a simulator test.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
ROUNDS = ('coplanar-v4', 'coplanar-repeat73', 'coplanar-repeat74', 'release', 'guard-release')


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def redact(value, path=()):
    if isinstance(value, dict):
        return {k: '[redacted ephemeral session key]' if k == 'key' and path[-1:] == ('gazebo',) and isinstance(v, str)
                else redact(v, (*path, k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, path) for v in value]
    return value


def main():
    sessions, cases, raw = [], [], []
    for name in ROUNDS:
        summary = read(OUT / name / 'summary.json')
        assert summary['all_expected'], name
        for row in summary['results']:
            sid = row['session_id']
            sessions.append((f'{name}-{row["case"]}', OUT / name / 'runtime/fieldsim' / sid))
            cases.append({'round': name, 'case': row['case'], 'session_id': sid,
                          'state': row['state'], 'returncode': row['returncode'],
                          'cleanup': row['cleanup'], 'checks': row['checks'],
                          'metrics': row['metrics'], 'errors': row['errors'],
                          'wheel_truth_max_m': max(v['odom_position_max_m'] for v in row['verdict']['dynamics']['vehicles']),
                          'zone_contact_entries': sum(c['contact_entries'] for c in row['ground_contacts'] if 'ground_zones::' in c['surface'])})
    regression = read(OUT / 'field-regression-final/summary.json')
    assert len(regression) == 9
    for row in regression:
        sessions.append((f'regression-{row["case"]}', OUT / 'field-regression-final/runtime/fieldsim' / row['session_id']))
    ui = read(OUT / 'ui-guard-verification.json')
    sessions.append(('ui-guard', ROOT / 'src/lab/runtime/fieldsim' / ui['session_id']))
    for label, runtime in sessions:
        report = read(runtime / 'session-report.json')
        assert report['cleanup_status'] == 'PASS' and not report['remaining_owned_processes'], label
        plan = read(runtime / 'plan.json')
        destination = OUT / 'logs' / label
        save(destination / 'session-report.json', redact(report))
        save(destination / 'provenance.json', plan['execution_provenance'])
        save(destination / 'frozen-execution.json', {k: plan.get(k) for k in ('execution', 'ground_zones_audit', 'physics_audit')})
        keys = []
        def find_keys(v, path=()):
            if isinstance(v, dict):
                for k, val in v.items():
                    if k == 'key' and path[-1:] == ('gazebo',) and isinstance(val, str) and val:
                        keys.append(val)
                    else:
                        find_keys(val, (*path, k))
            elif isinstance(v, list):
                for val in v: find_keys(val, path)
        find_keys(report)
        # The supervisor log lives outside the session folder.
        files = list((runtime / 'logs').glob('*.log')) + list(runtime.glob('check.*'))
        supervisor = runtime.parents[1] / 'logs' / f'fieldsim-{runtime.name}.log'
        if supervisor.exists(): files.append(supervisor)
        for path in files:
            text = path.read_text()
            for key in keys: text = text.replace(key, '[redacted ephemeral session key]')
            target = destination / path.name
            target.write_text(text)
        for path in runtime.rglob('*'):
            if path.is_file():
                raw.append({'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size,
                            'sha256': digest(path)})
    save(OUT / 'physical-cases.json', cases)
    save(OUT / 'field-regression-summary.json', regression)
    save(OUT / 'raw-manifest.json', {'scope': 'Original local run files, including unredacted private session reports; not uploaded.', 'files': raw})
    source = set()
    for _, runtime in sessions:
        source.update(read(runtime / 'plan.json')['execution_provenance']['source_sha256'])
    source.update(('uv.lock', 'src/lab/uv.lock', 'src/frontend/package-lock.json', '.github/workflows/ci.yml',
                   'src/lab/e2e/nonideal_audit.py', 'src/lab/tests/test_nonideal_audit.py',
                   'src/lab/e2e/nonideal_backend.py', 'src/lab/tests/test_field_nonideal.py',
                   'src/lab/urp_lab/fieldsim.py', 'src/lab/urp_lab/gateway.py',
                   'src/frontend/src/studio/types.ts',
                   'src/frontend/src/studio/experiment/replay.ts',
                   'src/frontend/src/studio/experiment/traffic.ts',
                   'src/frontend/src/studio/panels/FieldSimPanel.tsx',
                   'src/frontend/src/studio/experiment/ExperimentPanel.tsx',
                   'src/frontend/src/studio/experiment/ReplayPanel.tsx',
                   'src/frontend/src/studio/experiment/SessionEvidence.tsx'))
    save(OUT / 'source-fingerprints.json', {p: digest(ROOT / p) for p in sorted(source)})
    preserved = read(OUT / 'takeover.json')['unrelated_files']
    assert all(digest(ROOT / p) == sha for p, sha in preserved.items()), 'Unrelated files changed'
    save(OUT / 'preserved-work.json', {'all_tracked_unrelated_hashes_unchanged': True,
         'paths': list(preserved), 'scope': 'Six pre-existing dirty literature metadata files; user PDFs left outside this commit.'})


if __name__ == '__main__':
    main()
