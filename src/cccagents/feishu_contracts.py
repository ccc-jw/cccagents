from dataclasses import dataclass
from typing import Any

from cccagents.redaction import redact_text


ALLOWED_APPROVAL_ACTIONS = {"approve", "reject", "comment", "pause_project", "resume_project"}


@dataclass(frozen=True)
class FeishuInboundMessage:
    project_id: str
    feishu_message_id: str
    feishu_chat_id: str
    feishu_user_id: str
    message_type: str
    text: str
    received_at: int


@dataclass(frozen=True)
class PMRoute:
    project_id: str
    target_role: str
    source: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class FeishuApprovalAction:
    project_id: str
    approval_id: str
    action: str
    feishu_user_id: str
    feishu_message_id: str
    timestamp: int
    signature: str


@dataclass(frozen=True)
class FeishuSecurityContext:
    allowed_approvers: set[str]
    seen_event_ids: set[str]
    now: int
    timestamp_window_seconds: int
    expected_signature: str


@dataclass(frozen=True)
class FeishuDecision:
    allowed: bool
    reason: str


def build_pm_route(message: FeishuInboundMessage) -> PMRoute:
    return PMRoute(
        project_id=message.project_id,
        target_role="PM",
        source="feishu",
        payload={
            "feishu_message_id": message.feishu_message_id,
            "feishu_chat_id": message.feishu_chat_id,
            "feishu_user_id": message.feishu_user_id,
            "message_type": message.message_type,
            "text": message.text,
            "received_at": message.received_at,
        },
    )


def validate_approval_action(
    action: FeishuApprovalAction,
    context: FeishuSecurityContext,
) -> FeishuDecision:
    if action.signature != context.expected_signature:
        return FeishuDecision(False, "invalid_signature")
    if abs(context.now - action.timestamp) > context.timestamp_window_seconds:
        return FeishuDecision(False, "timestamp_out_of_window")
    if action.feishu_message_id in context.seen_event_ids:
        return FeishuDecision(False, "replay_detected")
    if action.feishu_user_id not in context.allowed_approvers:
        return FeishuDecision(False, "unauthorized_approver")
    if action.action not in ALLOWED_APPROVAL_ACTIONS:
        return FeishuDecision(False, "unsupported_action")
    return FeishuDecision(True, "approved")


def validate_card_content(content: str) -> FeishuDecision:
    redacted = redact_text(content)
    if redacted.redacted:
        return FeishuDecision(False, "secret_like_content")
    return FeishuDecision(True, "approved")
