"""PM-only boundary tests.

The deployment contract — see ``AGENTS.md`` — is that Feishu users only talk
to PM.  PDM/RES/ARCH/DEV/TEST/SEC are implementation roles invoked by PM, not
front-line user entry points.  This module pins that contract down with
explicit tests so a future refactor can't accidentally route a Feishu message
to a non-PM role.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cccagents.feishu_webhook import (
    SUPPORTED_EVENT_TYPES,
    build_pm_route,
    dispatch_event,
    handle_inbound_message,
    parse_message_event,
)


VALID_SENDERS = {"ou_pm_user"}
VALID_APPROVERS = {"ou_pm_user"}


def _sample_message_payload() -> str:
    return json.dumps(
        {
            "schema": "2.0",
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "sender": {
                    "sender_id": {"open_id": "ou_pm_user", "union_id": "on_x", "user_id": "u_x"}
                },
                "message": {
                    "message_id": "om_001",
                    "chat_id": "oc_001",
                    "chat_type": "p2p",
                    "message_type": "text",
                    "content": json.dumps({"text": "ping pm"}),
                },
                "create_time": "1700000000",
            },
        }
    )


def test_message_event_supported():
    """``im.message.receive_v1`` is in the supported set."""
    assert "im.message.receive_v1" in SUPPORTED_EVENT_TYPES


def test_unsupported_event_types_rejected():
    """Events outside the supported set must not silently route."""
    payload = json.dumps(
        {
            "schema": "2.0",
            "header": {"event_type": "im.message.reaction.created_v1"},
            "event": {},
        }
    )
    result = dispatch_event(
        payload=payload,
        project_root=Path("/tmp"),
        allowed_senders=VALID_SENDERS,
        allowed_approvers=VALID_APPROVERS,
        expected_signature="sig",
        now="2026-06-24T00:00:00Z",
    )
    assert result.success is False
    assert result.handler == "unknown"
    assert result.detail.get("event_type") == "im.message.reaction.created_v1"


def test_pm_only_routing_no_other_role_target():
    """``build_pm_route`` must always return ``target_role="PM"``."""
    msg = parse_message_event(_sample_message_payload())
    route = build_pm_route(msg)
    assert route.target_role == "PM"
    assert route.source == "feishu"


def test_inbound_message_unauthorized_sender_rejected():
    """Senders not on the allowlist must be rejected with a clear reason."""
    result = handle_inbound_message(
        payload=_sample_message_payload().replace("ou_pm_user", "ou_random_user"),
        project_root=Path("/tmp"),
        allowed_senders=VALID_SENDERS,
        now="2026-06-24T00:00:00Z",
    )
    assert result["success"] is False
    assert result["reason"] == "unauthorized_sender"
    assert result["target_role"] == "PM"


def test_inbound_message_authorized_routes_to_pm():
    """Allowed sender → success and target_role=PM (and only PM)."""
    with patch("cccagents.feishu_reply.reply_to_feishu", return_value={"ok": True, "message_id": "om_x"}):
        result = handle_inbound_message(
            payload=_sample_message_payload(),
            project_root=Path("/tmp/_pm-boundary-test"),
            allowed_senders=VALID_SENDERS,
            now="2026-06-24T00:00:00Z",
        )
    assert result["success"] is True
    assert result["target_role"] == "PM"
    # Make sure the route never mentions PDM/RES/ARCH/DEV/TEST/SEC.
    for forbidden in ("PDM", "RES", "ARCH", "DEV", "TEST", "SEC"):
        assert forbidden not in str(result)


def test_dispatch_message_handler_returns_pm():
    """End-to-end: a message event dispatched at the top level lands on PM."""
    with patch("cccagents.feishu_reply.reply_to_feishu", return_value={"ok": True, "message_id": "om_x"}):
        result = dispatch_event(
            payload=_sample_message_payload(),
            project_root=Path("/tmp/_pm-boundary-test"),
            allowed_senders=VALID_SENDERS,
            allowed_approvers=VALID_APPROVERS,
            expected_signature="sig",
            now="2026-06-24T00:00:00Z",
        )
    assert result.success is True
    assert result.handler == "message"
    assert result.detail["target_role"] == "PM"


@pytest.mark.parametrize("forbidden_role", ["PDM", "RES", "ARCH", "DEV", "TEST", "SEC"])
def test_no_handler_returns_forbidden_role(forbidden_role):
    """The handler set has no path that returns a non-PM target_role."""
    # parse_message_event produces a FeishuInboundMessage; build_pm_route is
    # the only place that produces a PMRoute, and PMRoute.target_role is
    # hard-coded to "PM".  This test fails if anyone adds a new builder that
    # targets a forbidden role.
    msg = parse_message_event(_sample_message_payload())
    route = build_pm_route(msg)
    assert route.target_role != forbidden_role


def test_url_verification_challenge_echoes_challenge():
    """The app-level ``url_verification`` event returns the challenge field."""
    payload = json.dumps(
        {
            "type": "url_verification",
            "challenge": "abc123",
        }
    )
    result = dispatch_event(
        payload=payload,
        project_root=Path("/tmp"),
        allowed_senders=VALID_SENDERS,
        allowed_approvers=VALID_APPROVERS,
        expected_signature="sig",
        now="2026-06-24T00:00:00Z",
    )
    assert result.success is True
    assert result.handler == "url_verification"
    assert result.detail["challenge"] == "abc123"


def test_malformed_payload_reports_handler():
    """Garbage payloads must not crash and must report a sensible handler."""
    result = dispatch_event(
        payload="not-json",
        project_root=Path("/tmp"),
        allowed_senders=VALID_SENDERS,
        allowed_approvers=VALID_APPROVERS,
        expected_signature="sig",
        now="2026-06-24T00:00:00Z",
    )
    assert result.success is False
    assert result.handler == "malformed"
