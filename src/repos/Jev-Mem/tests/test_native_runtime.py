"""Native crashes must be checked in a fresh process, not pytest's runtime."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("platform, requested, expected", [
    ("darwin", None, "cpu"), ("darwin", "auto", "cpu"),
    ("linux", None, None), ("linux", "auto", None),
    ("darwin", "cpu", "cpu"), ("linux", "cuda:1", "cuda:1"),
])
def test_local_model_device_policy(monkeypatch, platform, requested, expected):
    from memory import local_device
    monkeypatch.setattr(local_device, "sys", type("Platform", (), {"platform": platform}))
    assert local_device.local_model_device(requested) == expected


def test_local_embeddings_use_cpu_on_macos(monkeypatch):
    from memory import local_device, vector_db
    monkeypatch.setattr(local_device, "sys", type("Platform", (), {"platform": "darwin"}))
    devices = []

    class Encoder:
        def __init__(self, name, device):
            devices.append(device)

        def get_sentence_embedding_dimension(self):
            return 384

    monkeypatch.setattr(vector_db, "SentenceTransformer", Encoder)
    monkeypatch.setattr(vector_db, "SENTENCE_TRANSFORMER_AVAILABLE", True)
    assert vector_db.VectorEncoder(use_openai=False).dimension == 384
    assert devices == ["cpu"]


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS OpenMP compatibility")
def test_native_thread_defaults_precede_imports():
    env = dict(os.environ)
    for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        env.pop(key, None)
    result = subprocess.run([sys.executable, "-c", """
import memory
import os
import sys
assert os.environ['OMP_NUM_THREADS'] == '1'
assert os.environ['MKL_NUM_THREADS'] == '1'
assert 'torch' not in sys.modules and 'faiss' not in sys.modules
# Follow the benchmark import order, including sklearn and FAISS.
from memory.memory_builder import MemoryBuilder
import faiss
import torch
import numpy as np
assert torch.get_num_threads() == 1
assert faiss.omp_get_max_threads() == 1
from concurrent.futures import ThreadPoolExecutor
def work(_):
    for _ in range(5):
        weights = torch.nn.Linear(1024, 1024)
        assert torch.isfinite(weights(torch.ones(16, 1024))).all()
        index = faiss.IndexFlatL2(32)
        vectors = np.ones((100, 32), dtype=np.float32)
        index.add(vectors)
        assert index.search(vectors[:1], 1)[0][0, 0] == 0
with ThreadPoolExecutor(max_workers=3) as pool:
    list(pool.map(work, range(3)))
print('native runtime exited cleanly')
"""], cwd=ROOT, env=env, text=True, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert "native runtime exited cleanly" in result.stdout
    assert "leaked semaphore" not in result.stderr


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS OpenMP compatibility")
def test_explicit_thread_configuration_is_preserved():
    env = dict(os.environ, OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
    result = subprocess.run([sys.executable, "-c", """
import memory
import os
assert os.environ['OMP_NUM_THREADS'] == '2'
assert os.environ['MKL_NUM_THREADS'] == '2'
"""], cwd=ROOT, env=env, text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
