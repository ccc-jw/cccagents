import json
import os
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from cccagents.feishu_webhook import (
    DispatchResult,
    dispatch_event,
    handle_challenge,
)
from cccagents.metrics import METRICS
from cccagents.redaction import redact_text


# Track in-flight requests so the server can drain on SIGTERM.
_INFLIGHT = threading.Semaphore(value=10)  # cap concurrent requests


class FeishuWebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler for Feishu approval webhook events."""

    def do_POST(self):
        """Handle POST request from Feishu webhook.

        Routes to one of:
          - dispatch_event: approval / message / url_verification
          - 400 for malformed payloads
        """
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")

        # Redact sensitive data before logging
        redacted = redact_text(post_data)
        print(f"Received webhook: {redacted.text[:200]}...", flush=True)

        # Parse configuration from environment
        project_root = Path(os.getenv("CCCAGENTS_PROJECT_ROOT", "/home/ubuntu/cccagents/projects"))
        allowed_senders = set(
            s for s in os.getenv("FEISHU_ALLOWED_USERS", "").split(",") if s
        )
        allowed_approvers = allowed_senders  # same allowlist for now
        expected_signature = os.getenv("FEISHU_VERIFICATION_TOKEN", "")

        # Get current timestamp
        from datetime import datetime
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # We don't know the handler name until after dispatch_event runs, so
        # we use a placeholder first and then bucket the final outcome.
        with METRICS.time("post", "received"):
            try:
                result = dispatch_event(
                    payload=post_data,
                    project_root=project_root,
                    allowed_senders=allowed_senders,
                    allowed_approvers=allowed_approvers,
                    expected_signature=expected_signature,
                    now=now,
                )
            except Exception as e:
                print(f"Error processing webhook: {e}", flush=True)
                import traceback
                traceback.print_exc()
                METRICS.inc("post", "exception")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                error_response = json.dumps({"error": str(e)})
                self.wfile.write(error_response.encode("utf-8"))
                return

            METRICS.inc(result.handler, "ok" if result.success else "fail")
            if result.handler == "message":
                # /metrics is the only place that needs this breakdown.
                pass

        # Build the response envelope.  For url_verification we return the
        # challenge echoed (rare but supported).  For other handlers the
        # dispatcher's detail already contains the right shape.
        if result.handler == "url_verification":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"challenge": result.detail.get("challenge", "")}).encode("utf-8"))
            return

        if result.handler == "url_verification_encrypted":
            # Modern Feishu URL-verification POST: Feishu expects a JSON body
            # of the form {"challenge": "<base64-ciphertext>"}.  The verifier
            # decrypts it client-side using its Encrypt Key and checks the
            # inner challenge matches what it sent.
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            body = json.dumps({"challenge": result.detail.get("challenge", "")})
            self.wfile.write(body.encode("utf-8"))
            return

        body = {
            "dispatched_to": result.handler,
            "success": result.success,
            **result.detail,
        }
        status_code = 200 if result.success else 400
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode("utf-8"))
        print(f"Webhook dispatched: handler={result.handler} success={result.success}", flush=True)

    def do_GET(self):
        """Handle GET request — health check OR Feishu URL-verification challenge.

        Three sub-paths:
          1. /healthz — returns overall health (probes upstream services)
          2. /metrics — returns Prometheus text exposition
          3. /webhook/feishu?echostr=… — Feishu URL verification
          4. any other path — health probe JSON (back-compat for old health URL)
        """
        # /metrics: Prometheus exposition
        if self.path.startswith("/metrics"):
            with METRICS.time("metrics", "ok"):
                body = METRICS.render()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body.encode("utf-8"))))
            self.end_headers()
            self.wfile.write(body.encode("utf-8"))
            return

        # /healthz: probe upstream services and return combined health JSON
        if self.path.startswith("/healthz"):
            health = _check_upstream_health()
            status_code = 200 if health["ok"] else 503
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(health, ensure_ascii=False).encode("utf-8"))
            return

        query = urlsplit(self.path).query
        encrypt_key = os.getenv("FEISHU_ENCRYPT_KEY", "")

        result = handle_challenge(query_string=query, encrypt_key=encrypt_key)

        if result.mode == "health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(result.body.encode("utf-8"))
            return

        if not result.ok:
            print(f"Challenge failed: mode={result.mode} reason={result.reason}", flush=True)
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(result.body.encode("utf-8"))
            return

        # OK — return challenge body as-is.
        if result.mode == "encrypted":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
        else:  # plain
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(result.body.encode("utf-8"))

    def log_message(self, format, *args):
        """Override to use print for better logging."""
        print(f"{self.address_string()} - {format % args}", flush=True)


def _check_upstream_health() -> dict:
    """Probe upstream services and return a combined health snapshot.

    Returns a JSON-serialisable dict like::

        {
          "ok": true,
          "checked_at": "2026-06-24T14:30:00Z",
          "upstreams": {
            "hermes_gateway": "active",
            "pm_scheduler":  "active",
            "feishu_webhook": "active",
            "nginx":          "active",
            "gateway_url":    "200"
          }
        }

    The endpoint returns 200 when every upstream reports healthy; 503 if any
    check fails.  We deliberately do not raise on individual failures — the
    caller can decide which failures matter.
    """
    import subprocess
    from datetime import datetime

    services = (
        "cccagents-hermes-gateway",
        "cccagents-pm-scheduler",
        "cccagents-feishu-webhook",
        "nginx",
    )
    upstreams: dict[str, str] = {}
    ok = True

    for svc in services:
        try:
            state = subprocess.run(
                ["systemctl", "is-active", svc],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            ).stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            state = f"error: {type(exc).__name__}"
        upstreams[svc] = state
        # Expose each upstream as a gauge so Prometheus can alert on stale.
        METRICS.set_gauge("cccagents_webhook_upstream_health", svc, 1.0 if state == "active" else 0.0)
        if state != "active":
            ok = False

    # Probe the configured gateway URL with a 3s timeout.  200/401/403 are all
    # "reachable"; timeout / refused = unreachable.
    gateway_url = os.getenv("ANTHROPIC_BASE_URL", "").rstrip("/")
    if gateway_url:
        probe = gateway_url + "/v1/models"
        try:
            code = subprocess.run(
                ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
                 "--max-time", "3", probe],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            ).stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            code = "000"
        upstreams["gateway_url"] = code
        if code in ("", "000"):
            ok = False
    else:
        upstreams["gateway_url"] = "not configured"

    return {
        "ok": ok,
        "checked_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "upstreams": upstreams,
    }


def run_server(port=8080):
    """Run the webhook server with graceful shutdown and per-request threads.

    The original implementation used ``HTTPServer`` (single-threaded); with
    more than one Feishu event landing at once (approval + message + the
    5-min health-check POST), requests would queue.  We swap in
    ``ThreadingHTTPServer`` and install SIGINT/SIGTERM handlers that call
    ``server.shutdown()`` so systemd can stop us cleanly without dropping
    in-flight requests.
    """
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, FeishuWebhookHandler)
    print(f"Starting Feishu webhook server on port {port}...", flush=True)
    print(f"Project root: {os.getenv('CCCAGENTS_PROJECT_ROOT', '/home/ubuntu/cccagents/projects')}", flush=True)
    print(f"Allowed approvers: {os.getenv('FEISHU_ALLOWED_USERS', 'not set')}", flush=True)
    print(f"Concurrency cap: {_INFLIGHT._value}", flush=True)

    stop_event = threading.Event()

    def _stop(signum, frame):  # noqa: ARG001
        print(f"Received signal {signum}, shutting down...", flush=True)
        stop_event.set()
        # shutdown() must be called from another thread; serve_forever()
        # unblocks when shutdown() is invoked.
        threading.Thread(target=httpd.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()
        print("Webhook server stopped.", flush=True)


if __name__ == "__main__":
    port = int(os.getenv("WEBHOOK_PORT", "8080"))
    run_server(port)
