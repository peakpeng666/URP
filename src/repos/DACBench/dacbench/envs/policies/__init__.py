from dacbench.envs.policies.csa_cma import csa
from dacbench.envs.policies.optimal_fd import get_optimum as optimal_fd
from dacbench.envs.policies.optimal_function_approximation import (
    get_optimum as optimal_function_approximation,
)
from dacbench.envs.policies.optimal_luby import get_optimum as optimal_luby
from dacbench.envs.policies.sgd_ca import CosineAnnealingAgent

OPTIMAL_POLICIES = {
    "LubyBenchmark": optimal_luby,
    "FunctionApproximationBenchmark": optimal_function_approximation,
    "FastDownwardBenchmark": optimal_fd,
}

NON_OPTIMAL_POLICIES = {"CMAESBenchmark": csa, "SGDBenchmark": CosineAnnealingAgent}

ALL_POLICIES = {**OPTIMAL_POLICIES, **NON_OPTIMAL_POLICIES}
