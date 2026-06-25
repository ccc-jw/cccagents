"""Extended tests for pm_scheduler.

Covers the small cron-loop path that ``coverage report`` flagged as
uncovered (lines 55, 72-79, 83 of pm_scheduler.py).
"""

import io
import json
import os
import signal
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pytest

from cccagents.phase2_models import Task, TaskStatus
from cccagents.pm_scheduler import (
    ReconciliationResult,
    build_startup_summary,
    main,
    reconcile_project_after_restart,
)
from cccagents.recovery import RunRecord


def test_build_startup_summary_format():
    """The startup banner must include the project root and interval."""
    out = build_startup_summary("/home/u/projects", 60)
    assert "/home/u/projects" in out
    assert "60s" in out
    assert out.startswith("PM Scheduler watching")


def _task(task_id: str, status: TaskStatus) -> Task:
    return Task(
        id=task_id,
        project_id="p1",
        phase="DEVELOPMENT",
        flow="main",
        assignee_role="DEV",
        title="t",
        description="d",
        created_at="2026-06-24T00:00:00Z",
        status=status,
    )


def _record(task_id: str, **overrides) -> RunRecord:
    base = dict(
        project_id="p1",
        task_id=task_id,
        run_id="r1",
        status="running",
        permission_level="L1",
        idempotent=True,
        process_alive=False,
        heartbeat_stale=True,
        destructive=False,
        external=False,
        same_project_write_lock=False,
    )
    base.update(overrides)
    return RunRecord(**base)


def test_reconcile_writes_updated_tasks_back(tmp_path: Path):
    """The reconciliation pass must persist the new task statuses."""
    project_dir = tmp_path / "p1"
    project_dir.mkdir()
    tasks = [
        _task("t1", TaskStatus.RUNNING),
        _task("t2", TaskStatus.PENDING),
        _task("t3", TaskStatus.COMPLETED),
    ]
    records = [
        _record("t1"),  # RUNNING + heartbeat stale → INTERRUPTED
        _record("t2"),  # not used (PENDING)
        _record("t3"),  # not used (COMPLETED)
    ]
    (project_dir / "tasks.json").write_text(json.dumps([t.__dict__ for t in tasks]))
    (project_dir / "run-records.json").write_text(json.dumps([r.__dict__ for r in records]))

    results = reconcile_project_after_restart(project_dir)

    assert {r.task_id: r.next_status for r in results} == {
        "t1": "interrupted",
        "t2": "pending",
        "t3": "completed",
    }

    # Persisted file reflects the decisions.
    persisted = json.loads((project_dir / "tasks.json").read_text())
    by_id = {p["id"]: p["status"] for p in persisted}
    assert by_id == {"t1": "interrupted", "t2": "pending", "t3": "completed"}

    # Recovery evidence is appended.
    log = (project_dir / "08-logs" / "restart-recovery.jsonl").read_text()
    assert "t1" in log
    assert "interrupted" in log


def test_reconcile_handles_missing_tasks_and_records(tmp_path: Path):
    """A fresh project with neither tasks.json nor run-records.json is a no-op."""
    project_dir = tmp_path / "fresh"
    project_dir.mkdir()

    results = reconcile_project_after_restart(project_dir)

    assert results == []


def test_reconcile_recovery_log_is_appended(tmp_path: Path):
    """Calling reconciliation twice should append, not overwrite, the log."""
    project_dir = tmp_path / "p1"
    project_dir.mkdir()
    tasks = [_task("t1", TaskStatus.RUNNING)]
    records = [_record("t1")]
    (project_dir / "tasks.json").write_text(json.dumps([t.__dict__ for t in tasks]))
    (project_dir / "run-records.json").write_text(json.dumps([r.__dict__ for r in records]))

    reconcile_project_after_restart(project_dir)
    # Reset task to RUNNING so reconcile_project_after_restart has something
    # to log again.
    (project_dir / "tasks.json").write_text(json.dumps([t.__dict__ for t in tasks]))
    reconcile_project_after_restart(project_dir)

    lines = (project_dir / "08-logs" / "restart-recovery.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    # Both lines should be valid JSON for the same task.
    for line in lines:
        parsed = json.loads(line)
        assert parsed["task_id"] == "t1"


def test_main_prints_startup_banner(monkeypatch):
    """``main()`` should print the startup banner on entry."""
    # Force main() to break out of its loop after the banner.
    sleep_calls = {"n": 0}

    def fake_sleep(_seconds: float) -> None:
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 1:
            raise KeyboardInterrupt

    buf = io.StringIO()
    monkeypatch.setattr("time.sleep", fake_sleep)
    with redirect_stdout(buf):
        with pytest.raises(KeyboardInterrupt):
            main()
    out = buf.getvalue()
    assert "PM Scheduler watching" in out
    # Default project root is /home/ubuntu/cccagents/projects
    assert "cccagents" in out
    assert "60s" in out


def test_main_honours_interval_env(monkeypatch):
    """``CCCAGENTS_SCHEDULER_INTERVAL_SECONDS`` controls the sleep interval."""
    sleep_calls = []

    def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)
        if len(sleep_calls) >= 1:
            raise KeyboardInterrupt

    monkeypatch.setenv("CCCAGENTS_SCHEDULER_INTERVAL_SECONDS", "5")
    monkeypatch.setattr("time.sleep", fake_sleep)
    with pytest.raises(KeyboardInterrupt):
        main()
    assert sleep_calls == [5.0]


def test_main_honours_project_root_env(monkeypatch):
    """``CCCAGENTS_PROJECT_ROOT`` overrides the default project path."""
    sleep_calls = {"n": 0}

    def fake_sleep(_seconds: float) -> None:
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 1:
            raise KeyboardInterrupt

    monkeypatch.setenv("CCCAGENTS_PROJECT_ROOT", "/custom/project/root")
    monkeypatch.setattr("time.sleep", fake_sleep)
    buf = io.StringIO()
    with redirect_stdout(buf):
        with pytest.raises(KeyboardInterrupt):
            main()
    assert "/custom/project/root" in buf.getvalue()


def test_reconcile_decision_for_blocked_status(tmp_path: Path):
    """BLOCKED tasks are reported to PM via notify_pm=True."""
    project_dir = tmp_path / "p1"
    project_dir.mkdir()
    tasks = [_task("t1", TaskStatus.BLOCKED)]
    (project_dir / "tasks.json").write_text(json.dumps([t.__dict__ for t in tasks]))
    (project_dir / "run-records.json").write_text("[]")

    results = reconcile_project_after_restart(project_dir)
    assert results[0].next_status == "blocked"
    assert results[0].action == "summarize_blocker"
    assert results[0].notify_pm is True


def test_reconcile_decision_for_failed_status(tmp_path: Path):
    """FAILED tasks emit propose_fix_task with notify_pm=True."""
    project_dir = tmp_path / "p1"
    project_dir.mkdir()
    tasks = [_task("t1", TaskStatus.FAILED)]
    (project_dir / "tasks.json").write_text(json.dumps([t.__dict__ for t in tasks]))
    (project_dir / "run-records.json").write_text("[]")

    results = reconcile_project_after_restart(project_dir)
    assert results[0].next_status == "failed"
    assert results[0].action == "propose_fix_task"
    assert results[0].notify_pm is True


def test_reconcile_running_with_healthy_record_keeps_running(tmp_path: Path):
    """A RUNNING task whose run record says process_alive AND heartbeat fresh
    must be left alone (no notify_pm, action=keep_running)."""
    project_dir = tmp_path / "p1"
    project_dir.mkdir()
    tasks = [_task("t1", TaskStatus.RUNNING)]
    records = [_record("t1", process_alive=True, heartbeat_stale=False)]
    (project_dir / "tasks.json").write_text(json.dumps([t.__dict__ for t in tasks]))
    (project_dir / "run-records.json").write_text(json.dumps([r.__dict__ for r in records]))

    results = reconcile_project_after_restart(project_dir)
    assert results[0].next_status == "running"
    assert results[0].action == "keep_running"
    assert results[0].notify_pm is False