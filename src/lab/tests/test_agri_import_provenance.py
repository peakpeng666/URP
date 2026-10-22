"""Imported generator parameters remain reproducible without granting simulation access."""
import copy
import json
import pytest
from urp_lab import paths
from urp_lab import scenarios


def payload():
    return {'id': 'agri-import-test', 'title': '农业生成场景', 'problem_class': 'coverage',
            'frame': {'kind': 'field', 'units': 'm', 'crs': 'local'},
            'instance': {'field': [[0, 0], [100, 0], [100, 100], [0, 100]],
                         'obstacles': [], 'swath_width': 3, 'headland_width': 5, 'angle_deg': 0},
            'provenance': {'generator': 'urp.studio.agri', 'params': {'field_w': 100, 'pattern': 'coverage-tillage'}, 'seed': 42},
            'sim': {'supported': True}}


def test_import_preserves_generator_inputs_and_server_capabilities(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, 'USER_SCENARIOS', tmp_path)
    monkeypatch.setattr(scenarios, '_builtin', lambda: {})
    source = payload()
    original = copy.deepcopy(source)
    result = scenarios.import_scenario(source)
    saved = json.loads((tmp_path / (result['id'] + '.json')).read_text())
    assert source == original
    assert saved['provenance']['generator'] == 'user_import'
    assert saved['provenance']['source_generator'] == 'urp.studio.agri'
    assert saved['provenance']['params'] == original['provenance']['params']
    assert saved['provenance']['seed'] == 42
    assert saved['sim']['supported'] is False


@pytest.mark.parametrize('seed', [True, '42', 1.5])
def test_import_rejects_noninteger_seed(seed, tmp_path, monkeypatch):
    monkeypatch.setattr(paths, 'USER_SCENARIOS', tmp_path)
    monkeypatch.setattr(scenarios, '_builtin', lambda: {})
    obj = payload(); obj['provenance']['seed'] = seed
    with pytest.raises(ValueError, match='种子'):
        scenarios.import_scenario(obj)
    assert not list(tmp_path.glob('*.json'))


def test_import_rejects_nonfinite_generator_parameter(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, 'USER_SCENARIOS', tmp_path)
    monkeypatch.setattr(scenarios, '_builtin', lambda: {})
    obj = payload(); obj['provenance']['params']['field_w'] = float('nan')
    with pytest.raises(ValueError, match='生成参数'):
        scenarios.import_scenario(obj)
    assert not list(tmp_path.glob('*.json'))


def test_legacy_import_without_provenance(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, 'USER_SCENARIOS', tmp_path)
    monkeypatch.setattr(scenarios, '_builtin', lambda: {})
    obj = payload(); del obj['provenance']
    result = scenarios.import_scenario(obj)
    saved = json.loads((tmp_path / (result['id'] + '.json')).read_text())
    assert saved['provenance']['params'] == {} and saved['provenance']['seed'] is None


def test_reimport_keeps_original_generator(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, 'USER_SCENARIOS', tmp_path)
    monkeypatch.setattr(scenarios, '_builtin', lambda: {})
    scenarios.import_scenario(payload())
    saved = json.loads((tmp_path / 'agri-import-test.json').read_text())
    saved['id'] = 'agri-import-copy'
    scenarios.import_scenario(saved)
    restored = json.loads((tmp_path / 'agri-import-copy.json').read_text())
    assert restored['provenance']['source_generator'] == 'urp.studio.agri'
    assert restored['provenance']['params'] == saved['provenance']['params']
    assert restored['provenance']['seed'] == 42
