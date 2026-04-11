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


class OpenAIResponsesClient:
    """OpenAI Responses API client configured for Codex-oriented models."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-5.3-codex",
        reasoning_effort: str = "medium",
        base_url: str | None = None,
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

        self._client = OpenAI(**client_kwargs)
        self.model = model
        self.reasoning_effort = reasoning_effort

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        response = self._client.responses.create(
            model=self.model,
            reasoning={"effort": self.reasoning_effort},
            instructions=system_prompt,
            input=user_prompt,
        )
        return response.output_text
