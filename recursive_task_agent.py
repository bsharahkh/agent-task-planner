"""
Recursive Task Tree Agent with Neo4j storage

Install:
  pip install neo4j

Set env vars:
  NEO4J_URI=bolt://localhost:7687
  NEO4J_USER=neo4j
  NEO4J_PASSWORD=your_password

Run:
  python task_agent.py
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase


# -----------------------------
# Utilities
# -----------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def new_id() -> str:
    return str(uuid.uuid4())

def safe_json_loads(text: str) -> Any:
    """
    Tries hard to extract JSON from LLM output.
    Supports raw JSON or JSON wrapped in markdown fences.
    """
    text = text.strip()

    # Remove markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try to extract first JSON object/array
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))

    raise ValueError(f"Could not parse JSON from: {text[:500]}")


# -----------------------------
# Task model
# -----------------------------

@dataclass
class TaskNode:
    task_id: str
    prompt: str
    status: str
    depth: int
    parent_id: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    meta: Optional[Dict[str, Any]] = None

    def to_properties(self) -> Dict[str, Any]:
        data = asdict(self)
        if data["meta"] is None:
            data["meta"] = {}
        return data


# -----------------------------
# Neo4j storage layer
# -----------------------------

class TaskGraphStore:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._init_schema()

    def close(self):
        self.driver.close()

    def _init_schema(self):
        with self.driver.session() as session:
            session.run("CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:Task) REQUIRE t.task_id IS UNIQUE")
            session.run("CREATE INDEX task_status IF NOT EXISTS FOR (t:Task) ON (t.status)")
            session.run("CREATE INDEX task_depth IF NOT EXISTS FOR (t:Task) ON (t.depth)")

    def upsert_task(self, task: TaskNode):
        props = task.to_properties()
        with self.driver.session() as session:
            session.run(
                """
                MERGE (t:Task {task_id: $task_id})
                SET t += $props
                WITH t
                OPTIONAL MATCH (p:Task {task_id: $parent_id})
                FOREACH (_ IN CASE WHEN $parent_id IS NULL THEN [] ELSE [1] END |
                    MERGE (t)-[:CHILD_OF]->(p)
                )
                """,
                task_id=task.task_id,
                props=props,
                parent_id=task.parent_id,
            )

    def update_task(self, task_id: str, **fields):
        fields["updated_at"] = now_iso()
        with self.driver.session() as session:
            session.run(
                """
                MATCH (t:Task {task_id: $task_id})
                SET t += $fields
                """,
                task_id=task_id,
                fields=fields,
            )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self.driver.session() as session:
            record = session.run(
                "MATCH (t:Task {task_id: $task_id}) RETURN t LIMIT 1",
                task_id=task_id,
            ).single()
            if not record:
                return None
            return dict(record["t"])

    def get_children(self, task_id: str) -> List[Dict[str, Any]]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Task)-[:CHILD_OF]->(p:Task {task_id: $task_id})
                RETURN c
                ORDER BY c.depth ASC, c.created_at ASC
                """,
                task_id=task_id,
            )
            return [dict(r["c"]) for r in result]

    def get_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (t:Task {status: $status})
                RETURN t
                ORDER BY t.depth ASC, t.created_at ASC
                """,
                status=status,
            )
            return [dict(r["t"]) for r in result]


# -----------------------------
# LLM interface
# -----------------------------

ANCHOR_PROMPT = """
You are a recursive task planner.

Goal:
Break the given task into smaller tasks until each leaf task is simple enough to execute directly.

Rules:
1. Preserve meaning at every level.
2. Only split when the task is still too large, ambiguous, or multi-step.
3. Each child must be simpler than its parent.
4. Stop splitting when a task is atomic enough to execute.
5. Prefer 2 to 6 children at a time.
6. Return strict JSON only.

Return schema:
{
  "action": "split" | "execute",
  "reason": "short explanation",
  "children": [
    {
      "prompt": "subtask text",
      "reason": "why this child exists"
    }
  ]
}

If action is "execute", children must be [].
"""

def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Replace this with your model call.

    For example:
    - OpenAI / Anthropic / local model
    - must return plain text containing JSON only

    This stub raises on purpose so you wire it to your model.
    """
    raise NotImplementedError("Connect call_llm() to your model provider.")


# -----------------------------
# Agent
# -----------------------------

class RecursiveTaskAgent:
    def __init__(self, store: TaskGraphStore, max_depth: int = 8, max_children: int = 6):
        self.store = store
        self.max_depth = max_depth
        self.max_children = max_children

    def create_root(self, prompt: str) -> str:
        task_id = new_id()
        task = TaskNode(
            task_id=task_id,
            prompt=prompt,
            status="pending",
            depth=0,
            parent_id=None,
            created_at=now_iso(),
            updated_at=now_iso(),
            meta={
                "kind": "root",
                "attempts": 0,
                "notes": [],
            },
        )
        self.store.upsert_task(task)
        return task_id

    def run(self, root_prompt: str) -> str:
        root_id = self.create_root(root_prompt)
        self._process_task(root_id)
        return root_id

    def _process_task(self, task_id: str):
        task = self.store.get_task(task_id)
        if not task:
            return

        depth = int(task.get("depth", 0))
        prompt = task["prompt"]
        status = task.get("status", "pending")

        if status in {"done", "blocked"}:
            return

        self.store.update_task(task_id, status="ongoing")
        task = self.store.get_task(task_id) or task

        try:
            decision = self._decide(task)

            if decision["action"] == "split" and depth < self.max_depth:
                children = decision.get("children", [])[: self.max_children]
                if not children:
                    # Safety fallback: execute if model said split but gave nothing
                    result = self._execute(task)
                    self.store.update_task(task_id, status="done", result=result)
                    return

                self.store.update_task(
                    task_id,
                    status="needs_broken_more",
                    meta={**(task.get("meta") or {}), "split_reason": decision.get("reason", "")},
                )

                for child in children:
                    child_id = new_id()
                    child_task = TaskNode(
                        task_id=child_id,
                        prompt=child["prompt"],
                        status="pending",
                        depth=depth + 1,
                        parent_id=task_id,
                        created_at=now_iso(),
                        updated_at=now_iso(),
                        meta={
                            "kind": "child",
                            "reason": child.get("reason", ""),
                            "attempts": 0,
                            "notes": [],
                        },
                    )
                    self.store.upsert_task(child_task)

                # Recurse into children
                for child in self.store.get_children(task_id):
                    if child.get("status") in {"pending", "ongoing", "needs_broken_more", "reopen"}:
                        self._process_task(child["task_id"])

                # After children finish, aggregate
                self._try_aggregate(task_id)
                return

            # Atomic enough to execute
            result = self._execute(task)
            self.store.update_task(task_id, status="done", result=result, error=None)

        except Exception as e:
            self.store.update_task(task_id, status="failed", error=str(e))

    def _decide(self, task: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "task_id": task["task_id"],
            "depth": task.get("depth", 0),
            "prompt": task["prompt"],
            "status": task.get("status"),
            "meta": task.get("meta", {}),
        }

        llm_output = call_llm(
            system_prompt=ANCHOR_PROMPT,
            user_prompt=json.dumps(payload, ensure_ascii=False, indent=2),
        )
        data = safe_json_loads(llm_output)

        if data.get("action") not in {"split", "execute"}:
            raise ValueError(f"Invalid action: {data.get('action')}")
        if data["action"] == "split" and not isinstance(data.get("children", []), list):
            raise ValueError("children must be a list")
        return data

    def _execute(self, task: Dict[str, Any]) -> str:
        """
        Final leaf execution.
        Replace this with your actual work executor.
        """
        prompt = task["prompt"]
        depth = task.get("depth", 0)

        # Example: ask the model to solve the atomic task directly
        leaf_prompt = f"""
You are executing a tiny leaf task.

Task:
{prompt}

Return a direct answer. Be concise and complete.
"""

        result = call_llm(
            system_prompt="You are a precise task executor.",
            user_prompt=leaf_prompt,
        )
        return result.strip()

    def _try_aggregate(self, task_id: str):
        """
        If all children are done, summarize them into the parent.
        If some children failed, mark parent for reopen.
        """
        parent = self.store.get_task(task_id)
        if not parent:
            return

        children = self.store.get_children(task_id)
        if not children:
            return

        statuses = [c.get("status") for c in children]

        if any(s in {"failed", "blocked"} for s in statuses):
            self.store.update_task(task_id, status="reopen")
            return

        if not all(s == "done" for s in statuses):
            self.store.update_task(task_id, status="ongoing")
            return

        combined = "\n\n".join(
            f"[Child {i+1}] {c.get('result', '')}"
            for i, c in enumerate(children)
        )

        summary_prompt = f"""
You are combining child task results into the parent task result.

Parent task:
{parent['prompt']}

Child results:
{combined}

Return a final consolidated answer for the parent.
"""

        try:
            summary = call_llm(
                system_prompt="You consolidate task results.",
                user_prompt=summary_prompt,
            )
            self.store.update_task(task_id, status="done", result=summary.strip())
        except Exception as e:
            self.store.update_task(task_id, status="reopen", error=str(e))


# -----------------------------
# Example usage
# -----------------------------

def main():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    store = TaskGraphStore(uri, user, password)
    agent = RecursiveTaskAgent(store)

    try:
        root_prompt = """
Build a Python agent that recursively decomposes a task into smaller tasks,
stores them in Neo4j, tracks state, executes tiny leaf tasks, and aggregates results.
"""
        root_id = agent.run(root_prompt)
        print("Root task id:", root_id)
    finally:
        store.close()


if __name__ == "__main__":
    main()