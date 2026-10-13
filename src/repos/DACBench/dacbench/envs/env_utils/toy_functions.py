"""Toy functions for testing optimization algorithms."""

from __future__ import annotations

import ioh
import numpy as np
from numpy.polynomial import Polynomial as NP_Polynomial


class AbstractFunction:
    """Abstract function class."""

    def __init__(self, a, b) -> None:
        """Initialize the function."""
        super().__init__()
        self.a = a
        self.b = b

    def __call__(self, x):
        """Evaluate the function."""
        raise NotImplementedError

    def deriv(self, x, m=1):
        """Derivative of the function."""
        raise NotImplementedError

    @property
    def xmin(self):
        """Get the function minimum x location."""
        raise NotImplementedError

    @property
    def fmin(self):
        """Get the function minimum."""
        raise NotImplementedError

    @property
    def instance_description(self):
        """Get instance description."""
        raise NotImplementedError


class SigmiodFunction(AbstractFunction):
    """Sigmoid function."""

    def __call__(self, x):
        """Evaluate the function."""
        return 1 / (1 + np.exp(-self.a * (x - self.b)))

    def deriv(self, x, m=1):
        """Derivative of the function."""
        return self(x) * (1 - self(x))

    @property
    def xmin(self):
        """Get the function minimum x location."""
        raise ValueError("Sigmoid function has no clear x min")

    @property
    def fmin(self):
        """Get the function minimum."""
        return 0

    @property
    def instance_description(self):
        """Get instance description."""
        return (0, self.a, self.b)


class QuadraticFunction(AbstractFunction):
    """Quadratic function."""

    def __call__(self, x):
        """Evaluate the function."""
        return 0.5 * np.sum(self.a * (x - self.b) ** 2)

    def deriv(self, x, m=1):
        """Derivative of the function."""
        return np.sum(self.a * (x - self.b))

    @property
    def xmin(self):
        """Get the function minimum x location."""
        return np.sum(self.a * self.b) / np.sum(self.a)

    @property
    def fmin(self):
        """Get the function minimum."""
        return self(self.xmin)

    @property
    def instance_description(self):
        """Get instance description."""
        return (1, self.a, self.b)


class Polynomial(AbstractFunction):
    """Polynomial function."""

    def __call__(self, x):
        """Evaluate the function."""
        return NP_Polynomial(coef=[self.a, self.b])(x)

    def deriv(self, x, m=1):
        """Derivative of the function."""
        return NP_Polynomial([self.a, self.b]).deriv(m=m)(x)

    @property
    def xmin(self):
        """Get the function minimum x location."""
        return -self.b / (2 * self.a + 1e-10)

    @property
    def fmin(self):
        """Get the function minimum."""
        return self(self.xmin)

    @property
    def instance_description(self):
        """Get instance description."""
        return (2, self.a, self.b)


class LinearFunction(AbstractFunction):
    """Linear function."""

    def __call__(self, x):
        """Evaluate the function."""
        return self.a * x + self.b

    def deriv(self, x, m=1):
        """Derivative of the function."""
        return self.a

    @property
    def xmin(self):
        """Get the function minimum x location."""
        raise ValueError("Linear function has no minimum")

    @property
    def fmin(self):
        """Get the function minimum."""
        raise ValueError("Linear function has no minimum")

    @property
    def instance_description(self):
        """Get instance description."""
        return (3, self.a, self.b)


class ConstantFunction(AbstractFunction):
    """Constant function."""

    def __call__(self, x):
        """Evaluate the function."""
        return self.a

    def deriv(self, x, m=1):
        """Derivative of the function."""
        return 0

    @property
    def xmin(self):
        """Get the function minimum x location."""
        raise ValueError("Constant function has no clear x min")

    @property
    def fmin(self):
        """Get the function minimum."""
        return self.a

    @property
    def instance_description(self):
        """Get instance description."""
        return (4, self.a, self.a)


class LogarithmicFunction(AbstractFunction):
    """Logarithmic function."""

    def __call__(self, x):
        """Evaluate the function."""
        return self.a * np.log(x - self.b)

    def deriv(self, x, m=1):
        """Derivative of the function."""
        return self.a / (x - self.b)

    @property
    def xmin(self):
        """Get the function minimum x location."""
        raise ValueError("Logarithmic function has no minimum")

    @property
    def fmin(self):
        """Get the function minimum."""
        raise ValueError("Logarithmic function has no minimum")

    @property
    def instance_description(self):
        """Get instance description."""
        return (5, self.a, self.b)


class IOHFunction(AbstractFunction):
    """Wrapper for IOH function."""

    def __init__(self, function_name, dim, iid):
        """Initialize the IOH function."""
        self.function = ioh.get_problem(
            function_name,
            dimension=dim,
            instance=iid,
        )

    def __call__(self, x):
        """Evaluate the function."""
        return self.function(x)

    def deriv(self, x, m=1):
        """Derivative of the function."""
        raise NotImplementedError

    @property
    def xmin(self):
        """Get the function minimum x location."""
        return self.function.optimum.x

    @property
    def fmin(self):
        """Get the function minimum."""
        return self.function.optimum.y


def get_toy_function(identifier, a, b):
    """Get toy function by identifier."""
    if identifier in (0, "sigmoid"):
        return SigmiodFunction(a, b)
    elif identifier in (1, "quadratic"):  # noqa: RET505
        return QuadraticFunction(a, b)
    elif identifier in (2, "polynomial"):
        return Polynomial(a, b)
    elif identifier in (3, "linear"):
        return LinearFunction(a, b)
    elif identifier in (4, "constant"):
        return ConstantFunction(a, b)
    elif identifier in (5, "logarithmic"):
        return LogarithmicFunction(a, b)
    else:
        raise ValueError(f"Unknown function identifier {identifier}")
