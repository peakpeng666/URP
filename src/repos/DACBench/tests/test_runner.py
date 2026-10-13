from __future__ import annotations

import os
import tempfile
from pathlib import Path

import matplotlib
import numpy as np
from dacbench.abstract_agent import AbstractDACBenchAgent
from dacbench.runner import run_dacbench
from gymnasium import spaces

matplotlib.use("Agg")


class TestRunner:
    def test_loop(self):
        class DummyAgent(AbstractDACBenchAgent):
            def __init__(self, env):
                self.dict_action = False
                if isinstance(env.action_space, spaces.Discrete):
                    self.num_actions = 1
                elif isinstance(env.action_space, spaces.MultiDiscrete):
                    self.num_actions = len(env.action_space.nvec)
                elif isinstance(env.action_space, spaces.Dict):
                    self.num_actions = len(env.action_space.spaces)
                    self.dict_action = True
                    self.dict_keys = list(env.action_space.keys())
                else:
                    self.num_actions = len(env.action_space.high)

            def act(self, reward, state):
                action = np.ones(self.num_actions)
                if self.num_actions == 1:
                    action = 1
                if self.dict_action:
                    action = {key: action[i] for i, key in enumerate(self.dict_keys)}
                return action

            def train(self, reward, state):
                pass

            def end_episode(self, reward, state):
                pass

        def make(env):
            return DummyAgent(env)

        with tempfile.TemporaryDirectory() as tmp_dir:
            run_dacbench(
                tmp_dir,
                make,
                1,
                bench=["LubyBenchmark", "FunctionApproximationBenchmark"],
                seeds=[42],
            )
            path = Path(tmp_dir)
            assert os.stat(path / "LubyBenchmark") != 0
            assert os.stat(path / "FunctionApproximationBenchmark") != 0
