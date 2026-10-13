"""Benchmark for SGD."""

from __future__ import annotations

import math
from pathlib import Path

import ConfigSpace as CS  # noqa: N817
import numpy as np
import pandas as pd
from gymnasium import spaces
from torch import nn

from dacbench.abstract_benchmark import AbstractBenchmark, objdict
from dacbench.envs import SGDEnv, SGDInstance
from dacbench.envs.env_utils import sgd_utils

DEFAULT_CFG_SPACE = CS.ConfigurationSpace()
LR = CS.Float(name="learning_rate", bounds=(0.0, 0.05))
# Value used for momentum like adaptation, as adam optimizer has no real momentum;
# "beta1" is changed
MOMENTUM = CS.Float(
    name="momentum", bounds=(0.0, 1.0)
)  # ! Only used, when "use_momentum" var in config true
DEFAULT_CFG_SPACE.add(LR)
DEFAULT_CFG_SPACE.add(MOMENTUM)


def __default_loss_function(**kwargs):
    return nn.NLLLoss(reduction="none", **kwargs)


INFO = {
    "identifier": "LR",
    "name": "Learning Rate Adaption for Neural Networks",
    "reward": "Negative Log Differential Validation Loss",
    "state_description": [
        "Step",
        "Loss",
        "Validation Loss",
        "Crashed",
    ],
    "action_description": ["Learning Rate", "Momentum"],
}


SGD_DEFAULTS = objdict(
    {
        "config_space": DEFAULT_CFG_SPACE,
        "observation_space_class": "Dict",
        "observation_space_type": None,
        "observation_space_args": [
            {
                "step": spaces.Box(low=0, high=np.inf, shape=(1,)),
                "loss": spaces.Box(0, np.inf, shape=(1,)),
                "validationLoss": spaces.Box(low=0, high=np.inf, shape=(1,)),
                "crashed": spaces.Discrete(1),
            }
        ],
        "reward_range": [-(10**9), (10**9)],
        "device": "cpu",
        "use_instance_generator": False,
        "cutoff": 1e2,
        "loss_function": __default_loss_function,
        "loss_function_kwargs": {},
        # "reward_function":,    # Can be set, to replace the default function
        # "state_method":,       # Can be set, to replace the default function
        "use_momentum": False,
        "seed": 0,
        "crash_penalty": -100.0,
        "multi_agent": False,
        "instance_set_path": "sgd_cifar10_variations_train.csv",
        "benchmark_info": INFO,
        "epoch_mode": True,
        "local_model_path": False,
        "dataset_config": None,
    }
)


class SGDBenchmark(AbstractBenchmark):
    """Benchmark with default configuration & relevant functions for SGD."""

    def __init__(self, config_path=None, config=None):
        """Initialize SGD Benchmark.

        Parameters
        -------
        config_path : str
            Path to config file (optional)
        """
        super().__init__(config_path, config)
        if not self.config:
            self.config = objdict(SGD_DEFAULTS.copy())

        for key in SGD_DEFAULTS:
            if key not in self.config:
                self.config[key] = SGD_DEFAULTS[key]

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

        env = SGDEnv(self.config)
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
                / "../instance_sets/sgd"
                / self.config.test_set_path
            )
            keyword = "test_set"
        else:
            relative_path = (
                Path(__file__).resolve().parent / self.config.instance_set_path
            )
            absolute_path = Path(self.config.instance_set_path)
            dacbench_path = (
                Path(__file__).resolve().parent
                / "../instance_sets/sgd"
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

        instance_set = pd.read_csv(path)
        for index, row in instance_set.iterrows():
            if "_" in row["dataset"]:
                dataset_info = row["dataset"].split("_")
                dataset_name = dataset_info[0]
            else:
                dataset_name = row["dataset"]

            model_constructor = sgd_utils.get_model_constructor(
                row["model_type"],
                row["model_kwargs"].split("-"),
                self.config.local_model_path,
            )

            optimizer_params = row["optimizer_params"]
            if row["optimizer_params"] is None or math.isnan(row["optimizer_params"]):
                optimizer_params = {}

            instance = SGDInstance(
                model=model_constructor,
                optimizer_type=row["optimizer"],
                optimizer_params=optimizer_params,
                dataset_path=Path(__file__).resolve().parent,
                dataset_name=dataset_name,
                batch_size=row["batch_size"],
                fraction_of_dataset=row["fraction_of_dataset"],
                train_validation_ratio=row["train_validation_ratio"],
                seed=int(row["seed"]),
            )
            self.config[keyword][index] = instance

    def get_benchmark(self, instance_set_path=None, seed=0):
        """Get benchmark from the LTO paper.

        Parameters
        -------
        seed : int
            Environment seed

        Returns:
        -------
        env : SGDEnv
            SGD environment
        """
        self.config = objdict(SGD_DEFAULTS.copy())
        if instance_set_path is not None:
            self.config["instance_set_path"] = instance_set_path
        self.config.seed = seed
        self.read_instance_set()
        return SGDEnv(self.config)
