from __future__ import annotations

import json

from task_agent.llm import LLMClient
from task_agent.models import TaskChildSpec, TaskDecision, TaskNode, TaskStatus
from task_agent.prompts import (
    AGGREGATION_SYSTEM_PROMPT,
    ANCHOR_PROMPT,
    EXECUTION_SYSTEM_PROMPT,
)
from task_agent.storage import TaskGraphStore
from task_agent.utils import new_id, safe_json_loads


class RecursiveTaskAgent:
    def __init__(self, *, store: TaskGraphStore, llm_client: LLMClient, max_depth: int = 8, max_children: int = 6):
        self.store = store
        self.llm_client = llm_client
        self.max_depth = max_depth
        self.max_children = max_children

    def run(self, root_prompt: str) -> str:
        root_task = self._build_root_task(root_prompt)
        self.store.upsert_task(root_task)
        self._process_task(root_task.task_id)
        return root_task.task_id

    def _build_root_task(self, prompt: str) -> TaskNode:
        return TaskNode(
            task_id=new_id(),
            prompt=prompt.strip(),
            depth=0,
            meta={
                "kind": "root",
                "attempts": 0,
                "notes": [],
            },
        )

    def _process_task(self, task_id: str) -> None:
        task = self.store.get_task(task_id)
        if task is None or task.status in {TaskStatus.DONE, TaskStatus.BLOCKED}:
            return

        self.store.update_task(task_id, status=TaskStatus.ONGOING)
        task = self.store.get_task(task_id) or task

        try:
            decision = self._decide(task)

            if decision.action == "split" and task.depth < self.max_depth:
                self._expand_task(task, decision)
                for child in self.store.get_children(task.task_id):
                    if child.status in {
                        TaskStatus.PENDING,
                        TaskStatus.ONGOING,
                        TaskStatus.NEEDS_BREAKDOWN,
                        TaskStatus.REOPEN,
                    }:
                        self._process_task(child.task_id)
                self._try_aggregate(task.task_id)
                return

            result = self._execute(task)
            self.store.update_task(task.task_id, status=TaskStatus.DONE, result=result, error=None)
        except Exception as exc:
            self.store.update_task(task.task_id, status=TaskStatus.FAILED, error=str(exc))

    def _expand_task(self, task: TaskNode, decision: TaskDecision) -> None:
        children = decision.children[: self.max_children]
        if not children:
            result = self._execute(task)
            self.store.update_task(task.task_id, status=TaskStatus.DONE, result=result, error=None)
            return

        self.store.update_task(
            task.task_id,
            status=TaskStatus.NEEDS_BREAKDOWN,
            meta={**task.meta, "split_reason": decision.reason},
        )

        for child in children:
            child_prompt = child.prompt.strip()
            if not child_prompt:
                continue

            child_task = TaskNode(
                task_id=new_id(),
                prompt=child_prompt,
                depth=task.depth + 1,
                parent_id=task.task_id,
                meta={
                    "kind": "child",
                    "reason": child.reason,
                    "attempts": 0,
                    "notes": [],
                },
            )
            self.store.upsert_task(child_task)

    def _decide(self, task: TaskNode) -> TaskDecision:
        payload = {
            "task_id": task.task_id,
            "depth": task.depth,
            "prompt": task.prompt,
            "status": task.status,
            "meta": task.meta,
        }

        raw_response = self.llm_client.complete(
            system_prompt=ANCHOR_PROMPT,
            user_prompt=json.dumps(payload, ensure_ascii=False, indent=2),
        )
        parsed = safe_json_loads(raw_response)

        action = parsed.get("action")
        if action not in {"split", "execute"}:
            raise ValueError(f"Invalid action: {action!r}")

        raw_children = parsed.get("children", [])
        if not isinstance(raw_children, list):
            raise ValueError("children must be a list")

        children = [
            TaskChildSpec(
                prompt=str(child.get("prompt", "")).strip(),
                reason=str(child.get("reason", "")).strip(),
            )
            for child in raw_children
            if isinstance(child, dict)
        ]

        if action == "split" and not children:
            return TaskDecision(action="execute", reason="Planner returned no usable children.", children=[])

        return TaskDecision(
            action=action,
            reason=str(parsed.get("reason", "")).strip(),
            children=children,
        )

    def _execute(self, task: TaskNode) -> str:
        prompt = f"""
You are executing a tiny leaf task.

Task:
{task.prompt}

Return a direct answer. Be concise and complete.
""".strip()

        response = self.llm_client.complete(
            system_prompt=EXECUTION_SYSTEM_PROMPT,
            user_prompt=prompt,
        )
        return response.strip()

    def _try_aggregate(self, task_id: str) -> None:
        parent = self.store.get_task(task_id)
        if parent is None:
            return

        children = self.store.get_children(task_id)
        if not children:
            return

        statuses = {child.status for child in children}
        if statuses & {TaskStatus.FAILED, TaskStatus.BLOCKED}:
            self.store.update_task(task_id, status=TaskStatus.REOPEN)
            return

        if any(status != TaskStatus.DONE for status in statuses):
            self.store.update_task(task_id, status=TaskStatus.ONGOING)
            return

        child_results = "\n\n".join(
            f"[Child {index}] {child.result or ''}" for index, child in enumerate(children, start=1)
        )

        aggregation_prompt = f"""
You are combining child task results into the parent task result.

Parent task:
{parent.prompt}

Child results:
{child_results}

Return a final consolidated answer for the parent.
""".strip()

        try:
            summary = self.llm_client.complete(
                system_prompt=AGGREGATION_SYSTEM_PROMPT,
                user_prompt=aggregation_prompt,
            )
            self.store.update_task(task_id, status=TaskStatus.DONE, result=summary.strip(), error=None)
        except Exception as exc:
            self.store.update_task(task_id, status=TaskStatus.REOPEN, error=str(exc))
