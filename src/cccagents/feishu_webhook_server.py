import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from cccagents.feishu_webhook import handle_approval_webhook
from cccagents.redaction import redact_text


class FeishuWebhookHandler(BaseHTTPRequestHandler):
    """HTTP handler for Feishu approval webhook events."""

    def do_POST(self):
        """Handle POST request from Feishu webhook."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")

        # Redact sensitive data before logging
        redacted = redact_text(post_data)
        print(f"Received webhook: {redacted.text[:200]}...", flush=True)

        # Parse configuration from environment
        project_root = Path(os.getenv("CCCAGENTS_PROJECT_ROOT", "/home/ubuntu/cccagents/projects"))
        allowed_approvers = set(os.getenv("FEISHU_ALLOWED_USERS", "").split(","))
        expected_signature = os.getenv("FEISHU_VERIFICATION_TOKEN", "")

        # Get current timestamp
        from datetime import datetime
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # Handle the webhook
        try:
            result = handle_approval_webhook(
                payload=post_data,
                project_root=project_root,
                allowed_approvers=allowed_approvers,
                expected_signature=expected_signature,
                now=now,
            )

            # Send response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = json.dumps(result, ensure_ascii=False)
            self.wfile.write(response.encode("utf-8"))

            print(f"Webhook processed: {result}", flush=True)

        except Exception as e:
            print(f"Error processing webhook: {e}", flush=True)
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_response = json.dumps({"error": str(e)})
            self.wfile.write(error_response.encode("utf-8"))

    def do_GET(self):
        """Handle GET request for health check."""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Feishu webhook server is running\n")

    def log_message(self, format, *args):
        """Override to use print for better logging."""
        print(f"{self.address_string()} - {format % args}", flush=True)


def run_server(port=8080):
    """Run the webhook server."""
    server_address = ("", port)
    httpd = HTTPServer(server_address, FeishuWebhookHandler)
    print(f"Starting Feishu webhook server on port {port}...", flush=True)
    print(f"Project root: {os.getenv('CCCAGENTS_PROJECT_ROOT', '/home/ubuntu/cccagents/projects')}", flush=True)
    print(f"Allowed approvers: {os.getenv('FEISHU_ALLOWED_USERS', 'not set')}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    port = int(os.getenv("WEBHOOK_PORT", "8080"))
    run_server(port)
