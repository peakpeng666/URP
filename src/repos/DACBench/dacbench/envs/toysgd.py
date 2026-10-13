"""Environment for sgd with toy functions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from dacbench import AbstractMADACEnv

if TYPE_CHECKING:
    from dacbench.envs.env_utils.toy_functions import AbstractFunction


@dataclass
class ToySGDInstance:
    """Toy SGD Instance."""

    function: AbstractFunction


class ToySGDEnv(AbstractMADACEnv):
    """Optimize toy functions with SGD + Momentum.

    Action: [log_learning_rate, log_momentum] (log base 10)
    State: Dict with entries remaining_budget, gradient, learning_rate, momentum
    Reward: negative log regret of current and true function value

    An instance can look as follows:
    ID                                                  0
    family                                     polynomial
    order                                               2
    low                                                -2
    high                                                2
    coefficients    [ 1.40501053 -0.59899755  1.43337392]

    """

    def __init__(self, config):
        """Init env."""
        super().__init__(config)

        if config["batch_size"]:
            self.batch_size = config["batch_size"]
        self.velocity = 0
        self.gradient = np.zeros(self.batch_size)
        self.history = []
        self.n_dim = None
        self.objective_function = None
        self.x_cur = None
        self.f_cur = None
        self.momentum = 0
        self.learning_rate = None
        self.rng = np.random.default_rng(self.initial_seed)

        self.get_reward = config.get("reward_function", self.get_default_reward)
        self.get_state = config.get("state_method", self.get_default_state)

    def step(
        self, action: float | tuple[float, float]
    ) -> tuple[dict[str, float], float, bool, dict]:
        """Take one step with SGD.

        Parameters
        ----------
        action: Tuple[float, Tuple[float, float]]
            If scalar, action = (log_learning_rate)
            If tuple, action = (log_learning_rate, log_momentum)

        Returns:
        -------
        Tuple[Dict[str, float], float, bool, Dict]

            - state : Dict[str, float]
                State with entries:
                "remaining_budget", "gradient", "learning_rate", "momentum"
            - reward : float
            - terminated : bool
            - truncated : bool
            - info : Dict

        """
        truncated = super().step_()
        info = {}

        # parse action
        if np.isscalar(action):
            log_learning_rate = action
        elif len(action) == 2:
            log_learning_rate, log_momentum = action
            self.momentum = 10**log_momentum
        else:
            raise ValueError
        self.learning_rate = 10**log_learning_rate

        # SGD + Momentum update
        self.velocity = (
            self.momentum * self.velocity + self.learning_rate * self.gradient
        )
        self.x_cur -= self.velocity
        self.gradient = self.objective_function.deriv(self.x_cur)

        # current function value
        self.f_cur = self.objective_function(self.x_cur)
        self.history.append(self.x_cur)

        return self.get_state(self), self.get_reward(self), False, truncated, info

    def reset(self, seed=None, options=None):
        """Reset environment.

        Parameters
        ----------
        seed : int
            seed
        options : dict
            options dict (not used)

        Returns:
        -------
        np.array
            Environment state
        dict
            Meta-info

        """
        if options is None:
            options = {}
        super().reset_(seed)

        self.velocity = 0
        self.gradient = np.zeros(self.batch_size)
        self.history = []

        self.objective_function = self.instance.function
        self.x_cur = self.rng.uniform(-5, 5, size=self.batch_size)
        self.f_cur = self.objective_function(self.x_cur)

        self.momentum = 0
        self.learning_rate = 0

        return self.get_state(self), {}

    def get_default_reward(self, _):
        """Default reward: negative log regret."""
        log_regret = np.log10(np.abs(self.objective_function.fmin - self.f_cur))
        return -np.mean(log_regret)

    def get_default_state(self, _):
        """Default state: remaining_budget, gradient, learning_rate, momentum."""
        # TODO: add instance description?
        remaining_budget = self.n_steps - self.c_step
        return {
            "remaining_budget": remaining_budget,
            "gradient": self.gradient,
            "learning_rate": self.learning_rate,
            "momentum": self.momentum,
        }

    def render(self, **kwargs):
        """Render progress."""
        import matplotlib.pyplot as plt

        history = np.array(self.history).flatten()
        X = np.linspace(1.05 * np.amin(history), 1.05 * np.amax(history), 100)
        Y = self.objective_function(X)
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot(X, Y, label="True")
        ax.plot(
            history,
            self.objective_function(history),
            marker="x",
            color="black",
            label="Observed",
        )
        ax.plot(
            self.x_cur,
            self.objective_function(self.x_cur),
            marker="x",
            color="red",
            label="Current Optimum",
        )
        ax.legend()
        ax.set_xlabel("x")
        ax.set_ylabel("y")
        ax.set_title("instance: " + str(self.instance["coefficients"]))
        plt.show()

    def close(self):
        """Close env."""
