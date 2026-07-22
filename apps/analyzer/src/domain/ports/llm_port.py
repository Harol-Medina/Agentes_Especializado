"""Abstract LLM invocation port."""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class LLMPort(ABC):
    """Defines the contract for LLM text generation."""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Generate a complete response for the given *prompt*.

        Args:
            prompt: The user prompt / instruction.
            system_prompt: Optional system/role prompt to prepend.

        Returns:
            Generated text as a single string.
        """
        ...

    @abstractmethod
    async def stream(
        self, prompt: str, system_prompt: str = ""
    ) -> AsyncIterator[str]:
        """
        Stream a response token-by-token for the given *prompt*.

        Yields:
            Individual text tokens as they are produced by the model.
        """
        ...
