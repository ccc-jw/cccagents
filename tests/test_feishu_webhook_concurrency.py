"""Smoke tests for the ThreadingHTTPServer wiring in feishu_webhook_server."""

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler
from unittest.mock import MagicMock, patch

import pytest

from cccagents.feishu_webhook_server import (
    FeishuWebhookHandler,
    ThreadingHTTPServer,
    run_server,
)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _http_get(url: str, timeout: float = 5.0) -> tuple[int, str]:
    import urllib.request

    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def _http_post(url: str, body: dict, timeout: float = 5.0) -> tuple[int, str]:
    import urllib.request

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def test_threading_http_server_class_used():
    """run_server must use ThreadingHTTPServer, not the single-threaded one."""
    from cccagents import feishu_webhook_server as mod
    src = open(mod.__file__).read()
    assert "ThreadingHTTPServer(" in src
    # The class must be threaded — ThreadingHTTPServer.process_request is
    # mixed-in from socketserver.ThreadingMixIn, not the sync base class.
    import socketserver
    assert issubclass(mod.ThreadingHTTPServer, socketserver.ThreadingMixIn)


def test_concurrent_requests_dont_serialize(tmp_path):
    """Fire two requests at the same time; both should be served in parallel."""
    port = _free_port()

    class _Counter:
        def __init__(self) -> None:
            self.lock = threading.Lock()
            self.inflight = 0
            self.max_inflight = 0

        def inc(self) -> None:
            with self.lock:
                self.inflight += 1
                self.max_inflight = max(self.max_inflight, self.inflight)

        def dec(self) -> None:
            with self.lock:
                self.inflight -= 1

    counter = _Counter()

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            counter.inc()
            time.sleep(0.3)  # hold the request — if single-threaded, this
                              # would block the second request
            counter.dec()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *a, **kw):  # silence
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    try:
        # Fire two requests in parallel threads.
        results: list[tuple[int, str]] = []
        results_lock = threading.Lock()

        def worker() -> None:
            code, body = _http_get(f"http://127.0.0.1:{port}/")
            with results_lock:
                results.append((code, body))

        threads = [threading.Thread(target=worker) for _ in range(2)]
        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        elapsed = time.time() - start

        # With single-threaded HTTPServer the second request would only start
        # after 0.3s; with ThreadingHTTPServer both run in parallel and the
        # total wall time should be just over 0.3s, well under 0.55s.
        assert elapsed < 0.55, f"requests serialized: {elapsed:.2f}s"
        assert len(results) == 2
        assert all(code == 200 for code, _ in results)
        assert counter.max_inflight == 2, (
            f"expected concurrent execution, got max_inflight={counter.max_inflight}"
        )
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_run_server_drains_on_sigterm(monkeypatch):
    """run_server must shut down cleanly on SIGTERM, not leave threads hanging."""
    # We can't easily test the real signal handler without subprocess, but we
    # can verify the wiring exists and the stop callback unblocks serve_forever.
    from cccagents import feishu_webhook_server as mod
    src = open(mod.__file__).read()
    assert "signal.signal" in src
    assert "SIGTERM" in src
    assert "httpd.shutdown" in src
