"""Optimal policy for sigmoid."""

from __future__ import annotations

import numpy as np


def get_optimum(env, state):
    """Get the optimal action."""
    function_values = [
        env.instance.functions[i](env.c_step)
        for i in range(len(env.instance.functions))
    ]
    discrete = env.instance.discrete
    action = []
    for i, v in enumerate(function_values):
        if discrete[i]:
            v = np.linspace(0, 1, discrete[i])[int(v)]
        action.append(v)
    action_dict = {}
    for k in env.action_space:
        action_dict[k] = action.pop(0)
    return action_dict
