import json
import threading
from types import SimpleNamespace

from urp_lab.fieldsim import FieldSimManager


def test_index_caches_compact_data_and_invalidates_replacements_and_deletions(tmp_path, monkeypatch):
    service = FieldSimManager(None, SimpleNamespace(_lock=threading.RLock()), runtime=tmp_path)
    p = tmp_path / 'fieldsim' / 's' / 'result.json'
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({'session_id': 's', 'run_id': 'r', 'metrics': {'value': 1},
                            'trails': {'v': [[0, 0, 0, 0]] * 1000}}))
    rows = service.results()
    assert rows[0]['metrics'] == {'value': 1} and 'trails' not in rows[0]
    rows[0]['metrics']['value'] = 999
    with monkeypatch.context() as m:
        m.setattr(type(p), 'read_text', lambda *a, **k: (_ for _ in ()).throw(AssertionError('cache missed')))
        assert service.results('r')[0]['metrics']['value'] == 1
        assert service.results('another') == []
    replacement = p.with_suffix('.tmp')
    replacement.write_text(json.dumps({'session_id': 's', 'run_id': 'r', 'metrics': {'value': 2}}))
    replacement.replace(p)
    assert service.results()[0]['metrics']['value'] == 2
    p.unlink()
    assert service.results() == [] and service._result_cache == {}


def test_live_evidence_omits_traces_but_full_export_preserves_them(tmp_path):
    from fastapi.testclient import TestClient
    from urp_lab.gateway import Config, create_app
    p = tmp_path / 'fieldsim' / 'large' / 'result.json'
    p.parent.mkdir(parents=True)
    original = {'session_id': 'large', 'run_id': 'r', 'state': 'failed', 'check': {'valid': False},
                'physics': {'schema': 'test'}, 'trails': {'v': [[0, 0, 0, 0]] * 10000},
                'wheel_odometry': {'v': [[0, 0, 0, 0, 0, 0]] * 10000}}
    p.write_text(json.dumps(original))
    (p.parent / 'plan.json').write_text('{}')
    (p.parent / 'session-report.json').write_text('{"status":"FAIL","cleanup_status":"PASS"}')
    with TestClient(create_app(Config(runtime=tmp_path, background=False, archive_autostart=False,
                                      extra_hosts={'testserver'}))) as client:
        full = client.get('/lab/api/fieldsim/results/large')
        thin = client.get('/lab/api/fieldsim/results/large?evidence=true')
        assert full.status_code == thin.status_code == 200
        assert full.json()['trails'] == original['trails'] and full.json()['wheel_odometry'] == original['wheel_odometry']
        assert len(thin.content) < len(full.content) / 100
        assert thin.json()['check'] == {'valid': False} and thin.json()['session_report']['status'] == 'FAIL'
        assert 'trails' not in thin.json() and thin.headers['cache-control'] == 'no-store'
        assert client.get('/lab/api/fieldsim/results/missing?evidence=true').status_code == 404
    assert json.loads(p.read_text()) == original
