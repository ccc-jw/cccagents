import json
from dataclasses import asdict
from pathlib import Path

from cccagents.approval_handler import ApprovalRequest, process_approval_action
from cccagents.complexity_classifier import classify_project_request
from cccagents.feishu_contracts import FeishuSecurityContext
from cccagents.orchestrator import FakeExecutor, OrchestrationRequest, orchestrate_request
from cccagents.project_state import ProjectState, load_project_state, save_project_state
from cccagents.recovery import reconcile_task_after_restart
from cccagents.role_plan import build_role_plan


def orchestrate_project(
    project_dir: Path,
    request: OrchestrationRequest,
    executor: FakeExecutor,
    now: str,
) -> dict:
    """Orchestrate a project with recovery and approval handling."""
    project_dir.mkdir(parents=True, exist_ok=True)

    state_path = project_dir / "project-state.json"
    if state_path.exists():
        state = load_project_state(project_dir)
        if state.status in ("approved", "done"):
            return {"status": state.status, "message": "project already completed"}
        if state.status == "paused":
            return {"status": "paused", "message": "project is paused"}
        if state.status == "rejected":
            return {"status": "rejected", "message": "project was rejected"}

    decision = classify_project_request(request.text)

    if _requires_approval(decision.complexity, decision.risk_flags):
        _save_pending_approval_state(project_dir, request, decision, now)
        return {
            "status": "pending_approval",
            "project_id": request.project_id,
            "complexity": decision.complexity,
            "message": "project requires Feishu user approval",
        }

    result = orchestrate_request(request, executor)

    return {
        "status": result.status,
        "project_id": request.project_id,
        "complexity": result.complexity,
        "executed_roles": result.executed_roles,
        "issues": result.issues,
    }


def _requires_approval(complexity: str, issues: list[str]) -> bool:
    """Determine if a project requires manual approval."""
    if complexity == "S3":
        return True
    if any("security" in issue.lower() for issue in issues):
        return True
    return False


def _save_pending_approval_state(
    project_dir: Path,
    request: OrchestrationRequest,
    result: dict,
    now: str,
) -> None:
    """Save project state as pending approval."""
    decision = classify_project_request(request.text)
    plan = build_role_plan(decision)

    save_project_state(
        project_dir,
        ProjectState(
            project_id=request.project_id,
            source="feishu",
            status="pending_approval",
            complexity=result.complexity,
            current_phase="FEISHU_USER_APPROVAL",
            required_roles=decision.required_roles,
            risk_flags=decision.risk_flags,
            approval_policy="manual_approval_required",
            retry_count_by_phase={},
            created_at=now,
            updated_at=now,
            last_pm_notification_at=now,
        ),
    )

    (project_dir / "role-plan.json").write_text(
        json.dumps(asdict(plan), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def reconcile_and_orchestrate(
    project_dir: Path,
    request: OrchestrationRequest,
    executor: FakeExecutor,
    now: str,
) -> dict:
    """Reconcile interrupted tasks and continue orchestration."""
    project_dir.mkdir(parents=True, exist_ok=True)

    state_path = project_dir / "project-state.json"
    if not state_path.exists():
        return orchestrate_project(project_dir, request, executor, now)

    state = load_project_state(project_dir)

    if state.status == "interrupted":
        recovery_log = project_dir / "08-logs" / "restart-recovery.jsonl"
        recovery_log.parent.mkdir(parents=True, exist_ok=True)
        with recovery_log.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "project_id": state.project_id,
                        "action": "reconcile_interrupted",
                        "timestamp": now,
                    }
                )
                + "\n"
            )

        if _is_safe_for_auto_retry(state):
            save_project_state(
                project_dir,
                ProjectState(
                    project_id=state.project_id,
                    source=state.source,
                    status="running",
                    complexity=state.complexity,
                    current_phase=state.current_phase,
                    required_roles=state.required_roles,
                    risk_flags=state.risk_flags,
                    approval_policy=state.approval_policy,
                    retry_count_by_phase=state.retry_count_by_phase,
                    created_at=state.created_at,
                    updated_at=now,
                    last_pm_notification_at=now,
                ),
            )
            return orchestrate_project(project_dir, request, executor, now)
        else:
            return {
                "status": "interrupted",
                "project_id": state.project_id,
                "message": "project requires manual decision after restart",
            }

    return orchestrate_project(project_dir, request, executor, now)


def _is_safe_for_auto_retry(state: ProjectState) -> bool:
    """Determine if a project can be auto-retried after restart."""
    if state.complexity == "S3":
        return False
    if any(flag in state.risk_flags for flag in ["security_sensitive", "external_side_effect"]):
        return False
    retry_count = state.retry_count_by_phase.get(state.current_phase, 0)
    return retry_count < 2
