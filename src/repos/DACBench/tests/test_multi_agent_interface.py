from __future__ import annotations

import numpy as np
from dacbench.benchmarks import FunctionApproximationBenchmark, ToySGDBenchmark
from dacbench.envs import FunctionApproximationEnv, ToySGDEnv


class TestMultiAgentInterface:
    def test_make_env(self):
        bench = FunctionApproximationBenchmark()
        bench.config["multi_agent"] = True
        env = bench.get_environment()
        assert issubclass(type(env), FunctionApproximationEnv)

        bench = ToySGDBenchmark()
        bench.config["multi_agent"] = True
        env = bench.get_environment()
        assert issubclass(type(env), ToySGDEnv)

    def test_empty_reset_step(self):
        bench = FunctionApproximationBenchmark()
        bench.config["multi_agent"] = True
        env = bench.get_environment()
        out = env.reset()
        assert out is None
        env.register_agent("value_dim_1")
        out = env.step({"value_dim_1": 0})
        assert out is None

    def test_last(self):
        bench = ToySGDBenchmark()
        bench.config["multi_agent"] = True
        env = bench.get_environment()
        env.reset()
        state, reward, terminated, truncated, info = env.last()
        assert state is not None
        assert reward is None
        assert info is not None
        assert not terminated
        assert not truncated
        env.register_agent(max(env.possible_agents))
        env.step(0)
        _, reward, _, _, info = env.last()
        assert reward is not None
        assert info is not None

    def test_agent_registration(self):
        bench = FunctionApproximationBenchmark()
        bench.config["multi_agent"] = True
        env = bench.get_environment()
        env.reset()
        state, _, _, _, _ = env.last()
        env.register_agent("value_dim_1")
        env.register_agent("value_dim_2")
        assert len(env.agents) == 2
        assert 0 in env.agents
        assert max(env.possible_agents) in env.agents
        assert env.current_agent == 0
        env.step({"value_dim_1": 0})
        state2, _, _, _, _ = env.last()
        assert np.array_equal(state, state2)
        assert env.current_agent == max(env.possible_agents)
        env.step({"value_dim_2": 1})
        state3, _, _, _, _ = env.last()
        assert not np.array_equal(state, state3)
        env.remove_agent(0)
        assert len(env.agents) == 1
        assert 0 not in env.agents
        env.register_agent("value_dim_1")
        assert len(env.agents) == 2
        assert 0 in env.agents
