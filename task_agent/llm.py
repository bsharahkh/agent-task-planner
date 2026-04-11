from __future__ import annotations

import logging
from typing import Protocol

from task_agent.utils import retry

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        """Return the model response as plain text."""


class MissingLLMClient:
    """Placeholder client so the integration point is explicit."""

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError(
            "No LLM client is configured. Replace MissingLLMClient with your provider integration."
        )


class OpenAIResponsesClient:
    """OpenAI Responses API client configured for Codex-oriented models."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-5.3-codex",
        reasoning_effort: str = "medium",
        base_url: str | None = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.5,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required to use the OpenAI Codex client.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "The `openai` package is required. Install dependencies with `pip install -e .`."
            ) from exc

        client_kwargs: dict[str, str] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url

        self._client = OpenAI(**client_kwargs, timeout=timeout_seconds, max_retries=0)
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        def _request() -> str:
            response = self._client.responses.create(
                model=self.model,
                reasoning={"effort": self.reasoning_effort},
                instructions=system_prompt,
                input=user_prompt,
            )
            return response.output_text

        logger.debug("Requesting OpenAI response with model=%s", self.model)
        response = retry(
            _request,
            attempts=self.max_retries,
            delay_seconds=self.retry_delay_seconds,
        )
        return response
