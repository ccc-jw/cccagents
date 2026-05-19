# cccagents Phase 4 Long-running Async Operation Design

Date: 2026-05-20

## Goal

Phase 4 upgrades the proven real Feishu + Hermes + Claude Code CLI smoke path into a durable long-running async operation model. The system must support cross-hour and cross-day project execution on Linux without requiring the user to keep a Mac terminal open.

Feishu remains the only user entry and notification channel. PM remains the only user-facing Hermes Agent. Hermes owns project state, task routing, recovery, reminders, and approvals. Claude Code CLI remains the code and document execution engine, launched per task with narrow permissions.

## Scope

In scope:

- Run Hermes Gateway and worker/scheduler as durable Linux services.
- Replace temporary open Feishu access with a user allowlist.
- Recover tasks automatically after Hermes restart or server restart.
- Detect interrupted, stale, blocked, waiting, failed, and completed tasks.
- Support multiple `project_id` values with isolated workspaces, state, artifacts, and logs.
- Prevent concurrent writes inside the same project workspace.
- Send PM progress summaries, timeout reminders, blocker notices, approval requests, and completion notices through Feishu.
- Keep redacted Linux operation evidence for each Phase 4 verification.

Out of scope:

- Replacing Claude Code CLI with another executor.
- Letting Feishu users talk directly to PDM, RES, ARCH, DEV, TEST, or SEC.
- Public production deployment automation beyond the Linux service model.
- Complex organization-wide approval matrices.
- Changing the Phase 2 role contracts or Phase 3 Feishu PM-only contract.

## Recommended Delivery Path

Phase 4 uses full design with staged delivery:

```text
4A Service and allowlist hardening
4B Restart recovery and task reconciliation
4C Multi-project scheduling and project write locks
4D PM progress, timeout, blocker, approval, and completion notifications
```

This keeps the target architecture coherent while avoiding one large implementation step.

## Architecture

```text
Feishu user
  -> Hermes Gateway Service
  -> PM Agent / PM Scheduler
  -> Task Runner / Executor Adapter
  -> Claude Code CLI per-task session
  -> project workspace, artifacts, and logs
  -> PM Scheduler reconciliation
  -> Feishu notification or approval request
```

Core components:

1. **Gateway Service**
   - Runs Hermes Feishu Gateway as a durable Linux service.
   - Receives Feishu messages through the proven websocket mode.
   - Routes all user messages only to PM.

2. **PM Scheduler**
   - Periodically scans project state and task status.
   - Dispatches eligible tasks.
   - Reconciles stale `running` tasks against run locks and process state.
   - Sends progress, timeout, blocker, approval, and completion messages through PM.

3. **Task Runner / Executor Adapter**
   - Starts one Claude Code CLI process per task.
   - Binds every execution to `project_id`, `task_id`, `run_id`, `agent_role`, `cwd`, `allowed_tools`, and permission level.
   - Writes command logs and run logs before and after execution.
   - Uses narrow permissions such as `--allowedTools Read,Write` for local write tasks.
   - Does not use `--dangerously-skip-permissions` by default.

4. **Project State Store**
   - Stores project-local state and artifacts under `projects/<project_id>/`.
   - Stores working repos under `workspaces/<project_id>/repo/`.
   - Keeps each project independently recoverable.

5. **Notification and Approval Bridge**
   - Sends only PM-authored user-facing messages through Feishu.
   - Requires approval for L2/L3, deletion, force, deploy, external sharing, and production-impacting actions.

## Linux Service Model

Phase 4 should install durable service units or an equivalent supervised runner for:

```text
cccagents-hermes-gateway
cccagents-pm-scheduler
```

Minimum service behavior:

- Start automatically after server boot.
- Restart automatically after process failure.
- Load secrets from Linux-only secret/config files.
- Write stdout/stderr to Linux service logs and project-level redacted logs.
- Never write real secrets to repository evidence.

Secrets remain only on Linux, for example:

```text
/home/ubuntu/.hermes/.env
```

Repository evidence may contain only names and redacted values.

## Feishu Allowlist

Phase 3.5 used:

```text
GATEWAY_ALLOW_ALL_USERS=true
```

Phase 4 must replace it with a Feishu user allowlist before production-like use. The allowlist should include only confirmed Feishu user ids, such as the observed `ou_...` user id from redacted smoke logs.

Required rules:

- Unknown Feishu users are denied before reaching PM task creation.
- Denied events are logged with redacted user identifiers.
- Feishu user messages still route only to PM.
- Allowlist configuration stays on Linux and is recorded in repository evidence only as redacted names/shape.

## Task State and Recovery

Task recovery is status-driven:

| Status | Recovery behavior |
| --- | --- |
| `pending` | Eligible for dispatch when dependencies and project lock allow it. |
| `running` with live run lock/process | Keep running; update heartbeat only. |
| `running` without live run lock/process | Mark `interrupted`, preserve run evidence, and let PM decide retry or user notification. |
| `interrupted` with safe retry policy | PM Scheduler may retry automatically if the task is idempotent and no partial write risk exists. |
| `interrupted` without safe retry policy | PM notifies user or asks for approval before retrying. |
| `waiting_user` | Continue waiting for Feishu input or approval; do not auto-approve. |
| `blocked` | Keep blocked and summarize blocker to PM/user when reminder policy triggers. |
| `failed` | Preserve failure logs; create or propose a fix task. |
| `completed` | Do not re-run; advance only if downstream state requires it. |

Each run writes enough recovery evidence to decide the next action:

```text
project_id
task_id
run_id
agent_role
cwd
allowed_tools
permission_level
started_at
heartbeat_at
completed_at
exit_code
status_before
status_after
stdout_path
stderr_path
artifact_paths
redacted
```

## Hermes or Server Restart Recovery

Hermes restart and full server restart are explicit acceptance cases.

After restart:

1. Gateway Service and PM Scheduler start automatically.
2. PM Scheduler loads all active project state from `projects/<project_id>/`.
3. Scheduler scans task records and run logs.
4. Scheduler checks run locks, heartbeat timestamps, and process state.
5. Scheduler resumes safe `pending` tasks.
6. Scheduler keeps valid live `running` tasks if their process still exists.
7. Scheduler marks stale `running` tasks as `interrupted` when their process or heartbeat is gone.
8. Scheduler automatically retries only tasks declared safe and idempotent.
9. Scheduler sends Feishu PM notifications for tasks needing user/PM decision.

A task is safe for automatic retry only when all conditions are true:

- The task is L0 or allowed L1.
- The task is idempotent or has no partial write risk.
- The workspace path is inside the bound `project_id`.
- The previous run did not record a destructive, external, L2, or L3 action.
- No same-project write lock is currently held.

Tasks that do not meet these conditions must not be silently retried. They become `interrupted` or `waiting_user`, and PM notifies the user through Feishu.

## Multi-project Scheduling

Project isolation is mandatory because the Linux host may run multiple projects.

Required boundaries:

```text
workspaces/<project_id>/repo/
projects/<project_id>/
projects/<project_id>/08-logs/command-log.jsonl
projects/<project_id>/08-logs/hermes-runs/<run_id>/
```

Scheduling rules:

- Different projects may run concurrently up to a global concurrency limit.
- Same project write tasks are serialized by a project write lock.
- Same project read-only tasks may run concurrently when they cannot mutate workspace or project artifacts.
- Every task dispatch validates that `cwd` is inside the matching project workspace or project artifact directory.
- A task cannot write logs or artifacts outside its own `project_id` directory.
- Cross-project operations require explicit PM/user approval and should be treated as L3 unless proven harmless.

## Timeout and Reminder Policy

Timeouts should inform PM decisions without interrupting safe work unnecessarily.

- **Soft timeout**: task exceeds expected duration. PM sends a progress summary or records a risk note, but does not stop the task.
- **Hard timeout**: task exceeds maximum duration. PM marks the task risky and asks for a stop/retry/continue decision unless the task policy allows automatic handling.
- **Waiting timeout**: `waiting_user` has no Feishu response for a configured interval. PM sends reminders but does not auto-approve.
- **Blocked timeout**: blocker remains unresolved beyond threshold. PM summarizes blocker, owner, and next required decision.

Notification cadence must avoid spam. PM should aggregate routine progress, but immediately notify for approval needs, hard timeouts, restart recovery requiring a decision, and repeated failures.

## Permission and Approval Rules

Permission levels remain:

```text
L0 read-only
L1 local write/test
L2 project-level change
L3 external/shared/destructive action
```

Automation boundary:

- L0 may be automatic.
- Allowed, non-destructive L1 may be automatic.
- L2 requires PM/user approval.
- L3 requires PM/user approval.
- Delete, overwrite, force, deploy, dependency install, shared infrastructure, external publish, or production-impacting actions require approval even if requested by an agent.

The executor must record policy decisions with `permission_level`, `policy_decision`, `risk_reason`, and `approval_id` when applicable.

## Redaction and Evidence

Phase 4 evidence must be useful for recovery and review without leaking secrets.

Required redaction rules:

- No real Feishu secret values in repository files.
- No real API keys in prompts, logs, artifacts, or Feishu messages.
- No Authorization headers in saved evidence.
- Redacted logs must preserve structure, timestamps, task ids, run ids, and status transitions.
- If a log line is redacted, record `redacted=true` and a reason when possible.

Required evidence files should include:

```text
docs/phase4/linux-ops/service-install.log
docs/phase4/linux-ops/allowlist-check.log
docs/phase4/linux-ops/restart-recovery.log
docs/phase4/linux-ops/multi-project-scheduler.log
docs/phase4/linux-ops/pm-notification.log
docs/phase4/phase4-acceptance.md
```

## Acceptance Gates

| Gate | Required Result |
| --- | --- |
| Hermes Gateway/worker durable service | Services start automatically and restart after process failure. |
| Feishu allowlist | `GATEWAY_ALLOW_ALL_USERS=true` is replaced by a confirmed Feishu user allowlist. |
| PM-only Feishu boundary | Feishu messages only enter PM; no direct user route to PDM/RES/ARCH/DEV/TEST/SEC. |
| Hermes/server restart recovery | After Hermes restart or server reboot, tasks are automatically reconciled and safe tasks resume. |
| Interrupted task handling | Stale `running` tasks become `interrupted` with preserved run evidence and PM/user decision path. |
| Multi-project isolation | Two `project_id` values do not share workspace, state, artifacts, command logs, or run logs. |
| Same-project write lock | Same project write tasks do not run concurrently and cannot overwrite each other. |
| PM notifications | PM sends Feishu progress summaries, timeout reminders, blocker notices, approval requests, and completion notices. |
| Approval safety | L2/L3, destructive, external, deploy, force, and production-impacting actions require approval. |
| Secret safety | Repository evidence and project artifacts contain no real API keys, Feishu secrets, or Authorization headers. |
| Local tests | Python tests pass locally with `PYTHONPATH=src .venv/bin/pytest -q`. |
| Linux evidence | Redacted Linux service, recovery, scheduler, and notification logs are saved. |

## Open Decisions for Implementation Plan

- Whether to use systemd units, tmux-supervised scripts, or both for the first durable runner.
- Exact scheduler interval and timeout thresholds.
- Exact on-disk task state format if current helper models are not enough.
- Whether automatic retry is initially limited to L0/read-only tasks or includes selected L1 writes.
- How much PM notification formatting should be implemented in Hermes configuration versus project helper code.

## Conclusion

Phase 4 should first harden the proven Feishu websocket path into a durable Linux service, then add restart recovery, multi-project scheduling, and PM notification policy. The highest-priority production safety changes are replacing open Feishu access, preserving project isolation, and making Hermes/server restart recovery explicit and testable.
