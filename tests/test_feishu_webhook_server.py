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
        # Mock handle_approval_webhook to avoid file operations
        with patch('cccagents.feishu_webhook_server.handle_approval_webhook') as mock_handle:
            mock_handle.return_value = {
                "success": True,
                "project_id": "test-project",
                "action": "approve",
                "approved": True,
                "reason": "approved",
                "event_id": "evt_123"
            }

            # Call do_POST
            handler.do_POST()

            # Verify response
            handler.send_response.assert_called_with(200)
            handler.send_header.assert_called_with("Content-Type", "application/json")
            handler.end_headers.assert_called()

            # Verify handle_approval_webhook was called
            assert mock_handle.called
            call_args = mock_handle.call_args
            assert call_args.kwargs["project_root"] == Path("/tmp/test-projects")
            assert call_args.kwargs["allowed_approvers"] == {"user_456"}
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
        handler.do_POST()

        # Should still return 200 with error in response body
        handler.send_response.assert_called_with(200)


def test_webhook_handler_health_check():
    """Test that GET request returns health check response."""
    handler = FeishuWebhookHandler.__new__(FeishuWebhookHandler)
    handler.wfile = MagicMock()
    handler.address_string = lambda: "127.0.0.1"

    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()

    handler.do_GET()

    handler.send_response.assert_called_with(200)
    handler.send_header.assert_called_with("Content-Type", "text/plain")
    handler.end_headers.assert_called()
    handler.wfile.write.assert_called_with(b"Feishu webhook server is running\n")
