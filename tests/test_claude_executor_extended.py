"""Tests for :mod:`cccagents.claude_executor`.

These tests mock ``claude_executor.subprocess.run`` because the canonical
implementation invokes the locally-installed Claude Code CLI as a child
process (so we get ``--allowedTools`` enforcement and per-run workspace
isolation for free).  Earlier versions of the module talked to the
OpenAI-compatible HTTP gateway directly; those tests were retired when the
CLI subprocess path was adopted.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from cccagents.claude_executor import ClaudeRunRequest, ClaudeRunResult, run_claude_task
from cccagents.paths import ProjectPaths


def _make_request(tmp_path: Path, *, run_id: str, api_key: str = "secret://test-key") -> ClaudeRunRequest:
    project_paths = ProjectPaths(root=tmp_path, project_id="demo")
    project_paths.project_root.mkdir(parents=True, exist_ok=True)
    project_paths.workspace_root.mkdir(parents=True, exist_ok=True)
    return ClaudeRunRequest(
        task_id=f"task-{run_id}",
        role="DEV",
        prompt="只回复 OK",
        workspace_path=project_paths.workspace_root,
        project_dir=project_paths.project_root,
        allowed_tools=["Read", "Write"],
        model="gpt-5.5",
        base_url="https://cccai.store/v1",
        api_key=api_key,
        run_id=run_id,
    )


def test_run_claude_task_writes_prompt_stdout_stderr_and_result(tmp_path):
    """Successful CLI run writes all four artefacts under 08-logs/hermes-runs/<run_id>/."""
    request = _make_request(tmp_path, run_id="run-001")

    fake_completed = MagicMock()
    fake_completed.returncode = 0
    fake_completed.stdout = "OK\n"
    fake_completed.stderr = ""

    with patch("cccagents.claude_executor.subprocess.run", return_value=fake_completed) as mock_run:
        result = run_claude_task(request, now="2026-06-15T10:00:00Z")

    assert isinstance(result, ClaudeRunResult)
    assert result.exit_code == 0
    assert result.run_id == "run-001"
    assert result.stdout == "OK\n"

    run_dir = tmp_path / "projects" / "demo" / "08-logs" / "hermes-runs" / "run-001"
    assert (run_dir / "prompt.md").exists()
    assert (run_dir / "stdout.txt").exists()
    assert (run_dir / "stderr.txt").exists()
    assert (run_dir / "result.json").exists()

    prompt_content = (run_dir / "prompt.md").read_text()
    assert "只回复 OK" in prompt_content
    assert "DEV" in prompt_content

    # The CLI should be invoked with the project credentials in the env so
    # ANTHROPIC_BASE_URL / ANTHROPIC_API_KEY override the user's defaults.
    mock_run.assert_called_once()
    kwargs = mock_run.call_args.kwargs
    assert kwargs["cwd"].endswith("workspaces/demo/repo")
    env = kwargs["env"]
    assert env["ANTHROPIC_BASE_URL"] == "https://cccai.store/v1"
    assert env["ANTHROPIC_API_KEY"] == "secret://test-key"
    assert env["ANTHROPIC_MODEL"] == "gpt-5.5"
    cmd = mock_run.call_args.args[0]
    assert cmd[0] == "claude"
    assert "-p" in cmd
    assert "--model" in cmd
    assert "gpt-5.5" in cmd


def test_run_claude_task_captures_cli_failure(tmp_path):
    """When the CLI exits non-zero we record exit_code=1 and persist stderr."""
    request = _make_request(tmp_path, run_id="run-002")

    fake_completed = MagicMock()
    fake_completed.returncode = 1
    fake_completed.stdout = ""
    fake_completed.stderr = "execution failed"

    with patch("cccagents.claude_executor.subprocess.run", return_value=fake_completed):
        result = run_claude_task(request, now="2026-06-15T10:01:00Z")

    assert result.exit_code == 1
    assert "execution failed" in result.stderr

    run_dir = tmp_path / "projects" / "demo" / "08-logs" / "hermes-runs" / "run-002"
    result_data = json.loads((run_dir / "result.json").read_text())
    assert result_data["exit_code"] == 1
    assert result_data["role"] == "DEV"


def test_run_claude_task_rejects_dangerously_skip_permissions(tmp_path):
    """``--dangerously-skip-permissions`` must always be rejected up-front."""
    request = _make_request(tmp_path, run_id="run-003")

    try:
        run_claude_task(
            request,
            now="2026-06-15T10:02:00Z",
            extra_args=["--dangerously-skip-permissions"],
        )
    except ValueError as exc:
        assert "dangerously-skip-permissions" in str(exc)
    else:
        raise AssertionError("expected ValueError")
