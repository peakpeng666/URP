"""Abstract LLM client interface.

The framework uses this protocol; concrete implementations can wrap the
OpenAI-compatible REST API, a local vLLM server, or a test mock.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


class LLMClient(Protocol):
    """Minimal LLM interface: take a prompt string, return a completion string."""

    def generate(self, prompt: str) -> str: ...


@dataclass(slots=True)
class CallableLLMClient:
    """Wrap any ``prompt -> completion`` callable as an :class:`LLMClient`.

    Useful for unit tests (pass a ``lambda`` / stub) and for swapping backends
    without subclassing.
    """

    callable_: Callable[[str], str]

    def generate(self, prompt: str) -> str:
        return self.callable_(prompt)
