from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return the model response as plain text."""


class MissingLLMClient:
    """Placeholder client so the integration point is explicit."""

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError(
            "No LLM client is configured. Replace MissingLLMClient with your provider integration."
        )
