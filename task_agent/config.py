from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class AgentConfig:
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    max_depth: int = 8
    max_children: int = 6

    @classmethod
    def from_env(cls) -> "AgentConfig":
        return cls(
            neo4j_uri=os.getenv("NEO4J_URI", cls.neo4j_uri),
            neo4j_user=os.getenv("NEO4J_USER", cls.neo4j_user),
            neo4j_password=os.getenv("NEO4J_PASSWORD", cls.neo4j_password),
            max_depth=int(os.getenv("TASK_AGENT_MAX_DEPTH", "8")),
            max_children=int(os.getenv("TASK_AGENT_MAX_CHILDREN", "6")),
        )
