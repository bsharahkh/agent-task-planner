# Task Agent

A recursive task-planning agent that:

- decomposes large tasks into smaller tasks,
- stores the task tree in Neo4j,
- executes leaf tasks through OpenAI's Responses API,
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
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-5.3-codex
OPENAI_REASONING_EFFORT=medium
OPENAI_TIMEOUT_SECONDS=60
OPENAI_MAX_RETRIES=3
TASK_AGENT_RETRY_DELAY_SECONDS=1.5
TASK_AGENT_LOG_LEVEL=INFO
```

`NEO4J_PASSWORD` is required, and the OpenAI key must be provided either directly through `OPENAI_API_KEY` or indirectly through `OPENAI_API_KEY_ENV`.

If you do not want to store the literal API key in `.env`, you can point to a system environment variable instead:

```bash
OPENAI_API_KEY_ENV=MY_OPENAI_KEY
```

Then set `MY_OPENAI_KEY` in your Windows user or system environment. The app will resolve the key from there at runtime.

## Run

```bash
python recursive_task_agent.py "Build an internal research assistant"
```

The CLI automatically loads a local `.env` file when present, verifies Neo4j connectivity on startup, and retries OpenAI requests using the configured retry settings.

## Codex usage

This project now defaults to an OpenAI Codex-oriented model through
`task_agent/llm.py`.

The current OpenAI models docs list `gpt-5.3-codex` as the most capable
agentic coding model, so it is the default here. You can override it with:

```bash
python recursive_task_agent.py "Refactor this Python service" --model gpt-5-codex
```

If you want to switch models later, change `OPENAI_MODEL` or pass `--model`.
