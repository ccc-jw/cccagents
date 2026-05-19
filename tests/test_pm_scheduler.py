import json

from cccagents.pm_scheduler import build_startup_summary, reconcile_project_after_restart


def test_build_startup_summary_reports_project_root_and_interval():
    summary = build_startup_summary(project_root="/home/ubuntu/cccagents/projects", interval_seconds=60)

    assert summary == "PM Scheduler watching /home/ubuntu/cccagents/projects every 60s"


def test_reconcile_project_after_restart_marks_stale_running_task_interrupted(tmp_path):
    project_dir = tmp_path / "projects" / "demo"
    project_dir.mkdir(parents=True)
    (project_dir / "tasks.json").write_text(
        json.dumps(
            [
                {
                    "id": "task_1",
                    "project_id": "demo",
                    "phase": "DEVELOPMENT",
                    "flow": "main",
                    "assignee_role": "DEV",
                    "title": "Do work",
                    "description": "Run a small task",
                    "created_at": "2026-05-20T00:00:00Z",
                    "status": "running",
                }
            ]
        )
    )
    (project_dir / "run-records.json").write_text(
        json.dumps(
            [
                {
                    "project_id": "demo",
                    "task_id": "task_1",
                    "run_id": "run_1",
                    "status": "running",
                    "permission_level": "L1",
                    "idempotent": False,
                    "process_alive": False,
                    "heartbeat_stale": True,
                    "destructive": False,
                    "external": False,
                    "same_project_write_lock": False,
                }
            ]
        )
    )

    results = reconcile_project_after_restart(project_dir)

    assert results[0].task_id == "task_1"
    assert results[0].action == "mark_interrupted"
    assert results[0].next_status == "interrupted"
    saved_tasks = json.loads((project_dir / "tasks.json").read_text())
    assert saved_tasks[0]["status"] == "interrupted"
    evidence = (project_dir / "08-logs" / "restart-recovery.jsonl").read_text()
    assert '"action": "mark_interrupted"' in evidence


def test_reconcile_project_after_restart_retries_safe_interrupted_task(tmp_path):
    project_dir = tmp_path / "projects" / "demo"
    project_dir.mkdir(parents=True)
    (project_dir / "tasks.json").write_text(
        json.dumps(
            [
                {
                    "id": "task_2",
                    "project_id": "demo",
                    "phase": "DEVELOPMENT",
                    "flow": "main",
                    "assignee_role": "DEV",
                    "title": "Retry work",
                    "description": "Retry an idempotent task",
                    "created_at": "2026-05-20T00:00:00Z",
                    "status": "interrupted",
                }
            ]
        )
    )
    (project_dir / "run-records.json").write_text(
        json.dumps(
            [
                {
                    "project_id": "demo",
                    "task_id": "task_2",
                    "run_id": "run_2",
                    "status": "interrupted",
                    "permission_level": "L1",
                    "idempotent": True,
                    "process_alive": False,
                    "heartbeat_stale": True,
                    "destructive": False,
                    "external": False,
                    "same_project_write_lock": False,
                }
            ]
        )
    )

    results = reconcile_project_after_restart(project_dir)

    assert results[0].action == "retry"
    assert results[0].next_status == "pending"
    saved_tasks = json.loads((project_dir / "tasks.json").read_text())
    assert saved_tasks[0]["status"] == "pending"
