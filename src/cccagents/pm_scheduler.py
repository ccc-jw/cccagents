import json
from dataclasses import asdict, dataclass
from pathlib import Path

from cccagents.phase2_models import Task, TaskStatus
from cccagents.recovery import RunRecord, reconcile_task_after_restart


@dataclass(frozen=True)
class ReconciliationResult:
    task_id: str
    previous_status: str
    next_status: str
    action: str
    notify_pm: bool


def build_startup_summary(project_root: str, interval_seconds: int) -> str:
    return f"PM Scheduler watching {project_root} every {interval_seconds}s"


def reconcile_project_after_restart(project_dir: Path) -> list[ReconciliationResult]:
    tasks_path = project_dir / "tasks.json"
    run_records_path = project_dir / "run-records.json"
    tasks = [_task_from_dict(item) for item in _read_json_array(tasks_path)]
    run_records = {
        item["task_id"]: RunRecord(**item)
        for item in _read_json_array(run_records_path)
    }

    results = []
    updated_tasks = []
    for task in tasks:
        decision = reconcile_task_after_restart(task, run_records.get(task.id))
        results.append(
            ReconciliationResult(
                task_id=task.id,
                previous_status=str(task.status),
                next_status=str(decision.next_status),
                action=decision.action,
                notify_pm=decision.notify_pm,
            )
        )
        task_data = asdict(task)
        task_data["status"] = str(decision.next_status)
        updated_tasks.append(task_data)

    tasks_path.write_text(json.dumps(updated_tasks, indent=2, sort_keys=True) + "\n")
    _append_recovery_evidence(project_dir, results)
    return results


def _read_json_array(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _task_from_dict(data: dict) -> Task:
    return Task(**{**data, "status": TaskStatus(data["status"])})


def _append_recovery_evidence(project_dir: Path, results: list[ReconciliationResult]) -> None:
    log_dir = project_dir / "08-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "restart-recovery.jsonl").open("a") as handle:
        for result in results:
            handle.write(json.dumps(asdict(result), sort_keys=True) + "\n")


def main() -> None:
    import os
    import time

    project_root = os.getenv("CCCAGENTS_PROJECT_ROOT", "/home/ubuntu/cccagents/projects")
    interval_seconds = int(os.getenv("CCCAGENTS_SCHEDULER_INTERVAL_SECONDS", "60"))
    print(build_startup_summary(project_root, interval_seconds), flush=True)
    while True:
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
