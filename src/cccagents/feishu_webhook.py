import base64
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from cccagents.approval_handler import ApprovalRequest, process_approval_action
from cccagents.feishu_contracts import (
    FeishuInboundMessage,
    FeishuSecurityContext,
    build_pm_route,
)
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


@dataclass(frozen=True)
class ChallengeResult:
    """Outcome of processing Feishu's URL-verification challenge.

    ``body`` is exactly what we return to Feishu.  ``mode`` is either
    ``"plain"`` (echoed the raw ``echostr``) or ``"encrypted"`` (AES round-trip
    through ``FEISHU_ENCRYPT_KEY``).  ``ok`` is False when the challenge was
    malformed or decryption failed; the caller should still respond with the
    raw body if one is set, but a 4xx status is appropriate.
    """

    body: str
    mode: str
    ok: bool
    reason: str = ""


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


# ---------------------------------------------------------------------------
# Inbound message decoding (im.message.receive_v1)
# ---------------------------------------------------------------------------


def parse_message_event(payload: str) -> FeishuInboundMessage:
    """Parse a Feishu ``im.message.receive_v1`` event.

    The Feishu v2 schema wraps the event under ``header.event_type`` and
    ``event.{sender,message}``.  The message ``content`` field is a JSON
    string (yes, string-of-JSON) holding type-specific payload.
    """
    data = json.loads(payload)

    header = data.get("header", {})
    event = data.get("event", {})

    sender = event.get("sender", {})
    sender_id = sender.get("sender_id", {})
    # Prefer open_id so users are identified consistently across chats, but fall
    # back to union_id / user_id if open_id is missing.
    feishu_user_id = (
        sender_id.get("open_id")
        or sender_id.get("union_id")
        or sender_id.get("user_id")
        or ""
    )

    message = event.get("message", {})
    chat_id = message.get("chat_id", "")
    message_id = message.get("message_id", "")
    message_type = message.get("message_type", "text")
    raw_content = message.get("content", "{}")

    # ``content`` is a JSON-encoded string.  Decode it to extract the actual
    # text payload.  We do this defensively — if the decode fails we keep the
    # raw content as the text so the message is at least visible to PM.
    text = raw_content
    if message_type == "text":
        try:
            text = json.loads(raw_content).get("text", raw_content)
        except (ValueError, TypeError):
            pass

    # create_time is a millisecond timestamp in v2 events.
    received_at = int(event.get("create_time", "0") or 0)

    return FeishuInboundMessage(
        project_id="",  # Feishu messages don't carry a project_id; PM assigns one.
        feishu_message_id=message_id,
        feishu_chat_id=chat_id,
        feishu_user_id=feishu_user_id,
        message_type=message_type,
        text=text,
        received_at=received_at,
    )


def handle_inbound_message(
    payload: str,
    project_root: Path,
    allowed_senders: set[str],
    now: str,
) -> dict:
    """Route an inbound Feishu message to the PM role.

    Returns a dict with ``success``, ``target_role``, ``project_id`` (empty
    until PM assigns one), and ``route`` (the constructed PMRoute).
    """
    message = parse_message_event(payload)
    redacted = redact_text(message.text)

    if message.feishu_user_id not in allowed_senders:
        return {
            "success": False,
            "target_role": "PM",
            "project_id": "",
            "reason": "unauthorized_sender",
            "feishu_message_id": message.feishu_message_id,
        }

    route = build_pm_route(message)
    _log_message_event(project_root, message, redacted.text, now)

    # Best-effort ack back to the user so they know PM is processing.
    # Failures are logged but never block the dispatch path.
    reply_result: dict[str, Any] = {"ok": None}
    try:
        from cccagents.feishu_reply import reply_to_feishu
        reply_text = f"已收到（{message.message_type}），PM 正在处理…"
        reply_result = reply_to_feishu(message.feishu_user_id, reply_text)
    except Exception as exc:  # pragma: no cover - network paths
        reply_result = {"ok": False, "error": str(exc)}

    return {
        "success": True,
        "target_role": route.target_role,
        "project_id": route.project_id,
        "reason": "routed_to_pm",
        "feishu_message_id": message.feishu_message_id,
        "reply": reply_result,
    }


def _log_message_event(
    project_root: Path,
    message: FeishuInboundMessage,
    redacted_text: str,
    now: str,
) -> None:
    """Append a redaction-safe line to the global message-events log.

    PM-only boundary requires that other roles never see raw user text.
    We record the redacted form so even the log can't leak secrets.
    """
    log_dir = project_root / "_feishu-messages"
    log_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "feishu_message_id": message.feishu_message_id,
        "feishu_user_id": message.feishu_user_id,
        "feishu_chat_id": message.feishu_chat_id,
        "message_type": message.message_type,
        "text": redacted_text,
        "received_at": message.received_at,
        "processed_at": now,
    }
    with (log_dir / "inbound.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Event dispatcher
# ---------------------------------------------------------------------------


SUPPORTED_EVENT_TYPES = {
    "card_action",  # legacy v1 / interactive card callback
    "card_action.trigger",  # v2 card action
    "im.message.receive_v1",  # user message to bot
    "url_verification",  # Feishu app-level challenge (different from URL-verify challenge)
}


@dataclass(frozen=True)
class DispatchResult:
    handler: str  # which handler was invoked
    success: bool
    detail: dict[str, Any]


def dispatch_event(
    payload: str,
    project_root: Path,
    allowed_senders: set[str],
    allowed_approvers: set[str],
    expected_signature: str,
    now: str,
) -> DispatchResult:
    """Top-level dispatcher for every Feishu event the bot subscribes to.

    Returns a :class:`DispatchResult` naming the handler that ran so callers
    can log or audit which path took the message.
    """
    try:
        data = json.loads(payload)
    except (ValueError, TypeError) as exc:
        return DispatchResult(handler="malformed", success=False, detail={"error": str(exc)})

    # v2 events put the type under header.event_type; v1 puts it on event.type.
    # The app-level "url_verification" challenge lives at the top level as
    # ``type`` so we fall back to that too.
    event_type = (
        data.get("header", {}).get("event_type")
        or data.get("event", {}).get("type")
        or data.get("type")
        or ""
    )

    # Some Feishu URL-verification callbacks come through as POST with an
    # ``{"encrypt": "..."}`` body (encrypted challenge).  Detect that shape
    # before falling through to the generic dispatcher, otherwise we'd
    # return handler="unknown" and 400.
    if event_type == "url_verification":
        # App-level challenge (rare — usually only seen during subscribe flow).
        challenge = data.get("challenge", "")
        return DispatchResult(
            handler="url_verification",
            success=True,
            detail={"challenge": challenge},
        )

    if event_type == "" and "encrypt" in data:
        # Modern Feishu URL-verification: POST body is {"encrypt": "<base64>"}.
        # Decrypt it using the same AES-256-CBC / SHA-256(encrypt_key) / PKCS7(128)
        # scheme as the GET echostr variant.  Echo the inner ``challenge``
        # back as an encrypted blob so Feishu considers the URL valid.
        print(f"[dispatch] encrypted challenge branch: encrypt_len={len(data.get('encrypt', ''))}", flush=True)
        try:
            import os
            encrypt_key = os.getenv("FEISHU_ENCRYPT_KEY", "")
            if not encrypt_key:
                return DispatchResult(
                    handler="url_verification_encrypted",
                    success=False,
                    detail={"error": "missing FEISHU_ENCRYPT_KEY"},
                )
            plaintext = _feishu_decrypt(data["encrypt"], encrypt_key)
            inner = json.loads(plaintext)
            inner_challenge = inner.get("challenge", "")
            if not inner_challenge:
                return DispatchResult(
                    handler="url_verification_encrypted",
                    success=False,
                    detail={"error": "missing challenge field"},
                )
            echoed = _feishu_encrypt(
                json.dumps({"challenge": inner_challenge}), encrypt_key,
            )
            print(f"[dispatch] encrypted challenge echoed: inner={inner_challenge!r}", flush=True)
            return DispatchResult(
                handler="url_verification_encrypted",
                success=True,
                detail={"challenge": echoed, "raw": inner_challenge},
            )
        except Exception as exc:
            print(f"[dispatch] encrypted challenge error: {exc}", flush=True)
            return DispatchResult(
                handler="url_verification_encrypted",
                success=False,
                detail={"error": str(exc)},
            )

    if event_type in ("im.message.receive_v1",):
        result = handle_inbound_message(
            payload=payload,
            project_root=project_root,
            allowed_senders=allowed_senders,
            now=now,
        )
        return DispatchResult(handler="message", success=result["success"], detail=result)

    if event_type in ("card_action", "card_action.trigger"):
        approval_result = handle_approval_webhook(
            payload=payload,
            project_root=project_root,
            allowed_approvers=allowed_approvers,
            expected_signature=expected_signature,
            now=now,
        )
        return DispatchResult(
            handler="approval",
            success=approval_result["success"],
            detail=approval_result,
        )

    return DispatchResult(
        handler="unknown",
        success=False,
        detail={"error": "unsupported_event_type", "event_type": event_type},
    )


# ---------------------------------------------------------------------------
# URL-verification challenge
# ---------------------------------------------------------------------------


def handle_challenge(
    query_string: str,
    encrypt_key: str,
) -> ChallengeResult:
    """Process Feishu's URL-verification challenge.

    Feishu sends a GET with three shapes:

    1. **Plaintext** — ``echostr=<value>`` when no Encrypt Key is configured.
       The handler must echo the value verbatim.

    2. **Encrypted** — when an Encrypt Key is configured, Feishu sends the
       challenge as an AES-256-CBC-encrypted JSON blob keyed by
       SHA-256(encrypt_key) with the IV prepended (base64).  The handler must
       decrypt, extract the inner ``challenge`` field, then re-encrypt and
       return the new blob.

    3. **No challenge at all** — a plain health-check probe.  We respond with
       a small JSON body so curl / monitoring tools see a meaningful answer.
    """
    params = parse_qs(query_string or "")
    challenge_param = params.get("echostr", [None])[0]
    if challenge_param is None:
        # No challenge → treat as health probe.
        return ChallengeResult(body=json.dumps({"status": "ok"}), mode="health", ok=True)

    if not encrypt_key:
        # Plaintext mode: echo verbatim.
        return ChallengeResult(body=challenge_param, mode="plain", ok=True)

    # Encrypted mode: AES-256-CBC round-trip.
    try:
        plaintext = _feishu_decrypt(challenge_param, encrypt_key)
        inner = json.loads(plaintext)
        inner_challenge = inner.get("challenge", "")
        if not inner_challenge:
            return ChallengeResult(
                body=json.dumps({"error": "missing challenge"}),
                mode="encrypted",
                ok=False,
                reason="missing challenge field",
            )
        echoed = _feishu_encrypt(json.dumps({"challenge": inner_challenge}), encrypt_key)
        return ChallengeResult(body=echoed, mode="encrypted", ok=True)
    except Exception as exc:
        return ChallengeResult(
            body=json.dumps({"error": str(exc)}),
            mode="encrypted",
            ok=False,
            reason=str(exc),
        )


def _feishu_aes_key(encrypt_key: str) -> bytes:
    """Feishu derives the AES-256 key as SHA-256(encrypt_key)."""
    return hashlib.sha256(encrypt_key.encode("utf-8")).digest()


def _feishu_decrypt(ciphertext_b64: str, encrypt_key: str) -> str:
    """Decrypt a Feishu challenge blob (AES-256-CBC, base64, IV prepended)."""
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding

    raw = base64.b64decode(ciphertext_b64)
    iv, ciphertext = raw[:16], raw[16:]
    cipher = Cipher(algorithms.AES(_feishu_aes_key(encrypt_key)), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded) + unpadder.finalize()
    return plaintext.decode("utf-8")


def _feishu_encrypt(plaintext: str, encrypt_key: str) -> str:
    """Encrypt a Feishu challenge response (AES-256-CBC, base64, IV prepended)."""
    import os as _os

    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding

    iv = _os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(_feishu_aes_key(encrypt_key)), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(iv + ciphertext).decode("utf-8")
