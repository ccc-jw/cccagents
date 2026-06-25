"""Tests for :mod:`cccagents.feishu_reply`."""

import json
from unittest.mock import MagicMock, patch

import pytest

from cccagents import feishu_reply


def test_get_tenant_access_token_caches(monkeypatch):
    """The second call within the cache window must not re-fetch."""
    fake_response = MagicMock()
    fake_response.json.return_value = {
        "code": 0,
        "tenant_access_token": "t-xxx",
        "expire": 7200,
    }
    fake_response.raise_for_status = MagicMock()

    # Reset module-level cache.
    feishu_reply._TOKEN_CACHE["token"] = None
    feishu_reply._TOKEN_CACHE["expires_at"] = 0.0

    with patch.dict(
        "os.environ",
        {"FEISHU_APP_ID": "cli_test", "FEISHU_APP_SECRET": "sec_test"},
        clear=False,
    ), patch("cccagents.feishu_reply.requests.post", return_value=fake_response) as mock_post:
        tok1 = feishu_reply.get_tenant_access_token()
        tok2 = feishu_reply.get_tenant_access_token()
        assert tok1 == "t-xxx"
        assert tok2 == "t-xxx"
        # Second call should hit the cache, not re-post.
        assert mock_post.call_count == 1


def test_reply_to_feishu_uses_bearer_token(monkeypatch):
    """The send call must include Bearer auth and the right URL."""
    feishu_reply._TOKEN_CACHE["token"] = "cached-token"
    feishu_reply._TOKEN_CACHE["expires_at"] = 10**12  # far future

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "code": 0,
        "data": {"message_id": "om_out_001"},
    }
    fake_response.raise_for_status = MagicMock()

    with patch.dict(
        "os.environ",
        {"FEISHU_APP_ID": "cli_test", "FEISHU_APP_SECRET": "sec_test"},
        clear=False,
    ), patch("cccagents.feishu_reply.requests.post", return_value=fake_response) as mock_post:
        result = feishu_reply.reply_to_feishu("ou_abc", "hello world")

    assert result["ok"] is True
    assert result["message_id"] == "om_out_001"
    # Auth header
    call_args = mock_post.call_args
    headers = call_args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer cached-token"
    # URL has receive_id_type=open_id
    assert "receive_id_type=open_id" in call_args.args[0]
    # Body
    body = call_args.kwargs["json"]
    assert body["receive_id"] == "ou_abc"
    assert body["msg_type"] == "text"
    assert json.loads(body["content"]) == {"text": "hello world"}


def test_reply_to_feishu_handles_api_error():
    """An API-level error returns ok=False with the Feishu error code."""
    feishu_reply._TOKEN_CACHE["token"] = "cached-token"
    feishu_reply._TOKEN_CACHE["expires_at"] = 10**12

    fake_response = MagicMock()
    fake_response.json.return_value = {"code": 230002, "msg": "user not found"}
    fake_response.raise_for_status = MagicMock()

    with patch.dict(
        "os.environ",
        {"FEISHU_APP_ID": "cli_test", "FEISHU_APP_SECRET": "sec_test"},
        clear=False,
    ), patch("cccagents.feishu_reply.requests.post", return_value=fake_response):
        result = feishu_reply.reply_to_feishu("ou_abc", "hello")

    assert result["ok"] is False
    assert "user not found" in result["error"]
    assert result["code"] == 230002


def test_reply_to_feishu_requires_credentials(monkeypatch):
    """Missing env vars raise so misconfiguration is loud, not silent."""
    # Force the auth call to actually re-fetch by clearing the cache.
    feishu_reply._TOKEN_CACHE["token"] = None
    feishu_reply._TOKEN_CACHE["expires_at"] = 0.0
    monkeypatch.delenv("FEISHU_APP_ID", raising=False)
    monkeypatch.delenv("FEISHU_APP_SECRET", raising=False)
    with pytest.raises(ValueError, match="FEISHU_APP_ID / FEISHU_APP_SECRET"):
        feishu_reply.get_tenant_access_token()
