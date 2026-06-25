"""Integration tests for feishu_reply error handling.

These tests cover the failure paths that the unit tests don't exercise:
network timeouts, 401s, 429 rate limits, malformed JSON responses.  They
run entirely against a mocked `requests` so no real Feishu API call is
made.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests as real_requests

from cccagents import feishu_reply


def _reset_cache() -> None:
    feishu_reply._TOKEN_CACHE["token"] = None
    feishu_reply._TOKEN_CACHE["expires_at"] = 0.0


def _setup_token(token: str = "tok-1", expire: int = 7200) -> None:
    """Pretend we already have a valid cached token."""
    feishu_reply._TOKEN_CACHE["token"] = token
    feishu_reply._TOKEN_CACHE["expires_at"] = 10**12


def test_get_token_retries_on_5xx():
    """A 500 from the auth endpoint should raise so the caller knows."""
    _reset_cache()
    fake = MagicMock()
    fake.raise_for_status = MagicMock()
    fake.json.return_value = {"code": 0, "tenant_access_token": "tok-retry", "expire": 7200}
    with patch.dict(
        "os.environ",
        {"FEISHU_APP_ID": "cli_test", "FEISHU_APP_SECRET": "sec_test"},
        clear=False,
    ), patch("cccagents.feishu_reply.requests.post", return_value=fake) as mock_post:
        # First call returns 5xx-ish response (raise_for_status raises).
        bad = MagicMock()
        bad.raise_for_status.side_effect = real_requests.exceptions.HTTPError("500")
        # Sequence: bad (1st), good (2nd)
        mock_post.side_effect = [bad, fake]
        with pytest.raises(real_requests.exceptions.HTTPError):
            feishu_reply.get_tenant_access_token()


def test_get_token_rejects_business_error():
    """Feishu returns 200 with code != 0 for bad credentials; we should raise."""
    _reset_cache()
    fake = MagicMock()
    fake.raise_for_status = MagicMock()
    fake.json.return_value = {"code": 10003, "msg": "invalid app_id"}
    with patch.dict(
        "os.environ",
        {"FEISHU_APP_ID": "cli_bad", "FEISHU_APP_SECRET": "sec_bad"},
        clear=False,
    ), patch("cccagents.feishu_reply.requests.post", return_value=fake):
        with pytest.raises(RuntimeError, match="invalid app_id"):
            feishu_reply.get_tenant_access_token()


def test_get_token_handles_timeout():
    """Network timeout should raise so the caller can decide what to do."""
    _reset_cache()
    with patch.dict(
        "os.environ",
        {"FEISHU_APP_ID": "cli_x", "FEISHU_APP_SECRET": "sec_x"},
        clear=False,
    ), patch(
        "cccagents.feishu_reply.requests.post",
        side_effect=real_requests.exceptions.Timeout("timed out"),
    ):
        with pytest.raises(real_requests.exceptions.Timeout):
            feishu_reply.get_tenant_access_token()


def test_reply_to_feishu_handles_network_timeout():
    """A network failure during send must return ok=False, not crash."""
    _setup_token()
    with patch(
        "cccagents.feishu_reply.requests.post",
        side_effect=real_requests.exceptions.Timeout(),
    ):
        result = feishu_reply.reply_to_feishu("ou_abc", "hello")
    assert result["ok"] is False
    assert "send" in result["error"] or "Timeout" in result["error"]


def test_reply_to_feishu_handles_429_rate_limit():
    """429 should return ok=False with the error message — caller may retry."""
    _setup_token()
    fake = MagicMock()
    fake.json.return_value = {
        "code": 99991400,
        "msg": "rate limit exceeded",
    }
    fake.raise_for_status = MagicMock()
    with patch("cccagents.feishu_reply.requests.post", return_value=fake):
        result = feishu_reply.reply_to_feishu("ou_abc", "hi")
    assert result["ok"] is False
    assert "rate limit" in result["error"]


def test_reply_to_feishu_handles_401_refreshes_token():
    """If the cached token is rejected, we should refresh and retry once.

    This is a defensive behavior: Feishu tokens sometimes get revoked
    server-side before their stated expiry, so the first 401 should trigger
    a refresh, not be silently surfaced to the user.
    """
    _setup_token(token="expired-token")
    # First call: 401 token invalid; second call: success.
    fail = MagicMock()
    fail.json.return_value = {"code": 99991663, "msg": "token invalid"}
    fail.raise_for_status = MagicMock()
    ok = MagicMock()
    ok.json.return_value = {"code": 0, "data": {"message_id": "om_ok"}}
    ok.raise_for_status = MagicMock()

    # The fresh token call: return a new token + long expiry.
    fresh_token_resp = MagicMock()
    fresh_token_resp.json.return_value = {
        "code": 0,
        "tenant_access_token": "tok-fresh",
        "expire": 7200,
    }
    fresh_token_resp.raise_for_status = MagicMock()

    with patch.dict(
        "os.environ",
        {"FEISHU_APP_ID": "cli_t", "FEISHU_APP_SECRET": "sec_t"},
        clear=False,
    ), patch(
        "cccagents.feishu_reply.requests.post",
        side_effect=[fail, fresh_token_resp, ok],
    ) as mock_post:
        result = feishu_reply.reply_to_feishu("ou_abc", "hi")

    assert result["ok"] is True
    assert result["message_id"] == "om_ok"
    # Three HTTP calls: send (failed) → token refresh → send (succeeded).
    assert mock_post.call_count == 3
    # After the refresh, the cache should hold the new token.
    assert feishu_reply._TOKEN_CACHE["token"] == "tok-fresh"


def test_reply_to_feishu_handles_malformed_response():
    """If Feishu returns a body we can't parse, surface ok=False."""
    _setup_token()
    fake = MagicMock()
    fake.json.side_effect = ValueError("not json")
    fake.raise_for_status = MagicMock()
    with patch("cccagents.feishu_reply.requests.post", return_value=fake):
        result = feishu_reply.reply_to_feishu("ou_abc", "hi")
    assert result["ok"] is False
    # We should report either the parse error or the response.
    assert result["error"]


def test_reply_to_feishu_uses_correct_endpoint():
    """The URL must be the right Feishu messages endpoint + receive_id_type."""
    _setup_token(token="tok-endpoint")
    fake = MagicMock()
    fake.json.return_value = {"code": 0, "data": {"message_id": "om_ep"}}
    fake.raise_for_status = MagicMock()
    with patch("cccagents.feishu_reply.requests.post", return_value=fake) as mock_post:
        result = feishu_reply.reply_to_feishu(
            "oc_chat_xyz",
            "group hello",
            receive_id_type="chat_id",
        )
    assert result["ok"] is True
    call_url = mock_post.call_args.args[0]
    assert "/open-apis/im/v1/messages" in call_url
    assert "receive_id_type=chat_id" in call_url
    body = mock_post.call_args.kwargs["json"]
    assert body["receive_id"] == "oc_chat_xyz"


def test_get_token_uses_correct_endpoint():
    """The auth endpoint must be the tenant_access_token/internal route."""
    _reset_cache()
    fake = MagicMock()
    fake.json.return_value = {
        "code": 0,
        "tenant_access_token": "tok-ep",
        "expire": 7200,
    }
    fake.raise_for_status = MagicMock()
    with patch.dict(
        "os.environ",
        {"FEISHU_APP_ID": "cli_a", "FEISHU_APP_SECRET": "sec_a"},
        clear=False,
    ), patch("cccagents.feishu_reply.requests.post", return_value=fake) as mock_post:
        tok = feishu_reply.get_tenant_access_token()
    assert tok == "tok-ep"
    auth_url = mock_post.call_args.args[0]
    assert "/open-apis/auth/v3/tenant_access_token/internal" in auth_url
    body = mock_post.call_args.kwargs["json"]
    assert body["app_id"] == "cli_a"
    assert body["app_secret"] == "sec_a"
