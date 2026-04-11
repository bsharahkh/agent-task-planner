from __future__ import annotations

import argparse

from task_agent.agent import RecursiveTaskAgent
from task_agent.config import AgentConfig
from task_agent.llm import MissingLLMClient
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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = AgentConfig.from_env()
    if args.max_depth is not None:
        config.max_depth = args.max_depth
    if args.max_children is not None:
        config.max_children = args.max_children

    store = TaskGraphStore(
        uri=config.neo4j_uri,
        user=config.neo4j_user,
        password=config.neo4j_password,
    )
    agent = RecursiveTaskAgent(
        store=store,
        llm_client=MissingLLMClient(),
        max_depth=config.max_depth,
        max_children=config.max_children,
    )

    try:
        root_id = agent.run(args.prompt)
        print(f"Root task id: {root_id}")
        return 0
    finally:
        store.close()
