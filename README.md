# Task Agent

A recursive task-planning agent that:

- decomposes large tasks into smaller tasks,
- stores the task tree in Neo4j,
- executes leaf tasks through the local Codex CLI,
- aggregates child results back into parent tasks.

## Structure

```text
task_agent/
  agent.py
  cli.py
  config.py
  llm.py
  models.py
  prompts.py
  storage.py
  utils.py
recursive_task_agent.py
pyproject.toml
```

## Install

```bash
pip install -e .
```

## Environment

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
CODEX_MODEL=
CODEX_PROFILE=
CODEX_SANDBOX=read-only
CODEX_TIMEOUT_SECONDS=120
CODEX_MAX_RETRIES=3
TASK_AGENT_RETRY_DELAY_SECONDS=1.5
TASK_AGENT_LOG_LEVEL=INFO
```

`NEO4J_PASSWORD` is required. Codex authentication comes from your local Codex CLI session instead of `OPENAI_API_KEY`.

## Run

```bash
python recursive_task_agent.py "Build an internal research assistant"
```

The CLI automatically loads a local `.env` file when present, verifies Neo4j connectivity on startup, checks that Codex CLI is installed, and retries Codex runs using the configured retry settings.

## Codex usage

This project now uses the local Codex CLI through
`task_agent/llm.py`.

Before running the agent, make sure Codex CLI is authenticated on this machine.
If needed, run `codex login`.

You can override the model or profile with:

```bash
python recursive_task_agent.py "Refactor this Python service" --model gpt-5-codex --profile default
```

If you want to switch settings later, change `CODEX_MODEL`, `CODEX_PROFILE`, or `CODEX_SANDBOX`, or pass the matching CLI flags.
