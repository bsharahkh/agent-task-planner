from __future__ import annotations

import argparse
import logging

from task_agent.agent import RecursiveTaskAgent
from task_agent.config import AgentConfig, ConfigError
from task_agent.env import load_dotenv
from task_agent.llm import OpenAIResponsesClient
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
    parser.add_argument("--model", default=None, help="Override the OpenAI model, defaults to OPENAI_MODEL.")
    parser.add_argument(
        "--reasoning-effort",
        default=None,
        choices=["minimal", "low", "medium", "high", "xhigh"],
        help="Override the OpenAI reasoning effort.",
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
        config.openai_model = args.model
    if args.reasoning_effort is not None:
        config.openai_reasoning_effort = args.reasoning_effort

    try:
        config.validate()
    except ConfigError as exc:
        parser.error(str(exc))

    configure_logging(config.log_level)
    logger.info("Starting recursive task agent.")
    api_key = config.resolved_openai_api_key()

    store = TaskGraphStore(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password,
    )
    store.verify_connection()
    agent = RecursiveTaskAgent(
        store=store,
        llm_client=OpenAIResponsesClient(
            api_key=api_key,
            base_url=config.openai_base_url,
            model=config.openai_model,
            reasoning_effort=config.openai_reasoning_effort,
            timeout_seconds=config.openai_timeout_seconds,
            max_retries=config.openai_max_retries,
            retry_delay_seconds=config.retry_delay_seconds,
        ),
        max_depth=config.max_depth,
        max_children=config.max_children,
    )

    try:
        root_id = agent.run(args.prompt)
        print(f"Root task id: {root_id}")
        return 0
    finally:
        store.close()
