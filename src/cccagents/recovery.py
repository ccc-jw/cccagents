from dataclasses import dataclass

from cccagents.phase2_models import Task, TaskStatus


@dataclass(frozen=True)
class RunRecord:
    project_id: str
    task_id: str
    run_id: str
    status: str
    permission_level: str
    idempotent: bool
    process_alive: bool
    heartbeat_stale: bool
    destructive: bool
    external: bool
    same_project_write_lock: bool


@dataclass(frozen=True)
class RecoveryDecision:
    next_status: TaskStatus
    action: str
    notify_pm: bool


def reconcile_task_after_restart(task: Task, run_record: RunRecord | None) -> RecoveryDecision:
    if task.status == TaskStatus.PENDING:
        return RecoveryDecision(TaskStatus.PENDING, "dispatch", False)

    if task.status == TaskStatus.RUNNING:
        if run_record and run_record.process_alive and not run_record.heartbeat_stale:
            return RecoveryDecision(TaskStatus.RUNNING, "keep_running", False)
        return RecoveryDecision(TaskStatus.INTERRUPTED, "mark_interrupted", True)

    if task.status == TaskStatus.INTERRUPTED:
        if run_record and is_safe_for_auto_retry(run_record):
            return RecoveryDecision(TaskStatus.PENDING, "retry", False)
        return RecoveryDecision(TaskStatus.INTERRUPTED, "request_decision", True)

    if task.status == TaskStatus.BLOCKED:
        return RecoveryDecision(TaskStatus.BLOCKED, "summarize_blocker", True)

    if task.status == TaskStatus.FAILED:
        return RecoveryDecision(TaskStatus.FAILED, "propose_fix_task", True)

    if task.status == TaskStatus.COMPLETED:
        return RecoveryDecision(TaskStatus.COMPLETED, "do_not_rerun", False)

    return RecoveryDecision(task.status, "no_action", False)


def is_safe_for_auto_retry(run_record: RunRecord) -> bool:
    return (
        run_record.permission_level in {"L0", "L1"}
        and run_record.idempotent
        and not run_record.destructive
        and not run_record.external
        and not run_record.same_project_write_lock
    )
