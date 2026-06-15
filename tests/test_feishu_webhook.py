import json
from pathlib import Path

import pytest

from cccagents.feishu_webhook import handle_approval_webhook, parse_approval_webhook
from cccagents.project_state import ProjectState, save_project_state


def test_parse_approval_webhook():
    """Test parsing a Feishu approval webhook payload."""
    payload = json.dumps({
        "event": {
            "event_id": "evt_123",
            "type": "card_action",
            "operator": {"user_id": "user_456"},
            "message_id": "msg_789",
            "create_time": 1700000000,
            "action": {
                "value": {
                    "project_id": "proj_abc",
                    "action": "approve",
                    "comment": "Looks good"
                }
            }
        },
        "signature": "sig_xyz"
    })

    event = parse_approval_webhook(payload)

    assert event.event_id == "evt_123"
    assert event.event_type == "card_action"
    assert event.project_id == "proj_abc"
    assert event.action == "approve"
    assert event.user_id == "user_456"
    assert event.message_id == "msg_789"
    assert event.timestamp == 1700000000
    assert event.signature == "sig_xyz"
    assert event.comment == "Looks good"


def test_handle_approval_webhook_approves_project(tmp_path):
    """Test handling an approval webhook that approves a project."""
    project_id = "proj_test_approve"
    project_dir = tmp_path / project_id
    project_dir.mkdir()

    initial_state = ProjectState(
        project_id=project_id,
        complexity="S3",
        status="pending_approval",
        required_roles=["DEV", "TEST", "SEC"],
        risk_flags=["security_sensitive"],
        approval_policy="manual",
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
        current_phase="AWAITING_APPROVAL",
        source="feishu",
        retry_count_by_phase={},
    )
    save_project_state(project_dir, initial_state)

    payload = json.dumps({
        "event": {
            "event_id": "evt_approve_001",
            "type": "card_action",
            "operator": {"user_id": "user_approver"},
            "message_id": "msg_approve_001",
            "create_time": 1700000000,
            "action": {
                "value": {
                    "project_id": project_id,
                    "action": "approve",
                    "comment": "Approved"
                }
            }
        },
        "signature": "valid_sig"
    })

    result = handle_approval_webhook(
        payload=payload,
        project_root=tmp_path,
        allowed_approvers={"user_approver"},
        expected_signature="valid_sig",
        now="2026-06-15T10:05:00Z"
    )

    assert result["success"] is True
    assert result["approved"] is True
    assert result["action"] == "approve"
    assert result["project_id"] == project_id

    log_file = project_dir / "08-logs" / "approval-events.jsonl"
    assert log_file.exists()


def test_handle_approval_webhook_rejects_project(tmp_path):
    """Test handling an approval webhook that rejects a project."""
    project_id = "proj_test_reject"
    project_dir = tmp_path / project_id
    project_dir.mkdir()

    initial_state = ProjectState(
        project_id=project_id,
        complexity="S3",
        status="pending_approval",
        required_roles=["DEV", "TEST", "SEC"],
        risk_flags=["security_sensitive"],
        approval_policy="manual",
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
        current_phase="AWAITING_APPROVAL",
        source="feishu",
        retry_count_by_phase={},
    )
    save_project_state(project_dir, initial_state)

    payload = json.dumps({
        "event": {
            "event_id": "evt_reject_001",
            "type": "card_action",
            "operator": {"user_id": "user_approver"},
            "message_id": "msg_reject_001",
            "create_time": 1700000000,
            "action": {
                "value": {
                    "project_id": project_id,
                    "action": "reject",
                    "comment": "Not ready"
                }
            }
        },
        "signature": "valid_sig"
    })

    result = handle_approval_webhook(
        payload=payload,
        project_root=tmp_path,
        allowed_approvers={"user_approver"},
        expected_signature="valid_sig",
        now="2026-06-15T10:05:00Z"
    )

    assert result["success"] is True
    assert result["approved"] is False
    assert result["action"] == "reject"


def test_handle_approval_webhook_project_not_found(tmp_path):
    """Test handling a webhook for a non-existent project."""
    payload = json.dumps({
        "event": {
            "event_id": "evt_001",
            "type": "card_action",
            "operator": {"user_id": "user_001"},
            "message_id": "msg_001",
            "create_time": 1700000000,
            "action": {
                "value": {
                    "project_id": "nonexistent_project",
                    "action": "approve"
                }
            }
        },
        "signature": "sig_001"
    })

    result = handle_approval_webhook(
        payload=payload,
        project_root=tmp_path,
        allowed_approvers={"user_001"},
        expected_signature="sig_001",
        now="2026-06-15T10:00:00Z"
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_handle_approval_webhook_invalid_signature(tmp_path):
    """Test handling a webhook with invalid signature."""
    project_id = "proj_test_sig"
    project_dir = tmp_path / project_id
    project_dir.mkdir()

    initial_state = ProjectState(
        project_id=project_id,
        complexity="S3",
        status="pending_approval",
        required_roles=["DEV"],
        risk_flags=[],
        approval_policy="manual",
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
        current_phase="AWAITING_APPROVAL",
        source="feishu",
        retry_count_by_phase={},
    )
    save_project_state(project_dir, initial_state)

    payload = json.dumps({
        "event": {
            "event_id": "evt_001",
            "type": "card_action",
            "operator": {"user_id": "user_001"},
            "message_id": "msg_001",
            "create_time": 1700000000,
            "action": {
                "value": {
                    "project_id": project_id,
                    "action": "approve"
                }
            }
        },
        "signature": "invalid_sig"
    })

    result = handle_approval_webhook(
        payload=payload,
        project_root=tmp_path,
        allowed_approvers={"user_001"},
        expected_signature="valid_sig",
        now="2026-06-15T10:00:00Z"
    )

    assert result["success"] is True
    assert result["approved"] is False
    assert "invalid_signature" in result["reason"]


def test_handle_approval_webhook_unauthorized_user(tmp_path):
    """Test handling a webhook from an unauthorized user."""
    project_id = "proj_test_auth"
    project_dir = tmp_path / project_id
    project_dir.mkdir()

    initial_state = ProjectState(
        project_id=project_id,
        complexity="S3",
        status="pending_approval",
        required_roles=["DEV"],
        risk_flags=[],
        approval_policy="manual",
        created_at="2026-06-15T10:00:00Z",
        updated_at="2026-06-15T10:00:00Z",
        current_phase="AWAITING_APPROVAL",
        source="feishu",
        retry_count_by_phase={},
    )
    save_project_state(project_dir, initial_state)

    payload = json.dumps({
        "event": {
            "event_id": "evt_001",
            "type": "card_action",
            "operator": {"user_id": "unauthorized_user"},
            "message_id": "msg_001",
            "create_time": 1700000000,
            "action": {
                "value": {
                    "project_id": project_id,
                    "action": "approve"
                }
            }
        },
        "signature": "valid_sig"
    })

    result = handle_approval_webhook(
        payload=payload,
        project_root=tmp_path,
        allowed_approvers={"authorized_user"},
        expected_signature="valid_sig",
        now="2026-06-15T10:00:00Z"
    )

    assert result["success"] is True
    assert result["approved"] is False
    assert "unauthorized" in result["reason"].lower()
