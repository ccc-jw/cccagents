# cccagents Phase 4 Long-running Async Operation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 4 durable async operation layer so Hermes/PM can recover tasks after restart, enforce Feishu allowlists, schedule multiple projects safely, and notify users through PM.

**Architecture:** Add small focused Python helper modules for service specs, Feishu allowlists, run recovery records, scheduling decisions, and PM notifications. Keep Hermes as the runtime and Claude Code CLI as the per-task executor; repository code provides deterministic contracts, tests, scripts, and redacted evidence templates.

**Tech Stack:** Python dataclasses/enums, pytest, pathlib/json/sqlite-friendly records, Linux systemd documentation/scripts, Hermes Gateway websocket mode, Feishu user allowlist, Claude Code CLI narrow tool permissions.

---

## File Structure

Create or modify these files:

- Create `src/cccagents/phase4_service.py`: systemd service unit builders and service names for Hermes Gateway and PM Scheduler.
- Create `tests/test_phase4_service.py`: verifies service unit content is durable, restartable, and references Linux-only env files without embedding secrets.
- Create `src/cccagents/feishu_allowlist.py`: Feishu user allowlist policy and redacted audit decisions.
- Create `tests/test_feishu_allowlist.py`: verifies allowed users pass, unknown users are denied, open access is rejected for Phase 4.
- Create `src/cccagents/recovery.py`: run record model, restart reconciliation, safe retry decision rules.
- Create `tests/test_recovery.py`: verifies pending resume, live running preservation, stale running interruption, safe retry, unsafe retry escalation.
- Create `src/cccagents/scheduler.py`: project-scoped dispatch validation and same-project write lock decisions.
- Create `tests/test_scheduler.py`: verifies multi-project isolation, same-project write serialization, read-only concurrency, and path validation.
- Create `src/cccagents/pm_notifications.py`: PM notification event model and message formatting for progress, timeout, blocker, approval, completion, and recovery decisions.
- Create `tests/test_pm_notifications.py`: verifies notification text is PM-authored, redacted, and uses expected event types.
- Modify `src/cccagents/paths.py`: add `run_log_dir` helper for `projects/<project_id>/08-logs/hermes-runs/<run_id>/`.
- Modify `tests/test_paths.py`: verify the run log path stays inside the project root.
- Create `scripts/phase4/install_phase4_services.sh`: Linux script that writes service units from rendered templates or documents install commands without secrets.
- Create `scripts/phase4/collect_phase4_evidence.sh`: Linux script to collect redacted service/allowlist/recovery/scheduler/notification evidence.
- Create `docs/phase4/phase4-acceptance.md`: final acceptance checklist template with gates from the spec.

## Task 1: Add Phase 4 service unit contracts

**Files:**
- Create: `src/cccagents/phase4_service.py`
- Create: `tests/test_phase4_service.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_phase4_service.py` with:

```python
from cccagents.phase4_service import build_gateway_service_unit, build_scheduler_service_unit


def test_gateway_service_unit_is_restartable_and_uses_env_file():
    unit = build_gateway_service_unit(
        user="ubuntu",
        working_directory="/home/ubuntu/cccagents-source",
        env_file="/home/ubuntu/.hermes/.env",
    )

    assert "Description=cccagents Hermes Gateway" in unit
    assert "User=ubuntu" in unit
    assert "WorkingDirectory=/home/ubuntu/cccagents-source" in unit
    assert "EnvironmentFile=/home/ubuntu/.hermes/.env" in unit
    assert "ExecStart=/home/ubuntu/.local/bin/hermes gateway run --accept-hooks" in unit
    assert "Restart=always" in unit
    assert "WantedBy=multi-user.target" in unit
    assert "FEISHU_APP_SECRET" not in unit
    assert "ANTHROPIC_API_KEY" not in unit


def test_scheduler_service_unit_is_restartable_and_project_root_bound():
    unit = build_scheduler_service_unit(
        user="ubuntu",
        working_directory="/home/ubuntu/cccagents-source",
        env_file="/home/ubuntu/.hermes/.env",
        project_root="/home/ubuntu/cccagents/projects",
    )

    assert "Description=cccagents PM Scheduler" in unit
    assert "User=ubuntu" in unit
    assert "WorkingDirectory=/home/ubuntu/cccagents-source" in unit
    assert "EnvironmentFile=/home/ubuntu/.hermes/.env" in unit
    assert "Environment=CCCAGENTS_PROJECT_ROOT=/home/ubuntu/cccagents/projects" in unit
    assert "ExecStart=/usr/bin/env python3 -m cccagents.pm_scheduler" in unit
    assert "Restart=always" in unit
    assert "WantedBy=multi-user.target" in unit
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_phase4_service.py
```

Expected: fail with `ModuleNotFoundError: No module named 'cccagents.phase4_service'`.

- [ ] **Step 3: Implement service unit builders**

Create `src/cccagents/phase4_service.py` with:

```python
GATEWAY_SERVICE_NAME = "cccagents-hermes-gateway"
SCHEDULER_SERVICE_NAME = "cccagents-pm-scheduler"


def build_gateway_service_unit(user: str, working_directory: str, env_file: str) -> str:
    return f"""[Unit]
Description=cccagents Hermes Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_directory}
EnvironmentFile={env_file}
ExecStart=/home/ubuntu/.local/bin/hermes gateway run --accept-hooks
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""


def build_scheduler_service_unit(
    user: str,
    working_directory: str,
    env_file: str,
    project_root: str,
) -> str:
    return f"""[Unit]
Description=cccagents PM Scheduler
After=network-online.target cccagents-hermes-gateway.service
Wants=network-online.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_directory}
EnvironmentFile={env_file}
Environment=CCCAGENTS_PROJECT_ROOT={project_root}
ExecStart=/usr/bin/env python3 -m cccagents.pm_scheduler
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
```

- [ ] **Step 4: Run service tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_phase4_service.py
```

Expected: pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/cccagents/phase4_service.py tests/test_phase4_service.py
git commit -m "feat: add phase 4 service unit contracts"
```

## Task 2: Add Feishu allowlist policy

**Files:**
- Create: `src/cccagents/feishu_allowlist.py`
- Create: `tests/test_feishu_allowlist.py`

- [ ] **Step 1: Write failing allowlist tests**

Create `tests/test_feishu_allowlist.py` with:

```python
import pytest

from cccagents.feishu_allowlist import FeishuAllowlist, validate_phase4_allowlist


def test_allows_known_feishu_user():
    allowlist = FeishuAllowlist(allowed_user_ids={"ou_123"}, allow_all_users=False)

    decision = allowlist.decide("ou_123")

    assert decision.allowed is True
    assert decision.reason == "allowed_user"
    assert decision.redacted_user_id == "ou_***"


def test_denies_unknown_feishu_user():
    allowlist = FeishuAllowlist(allowed_user_ids={"ou_123"}, allow_all_users=False)

    decision = allowlist.decide("ou_999")

    assert decision.allowed is False
    assert decision.reason == "user_not_allowlisted"
    assert decision.redacted_user_id == "ou_***"


def test_phase4_rejects_open_allow_all_users():
    allowlist = FeishuAllowlist(allowed_user_ids={"ou_123"}, allow_all_users=True)

    with pytest.raises(ValueError, match="GATEWAY_ALLOW_ALL_USERS is not allowed in Phase 4"):
        validate_phase4_allowlist(allowlist)


def test_phase4_requires_at_least_one_user():
    allowlist = FeishuAllowlist(allowed_user_ids=set(), allow_all_users=False)

    with pytest.raises(ValueError, match="at least one Feishu user"):
        validate_phase4_allowlist(allowlist)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_feishu_allowlist.py
```

Expected: fail with `ModuleNotFoundError: No module named 'cccagents.feishu_allowlist'`.

- [ ] **Step 3: Implement allowlist policy**

Create `src/cccagents/feishu_allowlist.py` with:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class FeishuAllowlistDecision:
    allowed: bool
    reason: str
    redacted_user_id: str


@dataclass(frozen=True)
class FeishuAllowlist:
    allowed_user_ids: set[str]
    allow_all_users: bool = False

    def decide(self, user_id: str) -> FeishuAllowlistDecision:
        redacted_user_id = redact_feishu_user_id(user_id)
        if self.allow_all_users:
            return FeishuAllowlistDecision(True, "open_access", redacted_user_id)
        if user_id in self.allowed_user_ids:
            return FeishuAllowlistDecision(True, "allowed_user", redacted_user_id)
        return FeishuAllowlistDecision(False, "user_not_allowlisted", redacted_user_id)


def redact_feishu_user_id(user_id: str) -> str:
    if user_id.startswith("ou_"):
        return "ou_***"
    if len(user_id) <= 4:
        return "***"
    return f"{user_id[:2]}***"


def validate_phase4_allowlist(allowlist: FeishuAllowlist) -> None:
    if allowlist.allow_all_users:
        raise ValueError("GATEWAY_ALLOW_ALL_USERS is not allowed in Phase 4")
    if not allowlist.allowed_user_ids:
        raise ValueError("Phase 4 requires at least one Feishu user")
```

- [ ] **Step 4: Run allowlist tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_feishu_allowlist.py
```

Expected: pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/cccagents/feishu_allowlist.py tests/test_feishu_allowlist.py
git commit -m "feat: add Feishu allowlist policy"
```

## Task 3: Add run records and restart recovery reconciliation

**Files:**
- Create: `src/cccagents/recovery.py`
- Create: `tests/test_recovery.py`

- [ ] **Step 1: Write failing recovery tests**

Create `tests/test_recovery.py` with:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_recovery.py
```

Expected: fail with `ModuleNotFoundError: No module named 'cccagents.recovery'`.

- [ ] **Step 3: Implement recovery module**

Create `src/cccagents/recovery.py` with:

```python
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
```

- [ ] **Step 4: Run recovery tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_recovery.py
```

Expected: pass.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/cccagents/recovery.py tests/test_recovery.py
git commit -m "feat: add restart recovery reconciliation"
```

## Task 4: Add scheduler dispatch and project lock decisions

**Files:**
- Create: `src/cccagents/scheduler.py`
- Create: `tests/test_scheduler.py`

- [ ] **Step 1: Write failing scheduler tests**

Create `tests/test_scheduler.py` with:

```python
from pathlib import Path

from cccagents.scheduler import DispatchRequest, ProjectLockState, decide_dispatch


def test_allows_project_write_when_no_same_project_lock(tmp_path):
    request = DispatchRequest(
        project_id="project_a",
        cwd=tmp_path / "workspaces" / "project_a" / "repo",
        repo_root=tmp_path,
        permission_level="L1",
        mutates_project=True,
    )
    locks = ProjectLockState(active_write_project_ids=set(), global_running_count=0, global_limit=2)

    decision = decide_dispatch(request, locks)

    assert decision.allowed is True
    assert decision.reason == "dispatch_allowed"


def test_denies_same_project_concurrent_write(tmp_path):
    request = DispatchRequest(
        project_id="project_a",
        cwd=tmp_path / "workspaces" / "project_a" / "repo",
        repo_root=tmp_path,
        permission_level="L1",
        mutates_project=True,
    )
    locks = ProjectLockState(active_write_project_ids={"project_a"}, global_running_count=0, global_limit=2)

    decision = decide_dispatch(request, locks)

    assert decision.allowed is False
    assert decision.reason == "same_project_write_lock"


def test_allows_different_project_write_under_global_limit(tmp_path):
    request = DispatchRequest(
        project_id="project_b",
        cwd=tmp_path / "workspaces" / "project_b" / "repo",
        repo_root=tmp_path,
        permission_level="L1",
        mutates_project=True,
    )
    locks = ProjectLockState(active_write_project_ids={"project_a"}, global_running_count=1, global_limit=2)

    decision = decide_dispatch(request, locks)

    assert decision.allowed is True
    assert decision.reason == "dispatch_allowed"


def test_denies_dispatch_outside_project_scope(tmp_path):
    request = DispatchRequest(
        project_id="project_a",
        cwd=Path("/tmp/outside"),
        repo_root=tmp_path,
        permission_level="L1",
        mutates_project=True,
    )
    locks = ProjectLockState(active_write_project_ids=set(), global_running_count=0, global_limit=2)

    decision = decide_dispatch(request, locks)

    assert decision.allowed is False
    assert decision.reason == "cwd_outside_project"


def test_denies_when_global_limit_reached(tmp_path):
    request = DispatchRequest(
        project_id="project_a",
        cwd=tmp_path / "workspaces" / "project_a" / "repo",
        repo_root=tmp_path,
        permission_level="L0",
        mutates_project=False,
    )
    locks = ProjectLockState(active_write_project_ids=set(), global_running_count=2, global_limit=2)

    decision = decide_dispatch(request, locks)

    assert decision.allowed is False
    assert decision.reason == "global_limit_reached"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_scheduler.py
```

Expected: fail with `ModuleNotFoundError: No module named 'cccagents.scheduler'`.

- [ ] **Step 3: Implement scheduler module**

Create `src/cccagents/scheduler.py` with:

```python
from dataclasses import dataclass
from pathlib import Path

from cccagents.paths import ProjectPaths, assert_within_project


@dataclass(frozen=True)
class DispatchRequest:
    project_id: str
    cwd: Path
    repo_root: Path
    permission_level: str
    mutates_project: bool


@dataclass(frozen=True)
class ProjectLockState:
    active_write_project_ids: set[str]
    global_running_count: int
    global_limit: int


@dataclass(frozen=True)
class DispatchDecision:
    allowed: bool
    reason: str


def decide_dispatch(request: DispatchRequest, locks: ProjectLockState) -> DispatchDecision:
    if locks.global_running_count >= locks.global_limit:
        return DispatchDecision(False, "global_limit_reached")

    project_paths = ProjectPaths(root=request.repo_root, project_id=request.project_id)
    try:
        assert_within_project(request.cwd, project_paths)
    except ValueError:
        return DispatchDecision(False, "cwd_outside_project")

    if request.mutates_project and request.project_id in locks.active_write_project_ids:
        return DispatchDecision(False, "same_project_write_lock")

    return DispatchDecision(True, "dispatch_allowed")
```

- [ ] **Step 4: Run scheduler tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_scheduler.py
```

Expected: pass.

- [ ] **Step 5: Commit Task 4**

```bash
git add src/cccagents/scheduler.py tests/test_scheduler.py
git commit -m "feat: add project scheduler dispatch policy"
```

## Task 5: Add PM notification formatting

**Files:**
- Create: `src/cccagents/pm_notifications.py`
- Create: `tests/test_pm_notifications.py`

- [ ] **Step 1: Write failing notification tests**

Create `tests/test_pm_notifications.py` with:

```python
from cccagents.pm_notifications import PMNotification, format_pm_notification


def test_formats_progress_summary_without_secrets():
    notification = PMNotification(
        project_id="project_1",
        event_type="progress_summary",
        title="Phase 4 progress",
        body="Running recovery smoke with ANTHROPIC_API_KEY=secret-value",
        required_action="none",
        task_id="task_1",
    )

    message = format_pm_notification(notification)

    assert "PM update for project_1" in message
    assert "progress_summary" in message
    assert "ANTHROPIC_API_KEY=[REDACTED]" in message
    assert "secret-value" not in message


def test_formats_restart_recovery_decision():
    notification = PMNotification(
        project_id="project_1",
        event_type="restart_recovery",
        title="Task interrupted after restart",
        body="task_1 requires retry decision",
        required_action="approve_retry_or_stop",
        task_id="task_1",
    )

    message = format_pm_notification(notification)

    assert "Task interrupted after restart" in message
    assert "Required action: approve_retry_or_stop" in message
    assert "Task: task_1" in message


def test_rejects_unknown_event_type():
    notification = PMNotification(
        project_id="project_1",
        event_type="debug_noise",
        title="Debug",
        body="ignore",
        required_action="none",
        task_id=None,
    )

    try:
        format_pm_notification(notification)
    except ValueError as error:
        assert "unsupported PM notification event" in str(error)
    else:
        raise AssertionError("expected unsupported event error")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_pm_notifications.py
```

Expected: fail with `ModuleNotFoundError: No module named 'cccagents.pm_notifications'`.

- [ ] **Step 3: Implement PM notification module**

Create `src/cccagents/pm_notifications.py` with:

```python
from dataclasses import dataclass

from cccagents.redaction import redact_text


SUPPORTED_PM_EVENTS = {
    "progress_summary",
    "soft_timeout",
    "hard_timeout",
    "waiting_timeout",
    "blocked_timeout",
    "approval_request",
    "completion_notice",
    "restart_recovery",
}


@dataclass(frozen=True)
class PMNotification:
    project_id: str
    event_type: str
    title: str
    body: str
    required_action: str
    task_id: str | None


def format_pm_notification(notification: PMNotification) -> str:
    if notification.event_type not in SUPPORTED_PM_EVENTS:
        raise ValueError(f"unsupported PM notification event: {notification.event_type}")

    redacted_body = redact_text(notification.body).text
    lines = [
        f"PM update for {notification.project_id}",
        f"Event: {notification.event_type}",
        f"Title: {notification.title}",
        f"Body: {redacted_body}",
        f"Required action: {notification.required_action}",
    ]
    if notification.task_id:
        lines.append(f"Task: {notification.task_id}")
    return "\n".join(lines)
```

- [ ] **Step 4: Run notification tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_pm_notifications.py
```

Expected: pass.

- [ ] **Step 5: Commit Task 5**

```bash
git add src/cccagents/pm_notifications.py tests/test_pm_notifications.py
git commit -m "feat: add PM notification formatting"
```

## Task 6: Add run log path helper

**Files:**
- Modify: `src/cccagents/paths.py`
- Modify: `tests/test_paths.py`

- [ ] **Step 1: Add failing path test**

Append this test to `tests/test_paths.py`:

```python
def test_run_log_dir_is_inside_project_logs(tmp_path):
    paths = ProjectPaths(root=tmp_path, project_id="demo")

    run_log_dir = paths.run_log_dir("run_123")

    assert run_log_dir == tmp_path / "projects" / "demo" / "08-logs" / "hermes-runs" / "run_123"
    assert_within_project(run_log_dir, paths) == run_log_dir.resolve()
```

- [ ] **Step 2: Run path test to verify failure**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_paths.py::test_run_log_dir_is_inside_project_logs
```

Expected: fail with `AttributeError: 'ProjectPaths' object has no attribute 'run_log_dir'`.

- [ ] **Step 3: Add run log helper**

Modify `src/cccagents/paths.py` by adding this method inside `ProjectPaths` after `command_log`:

```python
    def run_log_dir(self, run_id: str) -> Path:
        return self.project_root / "08-logs" / "hermes-runs" / run_id
```

- [ ] **Step 4: Run path tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_paths.py
```

Expected: pass.

- [ ] **Step 5: Commit Task 6**

```bash
git add src/cccagents/paths.py tests/test_paths.py
git commit -m "feat: add Hermes run log path helper"
```

## Task 7: Add Phase 4 Linux scripts and acceptance template

**Files:**
- Create: `scripts/phase4/install_phase4_services.sh`
- Create: `scripts/phase4/collect_phase4_evidence.sh`
- Create: `docs/phase4/phase4-acceptance.md`

- [ ] **Step 1: Create service install script**

Create `scripts/phase4/install_phase4_services.sh` with:

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_SOURCE="${PROJECT_SOURCE:-/home/ubuntu/cccagents-source}"
PROJECT_ROOT="${PROJECT_ROOT:-/home/ubuntu/cccagents/projects}"
HERMES_ENV="${HERMES_ENV:-/home/ubuntu/.hermes/.env}"
RUN_USER="${RUN_USER:-ubuntu}"
UNIT_DIR="${UNIT_DIR:-/tmp/cccagents-systemd-units}"

mkdir -p "$UNIT_DIR"

cat > "$UNIT_DIR/cccagents-hermes-gateway.service" <<EOF
[Unit]
Description=cccagents Hermes Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$PROJECT_SOURCE
EnvironmentFile=$HERMES_ENV
ExecStart=/home/ubuntu/.local/bin/hermes gateway run --accept-hooks
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > "$UNIT_DIR/cccagents-pm-scheduler.service" <<EOF
[Unit]
Description=cccagents PM Scheduler
After=network-online.target cccagents-hermes-gateway.service
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$PROJECT_SOURCE
EnvironmentFile=$HERMES_ENV
Environment=CCCAGENTS_PROJECT_ROOT=$PROJECT_ROOT
ExecStart=/usr/bin/env python3 -m cccagents.pm_scheduler
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

printf 'unit_dir=%s\n' "$UNIT_DIR"
printf 'gateway_unit=%s\n' "$UNIT_DIR/cccagents-hermes-gateway.service"
printf 'scheduler_unit=%s\n' "$UNIT_DIR/cccagents-pm-scheduler.service"
printf 'install_hint=review units, then copy to /etc/systemd/system and run systemctl daemon-reload enable --now\n'
```

- [ ] **Step 2: Create evidence collection script**

Create `scripts/phase4/collect_phase4_evidence.sh` with:

```bash
#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${1:-docs/phase4/linux-ops}"
mkdir -p "$OUTPUT_DIR"

{
  date -u +%Y-%m-%dT%H:%M:%SZ
  systemctl is-enabled cccagents-hermes-gateway 2>/dev/null || true
  systemctl is-active cccagents-hermes-gateway 2>/dev/null || true
  systemctl is-enabled cccagents-pm-scheduler 2>/dev/null || true
  systemctl is-active cccagents-pm-scheduler 2>/dev/null || true
} > "$OUTPUT_DIR/service-install.log"

{
  date -u +%Y-%m-%dT%H:%M:%SZ
  if [ -f /home/ubuntu/.hermes/.env ]; then
    grep -E 'GATEWAY_ALLOW_ALL_USERS|FEISHU' /home/ubuntu/.hermes/.env | sed -E 's/(FEISHU_[A-Z_]+=).*/\1[REDACTED]/; s/(ou_)[A-Za-z0-9_-]+/\1[REDACTED]/g'
  else
    printf 'hermes_env=missing\n'
  fi
} > "$OUTPUT_DIR/allowlist-check.log"

for name in restart-recovery multi-project-scheduler pm-notification; do
  {
    date -u +%Y-%m-%dT%H:%M:%SZ
    printf '%s evidence pending live smoke\n' "$name"
  } > "$OUTPUT_DIR/$name.log"
done
```

- [ ] **Step 3: Create acceptance template**

Create `docs/phase4/phase4-acceptance.md` with:

```markdown
# Phase 4 Acceptance

Date: 2026-05-20

## Gate Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Hermes Gateway/worker durable service | pending | `docs/phase4/linux-ops/service-install.log` |
| Feishu allowlist replaces open access | pending | `docs/phase4/linux-ops/allowlist-check.log` |
| PM-only Feishu boundary preserved | pending | tests and Feishu contract evidence |
| Hermes/server restart recovery | pending | `docs/phase4/linux-ops/restart-recovery.log` |
| Interrupted task handling | pending | recovery tests and Linux evidence |
| Multi-project isolation | pending | `docs/phase4/linux-ops/multi-project-scheduler.log` |
| Same-project write lock | pending | scheduler tests |
| PM notifications | pending | `docs/phase4/linux-ops/pm-notification.log` |
| Approval safety | pending | command policy tests |
| Secret safety | pending | grep verification |
| Local tests | pending | pytest output |
| Linux evidence | pending | `docs/phase4/linux-ops/` |

## Decision

Pending Phase 4 implementation and Linux smoke verification.
```

- [ ] **Step 4: Make scripts executable**

Run:

```bash
chmod +x scripts/phase4/install_phase4_services.sh scripts/phase4/collect_phase4_evidence.sh
```

Expected: command exits 0.

- [ ] **Step 5: Commit Task 7**

```bash
git add scripts/phase4/install_phase4_services.sh scripts/phase4/collect_phase4_evidence.sh docs/phase4/phase4-acceptance.md
git commit -m "docs: add phase 4 Linux evidence scripts"
```

## Task 8: Run full verification and update acceptance evidence

**Files:**
- Modify: `docs/phase4/phase4-acceptance.md`

- [ ] **Step 1: Run full local test suite**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run repository secret scan**

Run:

```bash
grep -R "FEISHU_APP_SECRET=.*[A-Za-z0-9]\|FEISHU_VERIFICATION_TOKEN=.*[A-Za-z0-9]\|FEISHU_ENCRYPT_KEY=.*[A-Za-z0-9]\|sk-\|ANTHROPIC_API_KEY=.*[A-Za-z0-9]" docs src tests hermes scripts || true
```

Expected: no real secret values. Redacted placeholders such as `[REDACTED]` are acceptable.

- [ ] **Step 3: Update acceptance local evidence**

Modify `docs/phase4/phase4-acceptance.md` so local test and contract gates show `pass` after verification:

```markdown
| PM-only Feishu boundary preserved | pass | Feishu contract tests |
| Interrupted task handling | pass | recovery tests |
| Same-project write lock | pass | scheduler tests |
| PM notifications | pass | PM notification tests |
| Approval safety | pass | command policy tests |
| Secret safety | pass | grep verification |
| Local tests | pass | pytest output |
```

Keep Linux smoke gates as `pending` until real Linux service/restart verification is complete.

- [ ] **Step 4: Commit verification update**

```bash
git add docs/phase4/phase4-acceptance.md
git commit -m "docs: update phase 4 local acceptance evidence"
```

## Self-Review Notes

Spec coverage:

- Durable service: Task 1 and Task 7.
- Feishu allowlist: Task 2 and Task 7.
- Restart recovery: Task 3 and Task 8.
- Multi-project isolation and write locks: Task 4 and Task 6.
- PM notifications: Task 5.
- Redacted evidence and acceptance: Task 7 and Task 8.
- Local tests and secret scan: Task 8.

Placeholder scan: no unfinished implementation markers or undefined implementation steps are intentionally left in the plan. Linux live smoke gates remain explicitly `pending` until execution evidence exists.

Type consistency: `TaskStatus`, `ProjectPaths`, and helper names used across tasks match the existing code or are introduced before use.
