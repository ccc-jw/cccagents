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
