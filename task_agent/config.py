from __future__ import annotations

import os
from dataclasses import dataclass


class ConfigError(ValueError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(slots=True)
class AgentConfig:
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    openai_api_key: str = ""
    openai_base_url: str | None = None
    openai_model: str = "gpt-5.3-codex"
    openai_reasoning_effort: str = "medium"
    max_depth: int = 50
    max_children: int = 50

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            neo4j_uri=os.getenv("NEO4J_URI", cls.neo4j_uri).strip(),
            neo4j_user=os.getenv("NEO4J_USER", cls.neo4j_user).strip(),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "").strip(),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
            openai_base_url=(os.getenv("OPENAI_BASE_URL") or "").strip() or None,
            openai_model=os.getenv("OPENAI_MODEL", cls.openai_model).strip(),
            openai_reasoning_effort=os.getenv("OPENAI_REASONING_EFFORT", cls.openai_reasoning_effort).strip(),
            max_depth=int(os.getenv("TASK_AGENT_MAX_DEPTH", str(cls.max_depth))),
            max_children=int(os.getenv("TASK_AGENT_MAX_CHILDREN", str(cls.max_children))),
        )

    def validate(self) -> None:
        missing_vars: list[str] = []

        if not self.neo4j_uri:
            missing_vars.append("NEO4J_URI")
        if not self.neo4j_user:
            missing_vars.append("NEO4J_USER")
        if not self.neo4j_password:
            missing_vars.append("NEO4J_PASSWORD")
        if not self.openai_api_key:
            missing_vars.append("OPENAI_API_KEY")

        if missing_vars:
            joined = ", ".join(missing_vars)
            raise ConfigError(f"Missing required environment variables: {joined}")

        if self.max_depth < 1:
            raise ConfigError("TASK_AGENT_MAX_DEPTH must be at least 1.")
        if self.max_children < 1:
            raise ConfigError("TASK_AGENT_MAX_CHILDREN must be at least 1.")
