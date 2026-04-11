from __future__ import annotations

import os
import unittest

from task_agent.config import AgentConfig, ConfigError


class AgentConfigTests(unittest.TestCase):
    def test_validate_requires_neo4j_credentials(self) -> None:
        config = AgentConfig(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="",
        )

        with self.assertRaises(ConfigError):
            config.validate()

    def test_from_env_reads_required_values(self) -> None:
        old_env = dict(os.environ)
        try:
            os.environ["NEO4J_PASSWORD"] = "secret"
            os.environ["CODEX_SANDBOX"] = "workspace-write"
            os.environ["TASK_AGENT_MAX_DEPTH"] = "7"
            config = AgentConfig.from_env()
            self.assertEqual(config.neo4j_password, "secret")
            self.assertEqual(config.codex_sandbox, "workspace-write")
            self.assertEqual(config.max_depth, 7)
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    def test_validate_rejects_invalid_codex_sandbox(self) -> None:
        config = AgentConfig(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="secret",
            codex_sandbox="invalid",
        )

        with self.assertRaises(ConfigError):
            config.validate()


if __name__ == "__main__":
    unittest.main()
