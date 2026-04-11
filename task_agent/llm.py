from __future__ import annotations

import logging
import platform
import subprocess
import tempfile
from pathlib import Path
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
            "No executor is configured. Replace MissingLLMClient with your provider integration."
        )


class CodexCLIClient:
    """Execute prompts through the local Codex CLI in non-interactive mode."""

    def __init__(
        self,
        *,
        workspace: str,
        model: str = "",
        profile: str = "",
        sandbox: str = "read-only",
        timeout_seconds: float = 120.0,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.5,
    ) -> None:
        self.workspace = workspace
        self.model = model.strip()
        self.profile = profile.strip()
        self.sandbox = sandbox.strip() or "read-only"
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    def verify_installation(self) -> None:
        command = self._base_command() + ["--version"]
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=min(self.timeout_seconds, 15),
            cwd=self.workspace,
        )
        if completed.returncode != 0:
            details = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(f"Codex CLI is not available: {details or 'unknown error'}")

    def complete(self, *, system_prompt: str, user_prompt: str) -> str:
        prompt = self._build_prompt(system_prompt=system_prompt, user_prompt=user_prompt)

        def _request() -> str:
            with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt", encoding="utf-8") as output_file:
                output_path = Path(output_file.name)

            try:
                command = self._exec_command(output_path)
                completed = subprocess.run(
                    command,
                    input=prompt,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    cwd=self.workspace,
                )
                if completed.returncode != 0:
                    details = (completed.stderr or completed.stdout).strip()
                    raise RuntimeError(f"Codex CLI execution failed: {details or 'unknown error'}")

                result = output_path.read_text(encoding="utf-8").strip() if output_path.exists() else ""
                if result:
                    return result

                fallback = completed.stdout.strip()
                if fallback:
                    return fallback

                raise RuntimeError("Codex CLI returned no final message.")
            finally:
                output_path.unlink(missing_ok=True)

        logger.debug("Requesting Codex CLI response with model=%s sandbox=%s", self.model or "default", self.sandbox)
        return retry(
            _request,
            attempts=self.max_retries,
            delay_seconds=self.retry_delay_seconds,
        )

    def _base_command(self) -> list[str]:
        if platform.system() == "Windows":
            return ["cmd", "/c", "codex"]
        return ["codex"]

    def _exec_command(self, output_path: Path) -> list[str]:
        command = self._base_command() + [
            "exec",
            "--cd",
            self.workspace,
            "--ask-for-approval",
            "never",
            "--color",
            "never",
            "--sandbox",
            self.sandbox,
            "--output-last-message",
            str(output_path),
            "-",
        ]

        if self.profile:
            command.extend(["--profile", self.profile])
        if self.model:
            command.extend(["--model", self.model])

        return command

    @staticmethod
    def _build_prompt(*, system_prompt: str, user_prompt: str) -> str:
        return (
            "Follow these system instructions exactly.\n\n"
            f"{system_prompt.strip()}\n\n"
            "User task:\n"
            f"{user_prompt.strip()}\n"
        )
