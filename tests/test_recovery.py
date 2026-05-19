from cccagents.phase2_models import Task, TaskStatus
from cccagents.recovery import RunRecord, reconcile_task_after_restart


def make_task(status: TaskStatus) -> Task:
    return Task(
        id="task_1",
        project_id="project_1",
        phase="DEVELOPMENT",
        flow="main",
        assignee_role="DEV",
        title="Do work",
        description="Run a small task",
        created_at="2026-05-20T00:00:00Z",
        status=status,
    )


def test_pending_task_is_resumed_after_restart():
    decision = reconcile_task_after_restart(task=make_task(TaskStatus.PENDING), run_record=None)

    assert decision.next_status == TaskStatus.PENDING
    assert decision.action == "dispatch"
    assert decision.notify_pm is False


def test_live_running_task_is_kept_running():
    run_record = RunRecord(
        project_id="project_1",
        task_id="task_1",
        run_id="run_1",
        status="running",
        permission_level="L1",
        idempotent=True,
        process_alive=True,
        heartbeat_stale=False,
        destructive=False,
        external=False,
        same_project_write_lock=False,
    )

    decision = reconcile_task_after_restart(make_task(TaskStatus.RUNNING), run_record)

    assert decision.next_status == TaskStatus.RUNNING
    assert decision.action == "keep_running"
    assert decision.notify_pm is False


def test_stale_running_task_becomes_interrupted():
    run_record = RunRecord(
        project_id="project_1",
        task_id="task_1",
        run_id="run_1",
        status="running",
        permission_level="L1",
        idempotent=False,
        process_alive=False,
        heartbeat_stale=True,
        destructive=False,
        external=False,
        same_project_write_lock=False,
    )

    decision = reconcile_task_after_restart(make_task(TaskStatus.RUNNING), run_record)

    assert decision.next_status == TaskStatus.INTERRUPTED
    assert decision.action == "mark_interrupted"
    assert decision.notify_pm is True


def test_safe_interrupted_task_can_retry_automatically():
    run_record = RunRecord(
        project_id="project_1",
        task_id="task_1",
        run_id="run_1",
        status="interrupted",
        permission_level="L1",
        idempotent=True,
        process_alive=False,
        heartbeat_stale=True,
        destructive=False,
        external=False,
        same_project_write_lock=False,
    )

    decision = reconcile_task_after_restart(make_task(TaskStatus.INTERRUPTED), run_record)

    assert decision.next_status == TaskStatus.PENDING
    assert decision.action == "retry"
    assert decision.notify_pm is False


def test_unsafe_interrupted_task_waits_for_user_decision():
    run_record = RunRecord(
        project_id="project_1",
        task_id="task_1",
        run_id="run_1",
        status="interrupted",
        permission_level="L3",
        idempotent=True,
        process_alive=False,
        heartbeat_stale=True,
        destructive=False,
        external=True,
        same_project_write_lock=False,
    )

    decision = reconcile_task_after_restart(make_task(TaskStatus.INTERRUPTED), run_record)

    assert decision.next_status == TaskStatus.INTERRUPTED
    assert decision.action == "request_decision"
    assert decision.notify_pm is True
