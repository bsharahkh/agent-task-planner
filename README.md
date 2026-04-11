# Task Agent

A small recursive task-planning agent that:

- decomposes large tasks into smaller tasks,
- stores the task tree in Neo4j,
- executes leaf tasks through an LLM client,
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
```

## Run

```bash
python recursive_task_agent.py "Build an internal research assistant"
```

By default the package ships with a placeholder LLM client that raises until you
connect your model provider in `task_agent/llm.py`.
