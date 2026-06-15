from pathlib import Path

from cccagents.approval_handler import ApprovalRequest, process_approval_action
from cccagents.feishu_contracts import FeishuSecurityContext
from cccagents.project_state import ProjectState, save_project_state


def test_approve_action_updates_project_state(tmp_path):
    project_dir = tmp_path / "demo-approve"
    project_dir.mkdir(parents=True, exist_ok=True)

    initial_state = ProjectState(
        project_id="demo-approve",
        source="feishu",
        status="pending_approval",
        complexity="S3",
        current_phase="FEISHU_USER_APPROVAL",
        required_roles=["PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC"],
        risk_flags=["security_sensitive"],
        approval_policy="manual_approval_required",
        retry_count_by_phase={},
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
        last_pm_notification_at="2026-06-15T10:00:00Z",
    )
    save_project_state(project_dir, initial_state)

    request = ApprovalRequest(
        project_id="demo-approve",
        approval_id="approval-001",
        action="approve",
        feishu_user_id="user-1",
        feishu_message_id="msg-001",
        timestamp=1_700_000_000,
        signature="valid-sig",
    )

    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids=set(),
        now=1_700_000_000,
        timestamp_window_seconds=300,
        expected_signature="valid-sig",
    )

    result = process_approval_action(request, context, project_dir, now="2026-06-15T10:01:00Z")

    assert result.approved is True
    assert result.action == "approve"

    from cccagents.project_state import load_project_state
    state = load_project_state(project_dir)
    assert state.status == "approved"
    assert state.current_phase == "APPROVED"


def test_reject_action_updates_project_state(tmp_path):
    project_dir = tmp_path / "demo-reject"
    project_dir.mkdir(parents=True, exist_ok=True)

    initial_state = ProjectState(
        project_id="demo-reject",
        source="feishu",
        status="pending_approval",
        complexity="S3",
        current_phase="FEISHU_USER_APPROVAL",
        required_roles=["PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC"],
        risk_flags=["security_sensitive"],
        approval_policy="manual_approval_required",
        retry_count_by_phase={},
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
        last_pm_notification_at="2026-06-15T10:00:00Z",
    )
    save_project_state(project_dir, initial_state)

    request = ApprovalRequest(
        project_id="demo-reject",
        approval_id="approval-002",
        action="reject",
        feishu_user_id="user-1",
        feishu_message_id="msg-002",
        timestamp=1_700_000_000,
        signature="valid-sig",
    )

    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids=set(),
        now=1_700_000_000,
        timestamp_window_seconds=300,
        expected_signature="valid-sig",
    )

    result = process_approval_action(request, context, project_dir, now="2026-06-15T10:01:00Z")

    assert result.approved is False
    assert result.action == "reject"

    from cccagents.project_state import load_project_state
    state = load_project_state(project_dir)
    assert state.status == "rejected"


def test_pause_and_resume_actions(tmp_path):
    project_dir = tmp_path / "demo-pause"
    project_dir.mkdir(parents=True, exist_ok=True)

    initial_state = ProjectState(
        project_id="demo-pause",
        source="feishu",
        status="running",
        complexity="S2",
        current_phase="DEVELOPMENT",
        required_roles=["PM", "PDM", "ARCH", "DEV", "TEST"],
        risk_flags=["feature_change"],
        approval_policy="auto_if_l0_l1_and_all_reviews_pass",
        retry_count_by_phase={},
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
        last_pm_notification_at="2026-06-15T10:00:00Z",
    )
    save_project_state(project_dir, initial_state)

    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids=set(),
        now=1_700_000_000,
        timestamp_window_seconds=300,
        expected_signature="valid-sig",
    )

    pause_request = ApprovalRequest(
        project_id="demo-pause",
        approval_id="approval-003",
        action="pause_project",
        feishu_user_id="user-1",
        feishu_message_id="msg-003",
        timestamp=1_700_000_000,
        signature="valid-sig",
    )

    pause_result = process_approval_action(pause_request, context, project_dir, now="2026-06-15T10:01:00Z")
    assert pause_result.approved is True
    assert pause_result.reason == "paused"

    from cccagents.project_state import load_project_state
    state = load_project_state(project_dir)
    assert state.status == "paused"

    resume_request = ApprovalRequest(
        project_id="demo-pause",
        approval_id="approval-004",
        action="resume_project",
        feishu_user_id="user-1",
        feishu_message_id="msg-004",
        timestamp=1_700_000_100,
        signature="valid-sig",
    )

    resume_result = process_approval_action(resume_request, context, project_dir, now="2026-06-15T10:02:00Z")
    assert resume_result.approved is True
    assert resume_result.reason == "resumed"

    state = load_project_state(project_dir)
    assert state.status == "running"


def test_invalid_signature_is_rejected(tmp_path):
    project_dir = tmp_path / "demo-invalid"
    project_dir.mkdir(parents=True, exist_ok=True)

    initial_state = ProjectState(
        project_id="demo-invalid",
        source="feishu",
        status="pending_approval",
        complexity="S3",
        current_phase="FEISHU_USER_APPROVAL",
        required_roles=["PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC"],
        risk_flags=["security_sensitive"],
        approval_policy="manual_approval_required",
        retry_count_by_phase={},
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
        last_pm_notification_at="2026-06-15T10:00:00Z",
    )
    save_project_state(project_dir, initial_state)

    request = ApprovalRequest(
        project_id="demo-invalid",
        approval_id="approval-005",
        action="approve",
        feishu_user_id="user-1",
        feishu_message_id="msg-005",
        timestamp=1_700_000_000,
        signature="invalid-sig",
    )

    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids=set(),
        now=1_700_000_000,
        timestamp_window_seconds=300,
        expected_signature="valid-sig",
    )

    result = process_approval_action(request, context, project_dir, now="2026-06-15T10:01:00Z")

    assert result.approved is False
    assert result.reason == "invalid_signature"
