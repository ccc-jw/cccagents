from cccagents.feishu_contracts import (
    FeishuApprovalAction,
    FeishuInboundMessage,
    FeishuSecurityContext,
    build_pm_route,
    validate_approval_action,
    validate_card_content,
)


def test_feishu_inbound_message_always_routes_to_pm():
    message = FeishuInboundMessage(
        project_id="demo",
        feishu_message_id="msg-1",
        feishu_chat_id="chat-1",
        feishu_user_id="user-1",
        message_type="text",
        text="创建一个项目",
        received_at=1_700_000_000,
    )

    route = build_pm_route(message)

    assert route.project_id == "demo"
    assert route.target_role == "PM"
    assert route.source == "feishu"
    assert route.payload["text"] == "创建一个项目"


def test_valid_approval_action_passes_security_checks():
    action = FeishuApprovalAction(
        project_id="demo",
        approval_id="approval-1",
        action="approve",
        feishu_user_id="user-1",
        feishu_message_id="event-1",
        timestamp=1_700_000_000,
        signature="sig-ok",
    )
    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids=set(),
        now=1_700_000_100,
        timestamp_window_seconds=300,
        expected_signature="sig-ok",
    )

    decision = validate_approval_action(action, context)

    assert decision.allowed is True
    assert decision.reason == "approved"


def test_unknown_approver_is_rejected():
    action = FeishuApprovalAction(
        project_id="demo",
        approval_id="approval-1",
        action="approve",
        feishu_user_id="user-2",
        feishu_message_id="event-1",
        timestamp=1_700_000_000,
        signature="sig-ok",
    )
    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids=set(),
        now=1_700_000_100,
        timestamp_window_seconds=300,
        expected_signature="sig-ok",
    )

    decision = validate_approval_action(action, context)

    assert decision.allowed is False
    assert decision.reason == "unauthorized_approver"


def test_replayed_event_is_rejected():
    action = FeishuApprovalAction(
        project_id="demo",
        approval_id="approval-1",
        action="approve",
        feishu_user_id="user-1",
        feishu_message_id="event-1",
        timestamp=1_700_000_000,
        signature="sig-ok",
    )
    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids={"event-1"},
        now=1_700_000_100,
        timestamp_window_seconds=300,
        expected_signature="sig-ok",
    )

    decision = validate_approval_action(action, context)

    assert decision.allowed is False
    assert decision.reason == "replay_detected"


def test_old_timestamp_is_rejected():
    action = FeishuApprovalAction(
        project_id="demo",
        approval_id="approval-1",
        action="approve",
        feishu_user_id="user-1",
        feishu_message_id="event-1",
        timestamp=1_699_999_000,
        signature="sig-ok",
    )
    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids=set(),
        now=1_700_000_100,
        timestamp_window_seconds=300,
        expected_signature="sig-ok",
    )

    decision = validate_approval_action(action, context)

    assert decision.allowed is False
    assert decision.reason == "timestamp_out_of_window"


def test_invalid_signature_is_rejected():
    action = FeishuApprovalAction(
        project_id="demo",
        approval_id="approval-1",
        action="approve",
        feishu_user_id="user-1",
        feishu_message_id="event-1",
        timestamp=1_700_000_000,
        signature="sig-bad",
    )
    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids=set(),
        now=1_700_000_100,
        timestamp_window_seconds=300,
        expected_signature="sig-ok",
    )

    decision = validate_approval_action(action, context)

    assert decision.allowed is False
    assert decision.reason == "invalid_signature"


def test_secret_like_card_content_is_rejected():
    decision = validate_card_content("部署完成，ANTHROPIC_API_KEY=sk-live-secret")

    assert decision.allowed is False
    assert decision.reason == "secret_like_content"
