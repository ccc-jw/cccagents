from unittest.mock import patch, MagicMock
from pathlib import Path
import json
import pytest

from cccagents.feishu_webhook_server import FeishuWebhookHandler, run_server


def test_webhook_handler_processes_approval():
    """Test that webhook handler processes approval events correctly."""
    # Mock request and response
    handler = FeishuWebhookHandler.__new__(FeishuWebhookHandler)
    handler.rfile = MagicMock()
    handler.wfile = MagicMock()
    handler.headers = {"Content-Length": "0"}
    handler.address_string = lambda: "127.0.0.1"

    # Mock send_response, send_header, end_headers
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    # Create test payload
    payload = json.dumps({
        "event": {
            "event_id": "evt_123",
            "type": "card_action",
            "operator": {"user_id": "user_456"},
            "message_id": "msg_789",
            "create_time": 1700000000,
            "action": {
                "value": {
                    "project_id": "test-project",
                    "action": "approve",
                    "comment": "Looks good"
                }
            }
        },
        "signature": "test_sig"
    })

    handler.rfile.read.return_value = payload.encode("utf-8")
    handler.headers["Content-Length"] = str(len(payload))

    # Mock environment variables
    with patch.dict('os.environ', {
        'CCCAGENTS_PROJECT_ROOT': '/tmp/test-projects',
        'FEISHU_ALLOWED_USERS': 'user_456',
        'FEISHU_VERIFICATION_TOKEN': 'test_sig'
    }):
        # Mock dispatch_event to avoid file operations and assert the new
        # response envelope (dispatched_to / success / detail).
        from cccagents.feishu_webhook import DispatchResult
        with patch('cccagents.feishu_webhook_server.dispatch_event') as mock_dispatch:
            mock_dispatch.return_value = DispatchResult(
                handler="approval",
                success=True,
                detail={
                    "project_id": "test-project",
                    "action": "approve",
                    "approved": True,
                    "reason": "approved",
                    "event_id": "evt_123",
                },
            )

            # Call do_POST
            handler.do_POST()

            # Verify response
            handler.send_response.assert_called_with(200)
            handler.send_header.assert_called_with("Content-Type", "application/json")
            handler.end_headers.assert_called()

            # Verify dispatch_event was called
            assert mock_dispatch.called
            call_args = mock_dispatch.call_args
            assert call_args.kwargs["project_root"] == Path("/tmp/test-projects")
            assert call_args.kwargs["allowed_approvers"] == {"user_456"}
            assert call_args.kwargs["allowed_senders"] == {"user_456"}
            assert call_args.kwargs["expected_signature"] == "test_sig"


def test_webhook_handler_handles_missing_project():
    """Test that webhook handler handles missing project gracefully."""
    handler = FeishuWebhookHandler.__new__(FeishuWebhookHandler)
    handler.rfile = MagicMock()
    handler.wfile = MagicMock()
    handler.headers = {"Content-Length": "0"}
    handler.address_string = lambda: "127.0.0.1"

    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    payload = json.dumps({
        "event": {
            "event_id": "evt_123",
            "type": "card_action",
            "operator": {"user_id": "user_456"},
            "message_id": "msg_789",
            "create_time": 1700000000,
            "action": {
                "value": {
                    "project_id": "nonexistent-project",
                    "action": "approve"
                }
            }
        },
        "signature": "test_sig"
    })

    handler.rfile.read.return_value = payload.encode("utf-8")
    handler.headers["Content-Length"] = str(len(payload))

    with patch.dict('os.environ', {
        'CCCAGENTS_PROJECT_ROOT': '/tmp/test-projects',
        'FEISHU_ALLOWED_USERS': 'user_456',
        'FEISHU_VERIFICATION_TOKEN': 'test_sig'
    }):
        # Mock dispatch_event to short-circuit the missing-project error path.
        from cccagents.feishu_webhook import DispatchResult
        with patch('cccagents.feishu_webhook_server.dispatch_event') as mock_dispatch:
            mock_dispatch.return_value = DispatchResult(
                handler="approval",
                success=True,
                detail={"reason": "missing_project", "project_id": "nonexistent-project"},
            )

            handler.do_POST()

            # Should still return 200 (the dispatcher handled the error gracefully).
            handler.send_response.assert_called_with(200)


def test_webhook_handler_health_check():
    """Test that GET request returns health check response."""
    handler = FeishuWebhookHandler.__new__(FeishuWebhookHandler)
    handler.wfile = MagicMock()
    handler.address_string = lambda: "127.0.0.1"
    handler.path = "/"

    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_GET()

    handler.send_response.assert_called_with(200)
    handler.send_header.assert_called_with("Content-Type", "application/json")
    handler.end_headers.assert_called()
    # The new health probe responds with a JSON status body.
    body = handler.wfile.write.call_args.args[0].decode("utf-8")
    assert "status" in body


# ---------------------------------------------------------------------------
# Feishu URL-verification challenge tests
# ---------------------------------------------------------------------------

from cccagents.feishu_webhook import handle_challenge  # noqa: E402
from cccagents.feishu_webhook import dispatch_event  # noqa: E402


def test_challenge_plaintext_echoes_echostr():
    """When no encrypt key is set, echo the raw echostr verbatim."""
    result = handle_challenge("echostr=hello123&timestamp=1&nonce=2", encrypt_key="")
    assert result.ok is True
    assert result.mode == "plain"
    assert result.body == "hello123"


def test_challenge_health_probe_with_no_echostr():
    """A GET with no echostr is treated as a health probe."""
    result = handle_challenge(query_string="", encrypt_key="")
    assert result.ok is True
    assert result.mode == "health"
    assert "status" in result.body


def test_challenge_encrypted_roundtrip():
    """Encrypted challenge should decrypt, extract, and re-encrypt the challenge."""
    import base64
    import hashlib
    import os
    from urllib.parse import quote

    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding

    encrypt_key = "test-encrypt-key"
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    plaintext = padder.update(b'{"challenge":"abc123"}') + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    # URL-encode the base64 so the test query string is parseable by parse_qs.
    challenge_b64 = quote(base64.b64encode(iv + ciphertext).decode("utf-8"))

    result = handle_challenge(
        query_string=f"echostr={challenge_b64}&timestamp=1&nonce=2",
        encrypt_key=encrypt_key,
    )
    assert result.ok is True, f"challenge failed: mode={result.mode} reason={result.reason}"
    assert result.mode == "encrypted"
    raw = base64.b64decode(result.body)
    echoed_iv, echoed_ct = raw[:16], raw[16:]
    dec = Cipher(algorithms.AES(key), modes.CBC(echoed_iv)).decryptor()
    padded = dec.update(echoed_ct) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    plain = unpadder.update(padded) + unpadder.finalize()
    inner = json.loads(plain.decode("utf-8"))
    assert inner["challenge"] == "abc123"


def test_challenge_encrypted_with_bad_input_fails():
    """A bogus echostr with encrypt key configured should return ok=False cleanly."""
    result = handle_challenge(
        query_string="echostr=not-valid-base64-or-aes&timestamp=1&nonce=2",
        encrypt_key="some-key",
    )
    assert result.ok is False
    assert result.mode == "encrypted"


def test_dispatch_encrypted_challenge_post():
    """dispatch_event must accept modern Feishu URL-verification POST bodies
    ({"encrypt": "<base64>"}) and echo the decrypted challenge back."""
    import base64
    import hashlib
    import os

    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding

    encrypt_key = "deploy-test-key"
    aes = hashlib.sha256(encrypt_key.encode()).digest()
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    plain = padder.update(b'{"challenge":"fly_test_2026"}') + padder.finalize()
    ct = Cipher(algorithms.AES(aes), modes.CBC(iv)).encryptor().update(plain) + Cipher(algorithms.AES(aes), modes.CBC(iv)).encryptor().finalize()
    challenge_b64 = base64.b64encode(iv + ct).decode()

    payload = json.dumps({"encrypt": challenge_b64})

    with patch.dict(
        "os.environ",
        {"FEISHU_ENCRYPT_KEY": encrypt_key},
        clear=False,
    ):
        result = dispatch_event(
            payload=payload,
            project_root=Path("/tmp"),
            allowed_senders=set(),
            allowed_approvers=set(),
            expected_signature="",
            now="2026-06-25T00:00:00Z",
        )

    assert result.success is True
    assert result.handler == "url_verification_encrypted"
    # The detail contains the re-encrypted challenge — must NOT be the
    # plaintext form because Feishu's verifier parses the body as ciphertext.
    assert result.detail["raw"] == "fly_test_2026"
    echoed_b64 = result.detail["challenge"]
    assert isinstance(echoed_b64, str)
    assert len(echoed_b64) > 0

    # Round-trip: decrypt the echoed blob and confirm the inner challenge
    # matches the original.
    raw = base64.b64decode(echoed_b64)
    echoed_iv, echoed_ct = raw[:16], raw[16:]
    dec = Cipher(algorithms.AES(aes), modes.CBC(echoed_iv)).decryptor()
    padded = dec.update(echoed_ct) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    decoded = (unpadder.update(padded) + unpadder.finalize()).decode("utf-8")
    assert json.loads(decoded)["challenge"] == "fly_test_2026"


def test_dispatch_encrypted_challenge_post_without_key_fails():
    """No FEISHU_ENCRYPT_KEY set → ok=False with a clear reason."""
    payload = json.dumps({"encrypt": "any-base64-text"})
    with patch.dict("os.environ", {"FEISHU_ENCRYPT_KEY": ""}, clear=False):
        result = dispatch_event(
            payload=payload,
            project_root=Path("/tmp"),
            allowed_senders=set(),
            allowed_approvers=set(),
            expected_signature="",
            now="2026-06-25T00:00:00Z",
        )
    assert result.success is False
    assert result.handler == "url_verification_encrypted"
    assert "FEISHU_ENCRYPT_KEY" in result.detail["error"]


def test_dispatch_encrypted_challenge_post_with_garbage_payload():
    """A non-AES payload with the encrypt-key set must return ok=False cleanly."""
    with patch.dict(
        "os.environ",
        {"FEISHU_ENCRYPT_KEY": "some-key"},
        clear=False,
    ):
        result = dispatch_event(
            payload=json.dumps({"encrypt": "not-base64-or-aes"}),
            project_root=Path("/tmp"),
            allowed_senders=set(),
            allowed_approvers=set(),
            expected_signature="",
            now="2026-06-25T00:00:00Z",
        )
    assert result.success is False
    assert result.handler == "url_verification_encrypted"
    assert "error" in result.detail


def test_webhook_handler_healthz_returns_json():
    """GET /healthz should return a JSON snapshot of upstream health."""
    from unittest.mock import patch

    handler = FeishuWebhookHandler.__new__(FeishuWebhookHandler)
    handler.wfile = MagicMock()
    handler.address_string = lambda: "127.0.0.1"
    handler.path = "/healthz"
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    fake_health = {
        "ok": True,
        "checked_at": "2026-06-24T00:00:00Z",
        "upstreams": {
            "cccagents-hermes-gateway": "active",
            "cccagents-pm-scheduler": "active",
            "cccagents-feishu-webhook": "active",
            "nginx": "active",
            "gateway_url": "200",
        },
    }
    with patch(
        "cccagents.feishu_webhook_server._check_upstream_health",
        return_value=fake_health,
    ):
        handler.do_GET()

    handler.send_response.assert_called_with(200)
    handler.send_header.assert_called_with("Content-Type", "application/json")
    body = handler.wfile.write.call_args.args[0].decode("utf-8")
    parsed = json.loads(body)
    assert parsed["ok"] is True
    assert parsed["upstreams"]["nginx"] == "active"


def test_webhook_handler_healthz_returns_503_when_unhealthy():
    """GET /healthz must return 503 when any upstream is not active."""
    from unittest.mock import patch

    handler = FeishuWebhookHandler.__new__(FeishuWebhookHandler)
    handler.wfile = MagicMock()
    handler.address_string = lambda: "127.0.0.1"
    handler.path = "/healthz"
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    fake_health = {
        "ok": False,
        "checked_at": "2026-06-24T00:00:00Z",
        "upstreams": {
            "cccagents-hermes-gateway": "inactive",
            "cccagents-pm-scheduler": "active",
            "cccagents-feishu-webhook": "active",
            "nginx": "active",
            "gateway_url": "200",
        },
    }
    with patch(
        "cccagents.feishu_webhook_server._check_upstream_health",
        return_value=fake_health,
    ):
        handler.do_GET()

    handler.send_response.assert_called_with(503)
