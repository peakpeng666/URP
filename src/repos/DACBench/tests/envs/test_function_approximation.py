from __future__ import annotations

import unittest
from unittest import mock

import numpy as np
from dacbench import AbstractEnv
from dacbench.benchmarks.function_approximation_benchmark import FUNCTION_APPROXIMATION_DEFAULTS
from dacbench.envs import FunctionApproximationEnv, FunctionApproximationInstance
from dacbench.envs.env_utils.toy_functions import get_toy_function


class TestFunctionApproximationEnv(unittest.TestCase):
    def make_env(self):
        config = FUNCTION_APPROXIMATION_DEFAULTS.copy()
        functions = []
        for _ in range(2):
            functions.append(get_toy_function("linear", 2, 1))

        config["instance_set"] = {20: FunctionApproximationInstance(
                functions=functions,
                dimension_importances=[0.5, 0.5],
                discrete=[3, False],
                omit_instance_type=True,
            )}
        return FunctionApproximationEnv(config)

    def test_setup(self):
        env = self.make_env()
        assert issubclass(type(env), AbstractEnv)
        assert env.np_random is not None
        assert isinstance(env.instance, FunctionApproximationInstance)
        assert len(env.instance.functions) == 2
        assert env.instance.functions[0].__class__.__name__ == "LinearFunction"
        assert env.instance.functions[1].__class__.__name__ == "LinearFunction"
        assert env.instance.dimension_importances == [0.5, 0.5]

    def test_reset(self):
        env = self.make_env()
        state, info = env.reset()
        assert issubclass(type(info), dict)
        assert env.instance.functions[0].a == 2
        assert env.instance.functions[1].a == 2
        assert env.instance.functions[0].b == 1
        assert env.instance.functions[1].b == 1
        assert state[0] == FUNCTION_APPROXIMATION_DEFAULTS["cutoff"]
        assert state[1] == env.instance.functions[0].a
        assert state[2] == env.instance.functions[0].b
        assert state[3] == env.instance.functions[1].a
        assert state[4] == env.instance.functions[1].b
        assert np.array_equal(state[5:], -1 * np.ones(2))

    def test_step(self):
        env = self.make_env()
        env.reset()
        state, reward, terminated, truncated, meta = env.step({"dim_1": 1, "dim_2": 1})
        assert reward >= env.reward_range[0]
        assert reward <= env.reward_range[1]
        assert int(state[0]) == FUNCTION_APPROXIMATION_DEFAULTS["cutoff"]-1
        assert state[1] == env.instance.functions[0].a
        assert state[2] == env.instance.functions[0].b
        assert state[3] == env.instance.functions[1].a
        assert state[4] == env.instance.functions[1].b
        assert len(state) == 7
        assert not terminated
        assert not truncated
        assert len(meta.keys()) == 2

    def test_importances(self):
        env = self.make_env()
        env.reset()
        env.step({"dim_1": 1, "dim_2": 1})
        assert all([env.weighted_distances[i] == (np.array(env.distances) * np.array(env.instance.dimension_importances))[i] for i in range(len(env.distances))])
        env.instance.dimension_importances = [5, 1]
        env.step({"dim_1": 1, "dim_2": 1})
        assert all([env.weighted_distances[i] == (np.array(env.distances) * np.array(env.instance.dimension_importances))[i] for i in range(len(env.distances))])

    def test_close(self):
        env = self.make_env()
        assert env.close()