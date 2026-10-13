"""Backend switches must never silently relabel an existing graph."""
from dataclasses import replace
import json

import pytest

from memory.cache_compat import validate_cached_backend
from memory.jev_mem_config import JevMemConfig
from jev_mem.benchmarks.locomo import validate_reuse_memory


def saved_graph(path, config):
    (path / "vectors").mkdir()
    for name in ("graph.json", "keyword_index.json"):
        (path / name).write_text("{}")
    (path / "jev_mem_config.json").write_text(json.dumps(config.to_dict()))


@pytest.mark.parametrize("old,new", [("jev", "laya"), ("laya", "jev"),
                                      ("laya", "laya-mlx"), ("laya-mlx", "laya")])
def test_backend_changes_rejected_by_explicit_reuse_and_library(tmp_path, old, new):
    cfg = JevMemConfig(write_enabled=True, read_enabled=True, decision_backend=old)
    saved_graph(tmp_path, cfg)
    for validate in (validate_reuse_memory, validate_cached_backend):
        with pytest.raises(ValueError, match="decision_backend"):
            validate(tmp_path, replace(cfg, decision_backend=new))


@pytest.mark.parametrize("backend", ["laya", "laya-mlx"])
@pytest.mark.parametrize("change", [{"laya_model": "another/checkpoint"},
                                    {"laya_subfolder": "multilingual"}, {"jev_mock": True}])
def test_model_and_mock_changes_rejected(tmp_path, backend, change):
    cfg = JevMemConfig(decision_backend=backend, write_enabled=True, read_enabled=True)
    saved_graph(tmp_path, cfg)
    for validate in (validate_reuse_memory, validate_cached_backend):
        with pytest.raises(ValueError, match="construction settings"):
            validate(tmp_path, replace(cfg, **change))


def test_matching_backend_allows_retrieval_and_timeout_tuning(tmp_path):
    cfg = JevMemConfig(decision_backend="laya", write_enabled=True, read_enabled=True)
    saved_graph(tmp_path, cfg)
    current = replace(cfg, anchor_count=20, timeout_seconds=600, max_latency_seconds=1800)
    assert validate_reuse_memory(tmp_path, current) == tmp_path
    validate_cached_backend(tmp_path, current)


def test_historical_jev_cache_defaults_do_not_require_rebuild(tmp_path):
    cfg = JevMemConfig(write_enabled=True, read_enabled=True)
    saved_graph(tmp_path, cfg)
    saved = cfg.to_dict()
    for name in ("decision_backend", "laya_model", "laya_subfolder", "laya_device", "laya_batch_size"):
        saved.pop(name)
    (tmp_path / "jev_mem_config.json").unlink()
    (tmp_path / "sys1mem_config.json").write_text(json.dumps(saved))
    assert validate_reuse_memory(tmp_path, cfg) == tmp_path
    validate_cached_backend(tmp_path, cfg)
    with pytest.raises(ValueError, match="decision_backend"):
        validate_cached_backend(tmp_path, replace(cfg, decision_backend="laya"))


def test_library_rejects_wrong_backend_before_mutating_memory(tmp_path):
    from types import SimpleNamespace
    from memory.memory_builder import MemoryBuilder

    saved_graph(tmp_path, JevMemConfig(decision_backend="laya"))
    builder = MemoryBuilder.__new__(MemoryBuilder)
    builder.cache_dir = tmp_path
    builder.jev_config = JevMemConfig()
    builder.trg = SimpleNamespace(graph_db=SimpleNamespace(load=lambda *_: pytest.fail("Graph was loaded")))
    with pytest.raises(ValueError, match="decision_backend"):
        builder.load()
