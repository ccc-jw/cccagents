"""Feishu long-connection (WebSocket) event receiver.

Alternative to webhook mode — useful when the bot cannot expose a public
HTTPS URL (e.g. no domain ICP, NAT-internal servers, firewall restrictions
on inbound 443).  Connects outbound to Feishu's WebSocket gateway and
receives ``P2ImMessageReceiveV1`` / ``P2CardActionTrigger`` events without
needing any inbound URL to be exposed.

This module is a thin shim around ``lark_oapi.ws.Client``: it builds an
``EventDispatcherHandler`` that forwards inbound events to our existing
``cccagents.feishu_webhook`` routing layer.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
from lark_oapi.event.callback.model.p2_card_action_trigger import (
    P2CardActionTrigger,
)

# Make the cccagents package importable when launched via `python -m`.
CCCAGENTS_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(CCCAGENTS_SRC) not in sys.path:
    sys.path.insert(0, str(CCCAGENTS_SRC))

from cccagents.feishu_webhook import dispatch_event  # noqa: E402


def _build_handler(project_root: Path, allowed_senders: set[str],
                   allowed_approvers: set[str], verification_token: str,
                   encrypt_key: str) -> EventDispatcherHandler:
    """Wire up an ``EventDispatcherHandler`` that funnels Feishu events
    into our existing dispatch_event / handle_approval_webhook path."""
    builder = EventDispatcherHandler.builder(
        encrypt_key=encrypt_key,
        verification_token=verification_token,
    )

    def _on_message(data: P2ImMessageReceiveV1) -> None:
        # P2ImMessageReceiveV1 is the typed event; the underlying dict is
        # reachable via __dict__/lark_oapi's internal `event` attribute.
        # Easier: ask the SDK to serialise the event back to a v2-shaped
        # JSON so dispatch_event can parse it unchanged.
        try:
            payload = _serialise_message_event(data)
            result = dispatch_event(
                payload=payload,
                project_root=project_root,
                allowed_senders=allowed_senders,
                allowed_approvers=allowed_approvers,
                expected_signature=verification_token,
                now=_now_iso(),
            )
            print(f"[ws] message → handler={result.handler} success={result.success}", flush=True)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[ws] message dispatch failed: {exc}", flush=True)

    def _on_card_action(data: P2CardActionTrigger) -> None:
        try:
            payload = _serialise_card_action(data)
            result = dispatch_event(
                payload=payload,
                project_root=project_root,
                allowed_senders=allowed_senders,
                allowed_approvers=allowed_approvers,
                expected_signature=verification_token,
                now=_now_iso(),
            )
            print(f"[ws] card_action → handler={result.handler} success={result.success}", flush=True)
        except Exception as exc:  # pragma: no cover - defensive
            print(f"[ws] card_action dispatch failed: {exc}", flush=True)

    builder.register_p2_im_message_receive_v1(_on_message)
    builder.register_p2_card_action_trigger(_on_card_action)
    return builder.build()


def _now_iso() -> str:
    """UTC timestamp in the format dispatch_event expects."""
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _serialise_message_event(data: P2ImMessageReceiveV1) -> str:
    """Convert the typed event back into the v2 JSON shape that
    ``dispatch_event`` / ``parse_message_event`` already understand.

    The SDK's typed events aren't JSON, so we read their public attributes
    and reconstruct the same envelope we receive via webhook.
    """
    event = data.event
    sender = event.sender if event else None
    sender_id = sender.sender_id if sender and sender.sender_id else None
    message = event.message if event else None
    content_str = message.content if message and message.content else "{}"
    try:
        # content is a JSON-encoded string of {"text": "..."}; we want to
        # preserve it as-is so parse_message_event can decode it.
        json.loads(content_str)
    except (ValueError, TypeError):
        # Wrap raw text in the expected JSON envelope.
        content_str = json.dumps({"text": content_str}, ensure_ascii=False)

    payload = {
        "schema": "2.0",
        "header": {"event_type": "im.message.receive_v1"},
        "event": {
            "sender": {
                "sender_id": {
                    "open_id": getattr(sender_id, "open_id", None) if sender_id else None,
                    "union_id": getattr(sender_id, "union_id", None) if sender_id else None,
                    "user_id": getattr(sender_id, "user_id", None) if sender_id else None,
                }
            } if sender else {"sender_id": {}},
            "message": {
                "message_id": getattr(message, "message_id", None) if message else None,
                "chat_id": getattr(message, "chat_id", None) if message else None,
                "chat_type": getattr(message, "chat_type", None) if message else None,
                "message_type": getattr(message, "message_type", None) if message else None,
                "content": content_str,
            },
            "create_time": str(getattr(event, "create_time", 0) if event else 0),
        },
    }
    return json.dumps(payload, ensure_ascii=False)


def _serialise_card_action(data: P2CardActionTrigger) -> str:
    """Same idea for card-action callbacks."""
    event = data.event
    operator = event.operator if event else None
    action = event.action if event else None
    # Only dereference action.value when it's a real object (the SDK typed
    # models don't always expose it; MagicMock tests pass plain dicts).
    value_obj = getattr(action, "value", None) if action else None
    if value_obj is None or isinstance(value_obj, bool):
        value_dict: dict = {}
    else:
        value_dict = {
            "project_id": getattr(value_obj, "project_id", None),
            "action": getattr(value_obj, "action", None),
            "comment": getattr(value_obj, "comment", None),
        }
    return json.dumps({
        "event": {
            "event_id": getattr(event, "event_id", None) if event else None,
            "type": "card_action",
            "operator": {"user_id": getattr(operator, "user_id", None) if operator else None},
            "message_id": getattr(event, "message_id", None) if event else None,
            "create_time": getattr(event, "create_time", 0) if event else 0,
            "action": {"value": value_dict} if action else {},
        },
        "signature": getattr(event, "token", "") if event else "",
    }, ensure_ascii=False)


def run_forever() -> None:
    """Entry point for systemd: build client and run the long connection.

    Reads credentials and project root from environment variables set by
    the systemd unit (see scripts/phase4/cccagents-feishu-ws.service).
    """
    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        print("[ws] FEISHU_APP_ID / FEISHU_APP_SECRET not set", flush=True)
        sys.exit(2)

    project_root = Path(os.getenv("CCCAGENTS_PROJECT_ROOT", "/home/ubuntu/cccagents/projects"))
    allowed_senders = {s for s in os.getenv("FEISHU_ALLOWED_USERS", "").split(",") if s}
    allowed_approvers = allowed_senders
    verification_token = os.getenv("FEISHU_VERIFICATION_TOKEN", "")
    encrypt_key = os.getenv("FEISHU_ENCRYPT_KEY", "")
    domain = os.getenv("FEISHU_DOMAIN", "https://open.feishu.cn")

    handler = _build_handler(
        project_root=project_root,
        allowed_senders=allowed_senders,
        allowed_approvers=allowed_approvers,
        verification_token=verification_token,
        encrypt_key=encrypt_key,
    )

    client = lark.ws.Client(
        app_id=app_id,
        app_secret=app_secret,
        event_handler=handler,
        domain=domain,
        auto_reconnect=True,
        log_level=lark.LogLevel.INFO,
    )
    print(f"[ws] starting long connection: app_id={app_id} domain={domain}", flush=True)
    # .start() blocks until the process is killed / network error / explicit stop().
    client.start()


if __name__ == "__main__":
    run_forever()