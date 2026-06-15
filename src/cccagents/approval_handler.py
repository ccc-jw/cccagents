from dataclasses import dataclass
from pathlib import Path

from cccagents.feishu_contracts import FeishuApprovalAction, FeishuSecurityContext, validate_approval_action
from cccagents.project_state import ProjectState, load_project_state, save_project_state


@dataclass(frozen=True)
class ApprovalRequest:
    project_id: str
    approval_id: str
    action: str
    feishu_user_id: str
    feishu_message_id: str
    timestamp: int
    signature: str
    comment: str | None = None


@dataclass(frozen=True)
class ApprovalResult:
    project_id: str
    approval_id: str
    action: str
    approved: bool
    reason: str
    processed_at: str


def process_approval_action(
    request: ApprovalRequest,
    context: FeishuSecurityContext,
    project_dir: Path,
    now: str,
) -> ApprovalResult:
    """Process a Feishu approval action and update project state."""
    action = FeishuApprovalAction(
        project_id=request.project_id,
        approval_id=request.approval_id,
        action=request.action,
        feishu_user_id=request.feishu_user_id,
        feishu_message_id=request.feishu_message_id,
        timestamp=request.timestamp,
        signature=request.signature,
    )

    decision = validate_approval_action(action, context)

    if not decision.allowed:
        return ApprovalResult(
            project_id=request.project_id,
            approval_id=request.approval_id,
            action=request.action,
            approved=False,
            reason=decision.reason,
            processed_at=now,
        )

    state = load_project_state(project_dir)

    if request.action == "approve":
        updated_state = ProjectState(
            project_id=state.project_id,
            source=state.source,
            status="approved",
            complexity=state.complexity,
            current_phase="APPROVED",
            required_roles=state.required_roles,
            risk_flags=state.risk_flags,
            approval_policy=state.approval_policy,
            retry_count_by_phase=state.retry_count_by_phase,
            created_at=state.created_at,
            updated_at=now,
            last_pm_notification_at=now,
        )
        save_project_state(project_dir, updated_state)
        return ApprovalResult(
            project_id=request.project_id,
            approval_id=request.approval_id,
            action=request.action,
            approved=True,
            reason="approved",
            processed_at=now,
        )

    if request.action == "reject":
        updated_state = ProjectState(
            project_id=state.project_id,
            source=state.source,
            status="rejected",
            complexity=state.complexity,
            current_phase="REJECTED",
            required_roles=state.required_roles,
            risk_flags=state.risk_flags,
            approval_policy=state.approval_policy,
            retry_count_by_phase=state.retry_count_by_phase,
            created_at=state.created_at,
            updated_at=now,
            last_pm_notification_at=now,
        )
        save_project_state(project_dir, updated_state)
        return ApprovalResult(
            project_id=request.project_id,
            approval_id=request.approval_id,
            action=request.action,
            approved=False,
            reason="rejected",
            processed_at=now,
        )

    if request.action == "pause_project":
        updated_state = ProjectState(
            project_id=state.project_id,
            source=state.source,
            status="paused",
            complexity=state.complexity,
            current_phase=state.current_phase,
            required_roles=state.required_roles,
            risk_flags=state.risk_flags,
            approval_policy=state.approval_policy,
            retry_count_by_phase=state.retry_count_by_phase,
            created_at=state.created_at,
            updated_at=now,
            last_pm_notification_at=now,
        )
        save_project_state(project_dir, updated_state)
        return ApprovalResult(
            project_id=request.project_id,
            approval_id=request.approval_id,
            action=request.action,
            approved=True,
            reason="paused",
            processed_at=now,
        )

    if request.action == "resume_project":
        updated_state = ProjectState(
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
        )
        save_project_state(project_dir, updated_state)
        return ApprovalResult(
            project_id=request.project_id,
            approval_id=request.approval_id,
            action=request.action,
            approved=True,
            reason="resumed",
            processed_at=now,
        )

    return ApprovalResult(
        project_id=request.project_id,
        approval_id=request.approval_id,
        action=request.action,
        approved=False,
        reason="unsupported_action",
        processed_at=now,
    )
