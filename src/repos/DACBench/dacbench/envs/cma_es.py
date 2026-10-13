"""CMA ES Environment."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from modcma import ModularCMAES, Parameters

from dacbench import AbstractMADACEnv

if TYPE_CHECKING:
    from env_utils.toy_functions import AbstractFunction

BINARIES = {True: 1, False: 0}
STEP_SIZE_ADAPTATION = {
    "csa": 0,
    "tpa": 1,
    "msr": 2,
    "xnes": 3,
    "m-xnes": 4,
    "lp-xnes": 5,
    "psr": 6,
}
MIRRORED = {"None": 0, "mirrored": 1, "mirrored pairwise": 2}
BASE_SAMPLER = {"gaussian": 0, "sobol": 1, "halton": 2}
WEIGHTS_OPTION = {"default": 0, "equal": 1, "1/2^lambda": 2}
LOCAL_RESTART = {"None": 0, "IPOP": 1, "BIPOP": 2}
BOUND_CORRECTION = {
    "None": 0,
    "saturate": 1,
    "unif_resample": 2,
    "COTN": 3,
    "toroidal": 4,
    "mirror": 5,
}


@dataclass
class CMAESInstance:
    """CMA-ES Instance."""

    target_function: AbstractFunction
    dim: int
    fid: int
    iid: int
    active: bool
    elitist: bool
    orthogonal: bool
    sequential: bool
    threshold_convergence: bool
    step_size_adaptation: str
    mirrored: str
    base_sampler: str
    weights_option: str
    local_restart: str
    bound_correction: str


class CMAESEnv(AbstractMADACEnv):
    """The CMA ES environment controlles the step size on BBOB functions."""

    def __init__(self, config):
        """Initialize the environment."""
        super().__init__(config)

        self.es = None
        self.budget = config.budget
        self.total_budget = self.budget

        if not config.get("normalize_reward", False):
            self.get_reward = config.get("reward_function", self.get_default_reward)
        else:
            self.get_reward = config.get("reward_function", self.get_normalized_reward)

        self.get_state = config.get("state_method", self.get_default_state)

    def _uniform_name(self, name):
        # Convert name of parameters uniformly to lowercase,
        # separated with _ and no numbers
        pattern = r"^\d+_"

        # Use re.sub to remove the leading number and underscore
        result = re.sub(pattern, "", name)
        return result.lower()

    def reset(self, seed=None, options=None):
        """Reset the environment."""
        if options is None:
            options = {}
        super().reset_(seed)
        self.representation_dict = {
            "active": BINARIES[self.instance.active],
            "elitist": BINARIES[self.instance.elitist],
            "orthogonal": BINARIES[self.instance.orthogonal],
            "sequential": BINARIES[self.instance.sequential],
            "threshold_convergence": BINARIES[self.instance.threshold_convergence],
            "step_size_adaptation": STEP_SIZE_ADAPTATION[
                self.instance.step_size_adaptation
            ],
            "mirrored": MIRRORED[self.instance.mirrored],
            "base_sampler": BASE_SAMPLER[self.instance.base_sampler],
            "weights_option": WEIGHTS_OPTION[self.instance.weights_option],
            "local_restart": LOCAL_RESTART[self.instance.local_restart],
            "bound_correction": BOUND_CORRECTION[self.instance.bound_correction],
        }
        self.objective = self.instance.target_function
        self.es = ModularCMAES(
            self.objective,
            parameters=Parameters.from_config_array(
                self.instance.dim,
                np.array(list(self.representation_dict.values())).astype(int),
            ),
        )
        return self.get_state(self), {}

    def step(self, action):
        """Make one step of the environment."""
        truncated = super().step_()

        # Get all action values and uniform names
        complete_action = {}
        if isinstance(action, dict):
            for hp in action:
                n_name = self._uniform_name(hp)
                if n_name == "step_size":
                    # Step size is set separately
                    self.es.parameters.sigma = action[hp][0]
                else:
                    # Save parameter values from actions
                    complete_action[n_name] = action[hp]

            # Complete the given action with defaults
            for default in self.representation_dict:
                if default == "step_size":
                    continue
                if default not in complete_action:
                    complete_action[default] = self.representation_dict[default]
            complete_action = complete_action.values()
        else:
            raise ValueError("Action must be a Dict")

        new_parameters = Parameters.from_config_array(
            self.instance.dim, complete_action
        )
        self.es.parameters.update(
            {m: getattr(new_parameters, m) for m in Parameters.__modules__}
        )

        terminated = not self.es.step()
        return self.get_state(self), self.get_reward(self), terminated, truncated, {}

    def close(self):
        """Closes the environment."""
        return True

    def get_default_reward(self, *_):
        """The default reward function.

        Args:
            _ (_type_): Empty parameter, which can be used when overriding

        Returns:
            float: The calculated reward
        """
        return max(
            self.reward_range[0], min(self.reward_range[1], -self.es.parameters.fopt)
        )

    def get_normalized_reward(self, *_):
        """Normalize each reward within domain bounds.

        Args:
            _ (_type_): Empty parameter, which can be used when overriding

        Returns:
            float: The calculated reward
        """
        obj_min, obj_max = self.objective.fmin, 0
        current_reward = -self.es.parameters.fopt
        norm_reward = (current_reward - obj_min) / (obj_max - obj_min)
        return max(self.reward_range[0], min(self.reward_range[1], norm_reward))

    def get_default_state(self, *_):
        """Default state function.

        Args:
            _ (_type_): Empty parameter, which can be used when overriding

        Returns:
            dict: The current state
        """
        return np.array(
            [
                self.es.parameters.lambda_,
                self.es.parameters.sigma,
                self.budget - self.es.parameters.used_budget,
                self.instance.fid,
                self.instance.iid,
            ]
        )

    def render(self, mode="human"):
        """Render progress."""
        raise NotImplementedError("CMA-ES does not support rendering at this point")
