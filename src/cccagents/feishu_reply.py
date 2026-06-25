"""Send a text reply to a Feishu message via the Open API.

Flow per Feishu docs:
  1. POST {base}/auth/v3/tenant_access_token/internal  →  tenant_access_token
  2. POST {base}/im/v1/messages?receive_id_type=open_id
       with body {"receive_id": "...", "msg_type": "text", "content": "{\"text\":\"...\"}"}
       header: Authorization: Bearer {token}

The base URL for international / Lark is ``https://open.larksuite.com``; for
mainland China Feishu it is ``https://open.feishu.cn``.  We default to the
mainland one because the deployment is on a mainland server.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests


_TOKEN_CACHE: dict[str, Any] = {
    "token": None,
    "expires_at": 0.0,  # epoch seconds
}


def _base_url() -> str:
    return os.getenv("FEISHU_API_BASE", "https://open.feishu.cn")


def _app_credentials() -> tuple[str, str]:
    app_id = os.getenv("FEISHU_APP_ID", "")
    app_secret = os.getenv("FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        raise ValueError("FEISHU_APP_ID / FEISHU_APP_SECRET not set")
    return app_id, app_secret


def get_tenant_access_token() -> str:
    """Return a cached tenant_access_token, refreshing it when expired.

    Feishu tokens are valid for ~2 hours; we cache for 90 minutes so a
    10-minute clock skew never bites us.  Failures raise so the caller can
    decide whether to retry or return an error to the user.
    """
    now = time.time()
    if _TOKEN_CACHE["token"] and _TOKEN_CACHE["expires_at"] > now:
        return _TOKEN_CACHE["token"]  # type: ignore[return-value]

    app_id, app_secret = _app_credentials()
    resp = requests.post(
        f"{_base_url()}/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"tenant_access_token failed: {data}")

    _TOKEN_CACHE["token"] = data["tenant_access_token"]
    _TOKEN_CACHE["expires_at"] = now + data.get("expire", 7200) - 600
    return _TOKEN_CACHE["token"]  # type: ignore[return-value]


def reply_to_feishu(receive_id: str, text: str, receive_id_type: str = "open_id") -> dict:
    """Send a text reply to a user / chat.

    ``receive_id`` is the user's ``open_id`` (default) or a ``chat_id`` (when
    ``receive_id_type="chat_id"``).  ``text`` is the user-facing message.
    Returns the parsed JSON response from Feishu (or ``{"ok": False, "error": ...}``
    on transport failure).

    On a 99991663 ("token invalid") response we invalidate the cached token
    and retry once — Feishu sometimes revokes tokens server-side before
    their stated expiry and the 401 is the only signal we'll get.
    """
    try:
        token = get_tenant_access_token()
    except Exception as exc:  # pragma: no cover - network paths
        return {"ok": False, "error": f"auth: {exc}"}

    body = {
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    url = f"{_base_url()}/open-apis/im/v1/messages?receive_id_type={receive_id_type}"

    for attempt in (1, 2):
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=10)
            data = resp.json()
        except Exception as exc:  # pragma: no cover - network paths
            return {"ok": False, "error": f"send: {exc}"}

        # Token expired server-side — invalidate cache and retry once.
        if data.get("code") == 99991663 and attempt == 1:
            _TOKEN_CACHE["token"] = None
            _TOKEN_CACHE["expires_at"] = 0.0
            try:
                token = get_tenant_access_token()
            except Exception as exc:  # pragma: no cover
                return {"ok": False, "error": f"auth-retry: {exc}"}
            headers["Authorization"] = f"Bearer {token}"
            continue

        if data.get("code") != 0:
            return {"ok": False, "error": data.get("msg", "unknown"), "code": data.get("code")}

        return {"ok": True, "message_id": data.get("data", {}).get("message_id")}

    return {"ok": False, "error": "exhausted retries"}  # pragma: no cover


__all__ = ["get_tenant_access_token", "reply_to_feishu"]
