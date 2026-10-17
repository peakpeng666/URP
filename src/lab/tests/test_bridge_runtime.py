"""Bridge selection must be reversible and fail closed after unvalidated changes."""
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('bridge_runtime', Path(__file__).parents[1] / 'ros/bridge_runtime.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def test_explicit_system_bridge_needs_no_local_build(monkeypatch, tmp_path):
    monkeypatch.setattr(bridge, 'SOURCE', tmp_path / 'missing')
    monkeypatch.setenv('URP_BRIDGE_FIX', '0')
    assert bridge.bridge_environment() == {}


def test_invalid_bridge_choice_is_not_silently_enabled(monkeypatch):
    monkeypatch.setenv('URP_BRIDGE_FIX', 'maybe')
    with pytest.raises(RuntimeError, match='0 或 1'):
        bridge.bridge_environment()


def test_changed_dependency_cannot_fall_back_to_system_bridge(monkeypatch, tmp_path):
    lib = tmp_path / 'dependency.so'
    lib.write_bytes(b'changed dependency')
    (tmp_path / 'manifest.json').write_text(json.dumps({'sources': {}, 'system_files': {str(lib): 'unvalidated'}}))
    monkeypatch.setattr(bridge, 'SOURCE', tmp_path)
    monkeypatch.setenv('URP_BRIDGE_FIX', '1')
    with pytest.raises(RuntimeError, match='指纹变化'):
        bridge.bridge_environment()


@pytest.mark.parametrize('option,expected_issue', [('1', False), ('0', True), ('invalid', True)])
def test_gateway_bridge_status_matches_requested_mode(monkeypatch, option, expected_issue):
    from urp_lab.services import bridge_known_issues, bridge_note
    from urp_lab.simclient import stopped_state

    monkeypatch.setenv('URP_BRIDGE_FIX', option)
    assert bool(bridge_known_issues()) == expected_issue
    assert stopped_state()['known_issues'] == bridge_known_issues()
    if option == '0':
        assert '未修复' in bridge_note()
    elif option == 'invalid':
        assert '阻止仿真启动' in bridge_note()
    else:
        assert '源码关闭修复' in bridge_note()
