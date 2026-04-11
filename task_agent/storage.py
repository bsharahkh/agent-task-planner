from __future__ import annotations

from typing import Any

from neo4j import GraphDatabase

from task_agent.models import TaskNode
from task_agent.utils import now_iso


class TaskGraphStore:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._init_schema()

    def close(self) -> None:
        self.driver.close()

    def _init_schema(self) -> None:
        with self.driver.session() as session:
            session.run(
                "CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:Task) REQUIRE t.task_id IS UNIQUE"
            )
            session.run("CREATE INDEX task_status IF NOT EXISTS FOR (t:Task) ON (t.status)")
            session.run("CREATE INDEX task_depth IF NOT EXISTS FOR (t:Task) ON (t.depth)")

    def upsert_task(self, task: TaskNode) -> None:
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
                props=task.to_properties(),
                parent_id=task.parent_id,
            )

    def update_task(self, task_id: str, **fields: Any) -> None:
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

    def get_task(self, task_id: str) -> TaskNode | None:
        with self.driver.session() as session:
            record = session.run(
                "MATCH (t:Task {task_id: $task_id}) RETURN t LIMIT 1",
                task_id=task_id,
            ).single()
            if not record:
                return None
            return TaskNode.from_record(dict(record["t"]))

    def get_children(self, task_id: str) -> list[TaskNode]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (c:Task)-[:CHILD_OF]->(p:Task {task_id: $task_id})
                RETURN c
                ORDER BY c.depth ASC, c.created_at ASC
                """,
                task_id=task_id,
            )
            return [TaskNode.from_record(dict(row["c"])) for row in result]

    def get_tasks_by_status(self, status: str) -> list[TaskNode]:
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (t:Task {status: $status})
                RETURN t
                ORDER BY t.depth ASC, t.created_at ASC
                """,
                status=status,
            )
            return [TaskNode.from_record(dict(row["t"])) for row in result]
