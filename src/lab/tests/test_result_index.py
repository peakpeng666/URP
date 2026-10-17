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
