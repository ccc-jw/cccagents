from dataclasses import replace

from cccagents.phase2_models import Task, TaskStatus
from cccagents.task_store import TaskStore


def test_task_store_saves_and_loads_task(tmp_path):
    store = TaskStore(tmp_path / "state.db")
    store.initialize()
    task = Task(
        id="task_001",
        project_id="proj_001",
        phase="REQUIREMENT_DRAFTING",
        flow="main",
        assignee_role="PDM",
        title="Draft PRD",
        description="Create PRD draft",
        created_at="2026-05-19T10:00:00Z",
    )

    store.save_task(task)
    loaded = store.get_task("task_001")

    assert loaded.id == "task_001"
    assert loaded.status == TaskStatus.PENDING
    assert loaded.next_handler_role == "PDM"


def test_task_store_lists_and_updates_tasks(tmp_path):
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    first = Task(
        id="task-1",
        project_id="demo",
        phase="DEV_IMPLEMENTATION",
        flow="main",
        assignee_role="DEV",
        title="Implement",
        description="Implement change",
        created_at="2026-06-13T10:00:00Z",
    )
    second = replace(first, id="task-2", phase="TEST_VALIDATION", assignee_role="TEST")
    store.save_task(first)
    store.save_task(second)

    store.update_status("task-1", TaskStatus.RUNNING)
    running = store.list_tasks("demo", TaskStatus.RUNNING)
    pending = store.list_tasks("demo", TaskStatus.PENDING)

    assert [task.id for task in running] == ["task-1"]
    assert [task.id for task in pending] == ["task-2"]


def test_task_store_claim_complete_and_fail(tmp_path):
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    task = Task(
        id="task-1",
        project_id="demo",
        phase="DEV_IMPLEMENTATION",
        flow="main",
        assignee_role="DEV",
        title="Implement",
        description="Implement change",
        created_at="2026-06-13T10:00:00Z",
    )
    store.save_task(task)

    claimed = store.claim_task("task-1", started_at="2026-06-13T10:01:00Z")
    store.complete_task("task-1", ["artifact-1"], completed_at="2026-06-13T10:02:00Z")
    completed = store.get_task("task-1")

    assert claimed.status == TaskStatus.RUNNING
    assert completed.status == TaskStatus.COMPLETED
    assert completed.output_artifact_ids == ["artifact-1"]
    assert completed.completed_at == "2026-06-13T10:02:00Z"

    failed_task = replace(task, id="task-2")
    store.save_task(failed_task)
    store.fail_task("task-2", ["issue-1"], updated_at="2026-06-13T10:03:00Z")
    failed = store.get_task("task-2")

    assert failed.status == TaskStatus.FAILED
    assert failed.issue_ids == ["issue-1"]
