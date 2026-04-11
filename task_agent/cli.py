from __future__ import annotations

import argparse
import logging
from pathlib import Path

from task_agent.agent import RecursiveTaskAgent
from task_agent.config import AgentConfig, ConfigError
from task_agent.env import load_dotenv
from task_agent.llm import CodexCLIClient
from task_agent.logging_utils import configure_logging
from task_agent.storage import TaskGraphStore

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the recursive Neo4j-backed task agent.")
    parser.add_argument(
        "prompt",
        nargs="?",
        default=(
            "Build a Python agent that recursively decomposes a task into smaller tasks, "
            "stores them in Neo4j, tracks state, executes tiny leaf tasks, and aggregates results."
        ),
        help="Root task prompt to plan and execute.",
    )
    parser.add_argument("--max-depth", type=int, default=None, help="Override the maximum recursion depth.")
    parser.add_argument("--max-children", type=int, default=None, help="Override the maximum number of child tasks.")
    parser.add_argument("--model", default=None, help="Override the Codex model, defaults to CODEX_MODEL.")
    parser.add_argument(
        "--profile",
        default=None,
        help="Override the Codex CLI profile, defaults to CODEX_PROFILE.",
    )
    parser.add_argument(
        "--sandbox",
        default=None,
        choices=["read-only", "workspace-write", "danger-full-access"],
        help="Override the Codex sandbox mode.",
    )
    return parser


def main() -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    config = AgentConfig.from_env()
    if args.max_depth is not None:
        config.max_depth = args.max_depth
    if args.max_children is not None:
        config.max_children = args.max_children
    if args.model is not None:
        config.codex_model = args.model
    if args.profile is not None:
        config.codex_profile = args.profile
    if args.sandbox is not None:
        config.codex_sandbox = args.sandbox

    try:
        config.validate()
    except ConfigError as exc:
        parser.error(str(exc))

    configure_logging(config.log_level)
    logger.info("Starting recursive task agent.")
    workspace = str(Path.cwd())

    store = TaskGraphStore(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password,
    )
    store.verify_connection()
    executor = CodexCLIClient(
        workspace=workspace,
        model=config.codex_model,
        profile=config.codex_profile,
        sandbox=config.codex_sandbox,
        timeout_seconds=config.codex_timeout_seconds,
        max_retries=config.codex_max_retries,
        retry_delay_seconds=config.retry_delay_seconds,
    )
    executor.verify_installation()
    agent = RecursiveTaskAgent(
        store=store,
        llm_client=executor,
        max_depth=config.max_depth,
        max_children=config.max_children,
    )

    try:
        root_id = agent.run(args.prompt)
        print(f"Root task id: {root_id}")
        return 0
    finally:
        store.close()
