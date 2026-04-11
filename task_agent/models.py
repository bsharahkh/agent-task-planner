from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from task_agent.utils import now_iso


class TaskStatus(str, Enum):
    PENDING = "pending"
    ONGOING = "ongoing"
    NEEDS_BREAKDOWN = "needs_broken_more"
    REOPEN = "reopen"
    DONE = "done"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(slots=True)
class TaskNode:
    task_id: str
    prompt: str
    depth: int
    status: str = TaskStatus.PENDING
    parent_id: str | None = None
    result: str | None = None
    error: str | None = None
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_properties(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "TaskNode":
        return cls(
            task_id=record["task_id"],
            prompt=record["prompt"],
            depth=int(record.get("depth", 0)),
            status=record.get("status", TaskStatus.PENDING),
            parent_id=record.get("parent_id"),
            result=record.get("result"),
            error=record.get("error"),
            created_at=record.get("created_at", now_iso()),
            updated_at=record.get("updated_at", now_iso()),
            meta=record.get("meta") or {},
        )


@dataclass(slots=True)
class TaskChildSpec:
    prompt: str
    reason: str = ""


@dataclass(slots=True)
class TaskDecision:
    action: str
    reason: str
    children: list[TaskChildSpec]
