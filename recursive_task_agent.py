"""Backward-compatible entrypoint for the recursive task agent package."""

from task_agent.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
