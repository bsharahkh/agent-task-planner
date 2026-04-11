from __future__ import annotations

import unittest
from pathlib import Path

from task_agent.llm import CodexCLIClient


class CodexCLIClientTests(unittest.TestCase):
    def test_exec_command_includes_non_interactive_flags(self) -> None:
        client = CodexCLIClient(
            workspace="C:\\repo",
            model="gpt-5-codex",
            profile="default",
            sandbox="read-only",
        )

        command = client._exec_command(Path("out.txt"))

        self.assertIn("exec", command)
        self.assertIn("--ask-for-approval", command)
        self.assertIn("never", command)
        self.assertIn("--output-last-message", command)
        self.assertIn("--model", command)
        self.assertIn("--profile", command)

    def test_prompt_builder_combines_system_and_user_prompt(self) -> None:
        prompt = CodexCLIClient._build_prompt(
            system_prompt="System rule",
            user_prompt="Do the task",
        )

        self.assertIn("System rule", prompt)
        self.assertIn("Do the task", prompt)


if __name__ == "__main__":
    unittest.main()
