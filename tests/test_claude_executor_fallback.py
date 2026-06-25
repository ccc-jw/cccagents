"""Tests for claude_executor's HTTP fallback path.

The canonical ``run_claude_task`` invocation calls the local ``claude`` CLI
as a subprocess.  When that binary is missing (CI, sandbox), the executor
falls back to the OpenAI-compatible HTTP gateway.  These tests exercise
that fallback by injecting a ``FileNotFoundError`` on the subprocess call.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from cccagents.claude_executor import (
    ClaudeRunRequest,
    ClaudeRunResult,
    _http_fallback,
    run_claude_task,
)
from cccagents.paths import ProjectPaths


def _make_request(tmp_path: Path, *, run_id: str = "fb-001", base_url: str = "https://cccai.store/v1") -> ClaudeRunRequest:
    project_paths = ProjectPaths(root=tmp_path, project_id="fb")
    project_paths.project_root.mkdir(parents=True, exist_ok=True)
    project_paths.workspace_root.mkdir(parents=True, exist_ok=True)
    return ClaudeRunRequest(
        task_id="t-fb",
        role="DEV",
        prompt="fallback test",
        workspace_path=project_paths.workspace_root,
        project_dir=project_paths.project_root,
        allowed_tools=["Read"],
        model="gpt-5.5",
        base_url=base_url,
        api_key="fb-test-key",
        run_id=run_id,
    )


def test_run_claude_task_falls_back_when_claude_missing(tmp_path):
    """subprocess.run raising FileNotFoundError must trigger HTTP fallback."""
    request = _make_request(tmp_path)

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"choices": [{"message": {"content": "fallback OK"}}]}

    with patch("cccagents.claude_executor.subprocess.run", side_effect=FileNotFoundError("claude")):
        with patch("cccagents.claude_executor.requests.post", return_value=fake_response) as mock_post:
            result = run_claude_task(request, now="2026-06-24T00:00:00Z")

    assert isinstance(result, ClaudeRunResult)
    assert result.exit_code == 0
    assert result.stdout == "fallback OK"
    # The fallback hit the right endpoint.
    assert mock_post.call_args.args[0] == "https://cccai.store/v1/chat/completions"
    # Authorization header carried our key.
    assert mock_post.call_args.kwargs["headers"]["Authorization"] == "Bearer fb-test-key"


def test_run_claude_task_fallback_surfaces_http_error(tmp_path):
    """If the gateway returns 401, fallback reports it as exit_code=1."""
    request = _make_request(tmp_path)

    fake_response = MagicMock()
    fake_response.status_code = 401
    fake_response.text = "Unauthorized"

    with patch("cccagents.claude_executor.subprocess.run", side_effect=FileNotFoundError("claude")):
        with patch("cccagents.claude_executor.requests.post", return_value=fake_response):
            result = run_claude_task(request, now="2026-06-24T00:00:00Z")

    assert result.exit_code == 1
    assert "HTTP 401" in result.stderr
    assert "Unauthorized" in result.stderr
    assert "claude" in result.stderr  # the FileNotFoundError note is included


def test_run_claude_task_fallback_writes_artifacts(tmp_path):
    """The fallback path must persist prompt.md / stdout.txt / stderr.txt / result.json."""
    request = _make_request(tmp_path)

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}

    with patch("cccagents.claude_executor.subprocess.run", side_effect=FileNotFoundError("claude")):
        with patch("cccagents.claude_executor.requests.post", return_value=fake_response):
            run_claude_task(request, now="2026-06-24T00:00:00Z")

    run_dir = tmp_path / "projects" / "fb" / "08-logs" / "hermes-runs" / "fb-001"
    assert (run_dir / "prompt.md").exists()
    assert (run_dir / "stdout.txt").read_text() == "ok"
    assert (run_dir / "stderr.txt").exists()
    assert (run_dir / "result.json").exists()


def test_http_fallback_returns_0_on_success():
    """Direct test of ``_http_fallback`` with a 200 response."""
    request = ClaudeRunRequest(
        task_id="t1",
        role="DEV",
        prompt="x",
        workspace_path=Path("/tmp/w"),
        project_dir=Path("/tmp/p"),
        allowed_tools=[],
        model="gpt-5.5",
        base_url="https://api.example/v1",
        api_key="k",
        run_id="r1",
    )
    fake = MagicMock()
    fake.status_code = 200
    fake.json.return_value = {"choices": [{"message": {"content": "hello"}}]}
    with patch("cccagents.claude_executor.requests.post", return_value=fake) as mock_post:
        code, stdout, stderr = _http_fallback(request, "ignored prompt", "claude missing")

    assert code == 0
    assert stdout == "hello"
    assert "claude missing" in stderr


def test_http_fallback_returns_1_on_5xx():
    """Direct test of ``_http_fallback`` with a 503 response."""
    request = ClaudeRunRequest(
        task_id="t1",
        role="DEV",
        prompt="x",
        workspace_path=Path("/tmp/w"),
        project_dir=Path("/tmp/p"),
        allowed_tools=[],
        model="gpt-5.5",
        base_url="https://api.example/v1",
        api_key="k",
        run_id="r1",
    )
    fake = MagicMock()
    fake.status_code = 503
    fake.text = "service unavailable"
    with patch("cccagents.claude_executor.requests.post", return_value=fake):
        code, stdout, stderr = _http_fallback(request, "ignored", "claude missing")

    assert code == 1
    assert stdout == ""
    assert "HTTP 503" in stderr
    assert "service unavailable" in stderr
    assert "claude missing" in stderr  # note preserved


def test_http_fallback_handles_network_exception():
    """If requests.post raises (timeout, connection refused), fallback returns 1."""
    import requests as real_requests

    request = ClaudeRunRequest(
        task_id="t1",
        role="DEV",
        prompt="x",
        workspace_path=Path("/tmp/w"),
        project_dir=Path("/tmp/p"),
        allowed_tools=[],
        model="gpt-5.5",
        base_url="https://api.example/v1",
        api_key="k",
        run_id="r1",
    )
    with patch(
        "cccagents.claude_executor.requests.post",
        side_effect=real_requests.exceptions.ConnectionError("refused"),
    ):
        code, stdout, stderr = _http_fallback(request, "ignored", "claude missing")

    assert code == 1
    assert stdout == ""
    assert "refused" in stderr
    assert "claude missing" in stderr


def test_http_fallback_strips_trailing_slash_from_base_url():
    """A base_url ending in ``/`` must not produce a doubled slash."""
    request = ClaudeRunRequest(
        task_id="t1",
        role="DEV",
        prompt="x",
        workspace_path=Path("/tmp/w"),
        project_dir=Path("/tmp/p"),
        allowed_tools=[],
        model="gpt-5.5",
        base_url="https://api.example/v1/",
        api_key="k",
        run_id="r1",
    )
    fake = MagicMock()
    fake.status_code = 200
    fake.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
    with patch("cccagents.claude_executor.requests.post", return_value=fake) as mock_post:
        _http_fallback(request, "ignored", "")
    assert mock_post.call_args.args[0] == "https://api.example/v1/chat/completions"