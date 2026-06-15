import json
import sqlite3
from pathlib import Path

from cccagents.phase2_models import Task, TaskStatus


class TaskStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    flow TEXT NOT NULL,
                    assignee_role TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    parent_task_id TEXT,
                    input_artifact_ids TEXT NOT NULL,
                    output_artifact_ids TEXT NOT NULL,
                    issue_ids TEXT NOT NULL,
                    started_at TEXT,
                    updated_at TEXT,
                    due_at TEXT,
                    completed_at TEXT,
                    next_handler_role TEXT,
                    next_handler_reason TEXT
                )
                """
            )

    def save_task(self, task: Task) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.project_id,
                    task.phase,
                    task.flow,
                    task.assignee_role,
                    task.title,
                    task.description,
                    task.created_at,
                    task.status.value,
                    task.parent_task_id,
                    json.dumps(task.input_artifact_ids),
                    json.dumps(task.output_artifact_ids),
                    json.dumps(task.issue_ids),
                    task.started_at,
                    task.updated_at,
                    task.due_at,
                    task.completed_at,
                    task.next_handler_role,
                    task.next_handler_reason,
                ),
            )

    def get_task(self, task_id: str) -> Task:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        return self._task_from_row(row)

    def list_tasks(self, project_id: str, status: TaskStatus | None = None) -> list[Task]:
        query = "SELECT * FROM tasks WHERE project_id = ?"
        params: tuple[str, ...]
        if status is None:
            params = (project_id,)
        else:
            query += " AND status = ?"
            params = (project_id, status.value)
        query += " ORDER BY created_at, id"
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._task_from_row(row) for row in rows]

    def update_status(self, task_id: str, status: TaskStatus, updated_at: str | None = None) -> Task:
        task = self.get_task(task_id)
        updated = Task(
            **{
                **task.__dict__,
                "status": status,
                "updated_at": updated_at or task.updated_at,
            }
        )
        self.save_task(updated)
        return updated

    def claim_task(self, task_id: str, started_at: str) -> Task:
        task = self.get_task(task_id)
        updated = Task(
            **{
                **task.__dict__,
                "status": TaskStatus.RUNNING,
                "started_at": started_at,
                "updated_at": started_at,
            }
        )
        self.save_task(updated)
        return updated

    def complete_task(self, task_id: str, output_artifact_ids: list[str], completed_at: str) -> Task:
        task = self.get_task(task_id)
        updated = Task(
            **{
                **task.__dict__,
                "status": TaskStatus.COMPLETED,
                "output_artifact_ids": output_artifact_ids,
                "completed_at": completed_at,
                "updated_at": completed_at,
            }
        )
        self.save_task(updated)
        return updated

    def fail_task(self, task_id: str, issue_ids: list[str], updated_at: str) -> Task:
        task = self.get_task(task_id)
        updated = Task(
            **{
                **task.__dict__,
                "status": TaskStatus.FAILED,
                "issue_ids": issue_ids,
                "updated_at": updated_at,
            }
        )
        self.save_task(updated)
        return updated

    def _task_from_row(self, row: tuple) -> Task:
        return Task(
            id=row[0],
            project_id=row[1],
            phase=row[2],
            flow=row[3],
            assignee_role=row[4],
            title=row[5],
            description=row[6],
            created_at=row[7],
            status=TaskStatus(row[8]),
            parent_task_id=row[9],
            input_artifact_ids=json.loads(row[10]),
            output_artifact_ids=json.loads(row[11]),
            issue_ids=json.loads(row[12]),
            started_at=row[13],
            updated_at=row[14],
            due_at=row[15],
            completed_at=row[16],
            next_handler_role=row[17],
            next_handler_reason=row[18],
        )
