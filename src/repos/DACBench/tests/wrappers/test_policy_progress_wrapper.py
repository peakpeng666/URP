from __future__ import annotations

import unittest
from unittest import mock

import numpy as np
from dacbench.benchmarks import FunctionApproximationBenchmark
from dacbench.wrappers import PolicyProgressWrapper


def _sig(x, scaling, inflection):
    return 1 / (1 + np.exp(-scaling * (x - inflection)))


def compute_optimal_sigmoid(instance):
    sig_values = []
    for i in range(10):
        func_values = [f(i) for f in instance.functions]
        sig_values.append(func_values)
    return sig_values


class TestPolicyProgressWrapper(unittest.TestCase):
    def test_init(self):
        bench = FunctionApproximationBenchmark()
        env = bench.get_environment()
        wrapped = PolicyProgressWrapper(env, compute_optimal_sigmoid)
        assert len(wrapped.policy_progress) == 0
        assert len(wrapped.episode) == 0
        assert wrapped.compute_optimal is not None

    def test_step(self):
        bench = FunctionApproximationBenchmark()
        bench.config.omit_instance_type = True
        env = bench.get_environment()
        wrapped = PolicyProgressWrapper(env, compute_optimal_sigmoid)

        wrapped.reset()
        action = env.action_space.sample()
        _, _, terminated, truncated, _ = wrapped.step(action)
        assert len(wrapped.episode) == 1
        while not (terminated or truncated):
            _, _, terminated, truncated, _ = wrapped.step(action)
        assert len(wrapped.episode) == 0
        assert len(wrapped.policy_progress) == 1

    @mock.patch("dacbench.wrappers.policy_progress_wrapper.plt")
    def test_render(self, mock_plt):
        bench = FunctionApproximationBenchmark()
        env = bench.get_environment()
        env = PolicyProgressWrapper(env, compute_optimal_sigmoid)
        for _ in range(2):
            terminated, truncated = False, False
            env.reset()
            while not (terminated or truncated):
                _, _, terminated, truncated, _ = env.step(env.action_space.sample())
        env.render_policy_progress()
        assert mock_plt.show.called
