from pathlib import Path

from cccagents.approval_handler import ApprovalRequest, process_approval_action
from cccagents.feishu_contracts import FeishuSecurityContext
from cccagents.orchestrator import FakeExecutor, OrchestrationRequest
from cccagents.project_orchestrator import orchestrate_project
from cccagents.project_state import load_project_state


def test_full_s3_approval_flow(tmp_path):
    """Test complete S3 flow: orchestrate -> pending_approval -> approve -> done."""
    project_dir = tmp_path / "demo-s3-flow"
    request = OrchestrationRequest(
        project_id="demo-s3-flow",
        text="修改认证权限并部署到生产，涉及 FEISHU_APP_SECRET 配置",
        project_root=tmp_path,
        now="2026-06-15T10:00:00Z",
    )

    result = orchestrate_project(project_dir, request, FakeExecutor(), now="2026-06-15T10:00:00Z")

    assert result["status"] == "pending_approval"
    assert result["complexity"] == "S3"

    state = load_project_state(project_dir)
    assert state.status == "pending_approval"
    assert state.current_phase == "FEISHU_USER_APPROVAL"

    approval_request = ApprovalRequest(
        project_id="demo-s3-flow",
        approval_id="approval-flow-001",
        action="approve",
        feishu_user_id="user-1",
        feishu_message_id="msg-flow-001",
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

    approval_result = process_approval_action(
        approval_request, context, project_dir, now="2026-06-15T10:05:00Z"
    )

    assert approval_result.approved is True
    assert approval_result.action == "approve"

    state = load_project_state(project_dir)
    assert state.status == "approved"
    assert state.current_phase == "APPROVED"


def test_full_s3_rejection_flow(tmp_path):
    """Test complete S3 flow with rejection."""
    project_dir = tmp_path / "demo-s3-reject-flow"
    request = OrchestrationRequest(
        project_id="demo-s3-reject-flow",
        text="修改认证权限并部署到生产",
        project_root=tmp_path,
        now="2026-06-15T10:00:00Z",
    )

    result = orchestrate_project(project_dir, request, FakeExecutor(), now="2026-06-15T10:00:00Z")

    assert result["status"] == "pending_approval"

    rejection_request = ApprovalRequest(
        project_id="demo-s3-reject-flow",
        approval_id="approval-reject-001",
        action="reject",
        feishu_user_id="user-1",
        feishu_message_id="msg-reject-001",
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

    rejection_result = process_approval_action(
        rejection_request, context, project_dir, now="2026-06-15T10:05:00Z"
    )

    assert rejection_result.approved is False
    assert rejection_result.action == "reject"

    state = load_project_state(project_dir)
    assert state.status == "rejected"
    assert state.current_phase == "REJECTED"


def test_s0_completes_without_approval(tmp_path):
    """Test that S0 completes without requiring approval."""
    project_dir = tmp_path / "demo-s0-no-approval"
    request = OrchestrationRequest(
        project_id="demo-s0-no-approval",
        text="修复 README 里的 typo",
        project_root=tmp_path,
        now="2026-06-15T10:00:00Z",
    )

    result = orchestrate_project(project_dir, request, FakeExecutor(), now="2026-06-15T10:00:00Z")

    assert result["status"] == "done"
    assert result["complexity"] == "S0"

    state = load_project_state(project_dir)
    assert state.status == "done"
    assert state.current_phase == "DONE"


def test_s1_completes_without_approval(tmp_path):
    """Test that S1 completes without requiring approval."""
    project_dir = tmp_path / "demo-s1-no-approval"
    request = OrchestrationRequest(
        project_id="demo-s1-no-approval",
        text="修复登录按钮 loading 的局部 bug，并跑本地测试",
        project_root=tmp_path,
        now="2026-06-15T10:00:00Z",
    )

    result = orchestrate_project(project_dir, request, FakeExecutor(), now="2026-06-15T10:00:00Z")

    assert result["status"] == "done"
    assert result["complexity"] == "S1"

    state = load_project_state(project_dir)
    assert state.status == "done"
