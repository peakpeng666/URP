from __future__ import annotations

import unittest

import numpy as np
import pytest
from dacbench.benchmarks import LubyBenchmark
from dacbench.envs import LubyInstance
from dacbench.wrappers import InstanceSamplingWrapper
from sklearn.metrics import mutual_info_score


class TestInstanceSamplingWrapper(unittest.TestCase):
    def test_init(self):
        bench = LubyBenchmark()
        bench.config.instance_update_func = "none"
        env = bench.get_environment()

        with pytest.raises(Exception):
            wrapped = InstanceSamplingWrapper(env)

        def sample():
            return [0, 0]

        wrapped = InstanceSamplingWrapper(env, sampling_function=sample)
        assert wrapped.sampling_function is not None

    def test_reset(self):
        bench = LubyBenchmark()
        bench.config.instance_update_func = "none"
        env = bench.get_environment()

        def sample():
            return LubyInstance(4, 4)

        wrapped = InstanceSamplingWrapper(env, sampling_function=sample)

        assert not np.array_equal(wrapped.instance, sample())
        assert not np.array_equal(next(iter(wrapped.instance_set.values())), sample())

        wrapped.reset()
        assert np.array_equal(wrapped.instance, sample())

    def test_fit(self):
        bench = LubyBenchmark()
        bench.config.instance_update_func = "none"
        bench.config.instance_set_path = "../instance_sets/luby/luby_train.csv"
        bench.read_instance_set()
        instances = bench.config.instance_set
        env = bench.get_environment()

        wrapped = InstanceSamplingWrapper(env, instances=instances)
        samples = []
        for _ in range(100):
            samples.append(wrapped.sampling_function())

        starts_instance_set = [instances[i].start_shift for i in instances]
        starts_samples = [samples[i][0] for i in range(len(samples))]
        stickies_instance_set = [instances[i].sticky_shift for i in instances]
        stickies_samples = [samples[i][1] for i in range(len(samples))]

        mi1 = mutual_info_score(starts_instance_set, starts_samples)
        mi2 = mutual_info_score(stickies_instance_set, stickies_samples)

        assert mi1 > 0.99
        assert mi1 != 1
        assert mi2 > 0.99
        assert mi2 != 1
