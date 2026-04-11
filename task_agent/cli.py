from __future__ import annotations

import argparse

from task_agent.agent import RecursiveTaskAgent
from task_agent.config import AgentConfig, ConfigError
from task_agent.llm import OpenAIResponsesClient
from task_agent.storage import TaskGraphStore


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

    store = TaskGraphStore(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password,
    )
    agent = RecursiveTaskAgent(
        store=store,
        llm_client=OpenAIResponsesClient(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
            model=config.openai_model,
            reasoning_effort=config.openai_reasoning_effort,
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
