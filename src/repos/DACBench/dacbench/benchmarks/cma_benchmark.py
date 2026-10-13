"""CMA ES Benchmark."""

from __future__ import annotations

from pathlib import Path

import ConfigSpace as CS  # noqa: N817
import ConfigSpace.hyperparameters as CSH
import numpy as np
import pandas as pd

from dacbench.abstract_benchmark import AbstractBenchmark, objdict
from dacbench.envs import CMAESEnv, CMAESInstance
from dacbench.envs.env_utils.toy_functions import IOHFunction

DEFAULT_CFG_SPACE = CS.ConfigurationSpace()
ACTIVE = CSH.CategoricalHyperparameter(name="0_active", choices=[True, False])
ELITIST = CSH.CategoricalHyperparameter(name="1_elitist", choices=[True, False])
ORTHOGONAL = CSH.CategoricalHyperparameter(name="2_orthogonal", choices=[True, False])
SEQUENTIAL = CSH.CategoricalHyperparameter(name="3_sequential", choices=[True, False])
THRESHOLD_CONVERGENCE = CSH.CategoricalHyperparameter(
    name="4_threshold_convergence", choices=[True, False]
)
STEP_SIZE_ADAPTATION = CSH.CategoricalHyperparameter(
    name="5_step_size_adaptation",
    choices=["csa", "tpa", "msr", "xnes", "m-xnes", "lp-xnes", "psr"],
)
MIRRORED = CSH.CategoricalHyperparameter(
    name="6_mirrored", choices=["None", "mirrored", "mirrored pairwise"]
)
BASE_SAMPLER = CSH.CategoricalHyperparameter(
    name="7_base_sampler", choices=["gaussian", "sobol", "halton"]
)
WEIGHTS_OPTION = CSH.CategoricalHyperparameter(
    name="8_weights_option", choices=["default", "equal", "1/2^lambda"]
)
LOCAL_RESTART = CSH.CategoricalHyperparameter(
    name="90_local_restart", choices=["None", "IPOP", "BIPOP"]
)
BOUND_CORRECTION = CSH.CategoricalHyperparameter(
    name="91_bound_correction",
    choices=["None", "saturate", "unif_resample", "COTN", "toroidal", "mirror"],
)
STEP_SIZE = CS.Float(name="92_step_size", bounds=(0.0, 10.0))
DEFAULT_CFG_SPACE.add(ACTIVE)
DEFAULT_CFG_SPACE.add(ELITIST)
DEFAULT_CFG_SPACE.add(ORTHOGONAL)
DEFAULT_CFG_SPACE.add(SEQUENTIAL)
DEFAULT_CFG_SPACE.add(THRESHOLD_CONVERGENCE)
DEFAULT_CFG_SPACE.add(STEP_SIZE_ADAPTATION)
DEFAULT_CFG_SPACE.add(MIRRORED)
DEFAULT_CFG_SPACE.add(BASE_SAMPLER)
DEFAULT_CFG_SPACE.add(WEIGHTS_OPTION)
DEFAULT_CFG_SPACE.add(LOCAL_RESTART)
DEFAULT_CFG_SPACE.add(BOUND_CORRECTION)
DEFAULT_CFG_SPACE.add(STEP_SIZE)

FUNCTION_NAMES = {
    "BentCigar": 1,
    "BuecheRastrigin": 2,
    "DifferentPowers": 3,
    "Discus": 4,
    "Ellipsoid": 5,
    "EllipsoidRotated": 6,
    "Gallagher101": 7,
    "Gallagher21": 8,
    "GriewankRosenbrock": 9,
    "Katsuura": 10,
    "LinearSlope": 11,
    "LunacekBiRastrigin": 12,
    "Rastrigin": 13,
    "RastriginRotated": 14,
    "Rosenbrock": 15,
    "RosenbrockRotated": 16,
    "Schaffers10": 17,
    "Schaffers1000": 18,
    "Schwefel": 19,
    "SharpRidge": 20,
    "Sphere": 21,
    "StepEllipsoid": 22,
    "Weierstrass": 23,
}

INFO = {
    "identifier": "CMA-ES",
    "name": "Online Selection of CMA-ES Variants and step-size control",
    "reward": "Negative best function value",
    "state_description": [
        "Generation Size",
        "Sigma",
        "Remaining Budget",
        "Function ID",
        "Instance ID",
    ],
}


CMAES_DEFAULTS = objdict(
    {
        "config_space": DEFAULT_CFG_SPACE,
        "observation_space_class": "Box",
        "observation_space_args": [-np.inf * np.ones(5), np.inf * np.ones(5)],
        "observation_space_type": np.float32,
        "reward_range": (-(10**12), 0),
        "budget": 100,
        "cutoff": 1e6,
        "seed": 0,
        "multi_agent": False,
        "instance_set_path": "../instance_sets/cma/cma_bbob_dim10_train.csv",
        "test_set_path": "../instance_sets/cma/cma_bbob_dim10_test.csv",
        "benchmark_info": INFO,
    }
)


class CMAESBenchmark(AbstractBenchmark):
    """Benchmark for controlling the step size of CMA-ES on BBOB functions."""

    def __init__(self, config_path: str | None = None, config=None):
        """Initialize CMA ES Benchmark.

        Parameters
        -------
        config_path : str
            Path to config file (optional)
        """
        super().__init__(config_path, config)
        self.config = objdict(CMAES_DEFAULTS.copy(), **(self.config or {}))

    def get_environment(self):
        """Return SGDEnv env with current configuration.

        Returns:
        -------
        SGDEnv
            SGD environment
        """
        if "instance_set" not in self.config:
            self.read_instance_set()

        # Read test set if path is specified
        if "test_set" not in self.config and "test_set_path" in self.config:
            self.read_instance_set(test=True)

        env = CMAESEnv(self.config)

        for func in self.wrap_funcs:
            env = func(env)
        return env

    def read_instance_set(self, test=False):
        """Read path of instances from config into list."""
        if test:
            relative_path = Path(__file__).resolve().parent / self.config.test_set_path
            absolute_path = Path(self.config.test_set_path)
            dacbench_path = (
                Path(__file__).resolve().parent
                / "../instance_sets/cma"
                / self.config.test_set_path
            )
            keyword = "test_set"
        else:
            relative_path = (
                Path(__file__).resolve().parent / self.config.instance_set_path
            )
            absolute_path = Path(self.config.instance_set_path)
            (
                Path(__file__).resolve().parent
                / "../instance_sets/toysgd"
                / self.config.instance_set_path
            )
            keyword = "instance_set"

        if absolute_path.exists():
            path = absolute_path
        elif relative_path.exists():
            path = relative_path
        elif dacbench_path.is_file():
            path = dacbench_path
        else:
            raise FileNotFoundError(
                f"Instance set file not found at {absolute_path} or {relative_path}"
            )

        self.config[keyword] = {}
        instance_csv = pd.read_csv(path)
        for i, row in instance_csv.iterrows():
            self.config[keyword][i] = CMAESInstance(
                IOHFunction(
                    function_name=row["func_name"], dim=row["dim"], iid=row["iid"]
                ),
                dim=row["dim"],
                fid=FUNCTION_NAMES[row["func_name"]],
                iid=row["iid"],
                active=row["active"],
                elitist=row["elitist"],
                orthogonal=row["orthogonal"],
                sequential=row["sequential"],
                threshold_convergence=row["threshold_convergence"],
                step_size_adaptation=row["step_size_adaptation"],
                mirrored=row["mirrored"],
                base_sampler=row["base_sampler"],
                weights_option=row["weights_option"],
                local_restart=row["local_restart"],
                bound_correction=row["bound_correction"],
            )
