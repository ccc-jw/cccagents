import json
from dataclasses import dataclass
from pathlib import Path

from cccagents.approval_handler import ApprovalRequest, process_approval_action
from cccagents.feishu_contracts import FeishuSecurityContext
from cccagents.redaction import redact_text


@dataclass(frozen=True)
class WebhookEvent:
    event_id: str
    event_type: str
    project_id: str
    action: str
    user_id: str
    message_id: str
    timestamp: int
    signature: str
    comment: str | None = None


def parse_approval_webhook(payload: str) -> WebhookEvent:
    """Parse a Feishu webhook payload into a WebhookEvent."""
    data = json.loads(payload)

    event = data.get("event", {})
    action_data = event.get("action", {})

    return WebhookEvent(
        event_id=event.get("event_id", ""),
        event_type=event.get("type", ""),
        project_id=action_data.get("value", {}).get("project_id", ""),
        action=action_data.get("value", {}).get("action", ""),
        user_id=event.get("operator", {}).get("user_id", ""),
        message_id=event.get("message_id", ""),
        timestamp=event.get("create_time", 0),
        signature=data.get("signature", ""),
        comment=action_data.get("value", {}).get("comment"),
    )


def handle_approval_webhook(
    payload: str,
    project_root: Path,
    allowed_approvers: set[str],
    expected_signature: str,
    now: str,
) -> dict:
    """Handle a Feishu approval webhook event."""
    redacted_payload = redact_text(payload)

    event = parse_approval_webhook(payload)

    project_dir = project_root / event.project_id
    if not project_dir.exists():
        return {
            "success": False,
            "error": f"Project not found: {event.project_id}",
            "event_id": event.event_id,
        }

    context = FeishuSecurityContext(
        allowed_approvers=allowed_approvers,
        seen_event_ids=set(),
        now=event.timestamp,
        timestamp_window_seconds=300,
        expected_signature=expected_signature,
    )

    request = ApprovalRequest(
        project_id=event.project_id,
        approval_id=event.event_id,
        action=event.action,
        feishu_user_id=event.user_id,
        feishu_message_id=event.message_id,
        timestamp=event.timestamp,
        signature=event.signature,
        comment=event.comment,
    )

    result = process_approval_action(request, context, project_dir, now=now)

    log_approval_event(project_dir, event, result, now)

    return {
        "success": True,
        "project_id": event.project_id,
        "action": event.action,
        "approved": result.approved,
        "reason": result.reason,
        "event_id": event.event_id,
    }


def log_approval_event(project_dir: Path, event: WebhookEvent, result, now: str) -> None:
    """Log approval event to project directory."""
    log_dir = project_dir / "08-logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_entry = {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "project_id": event.project_id,
        "action": event.action,
        "user_id": event.user_id,
        "timestamp": event.timestamp,
        "approved": result.approved,
        "reason": result.reason,
        "processed_at": now,
    }

    with (log_dir / "approval-events.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False, sort_keys=True) + "\n")
