import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from cccagents.claude_executor import ClaudeRunRequest, ClaudeRunResult, run_claude_task
from cccagents.paths import ProjectPaths


def test_run_claude_task_writes_prompt_stdout_stderr_and_result(tmp_path):
    project_paths = ProjectPaths(root=tmp_path, project_id="demo")
    project_paths.project_root.mkdir(parents=True, exist_ok=True)
    project_paths.workspace_root.mkdir(parents=True, exist_ok=True)

    request = ClaudeRunRequest(
        task_id="task-1",
        role="DEV",
        prompt="只回复 OK",
        workspace_path=project_paths.workspace_root,
        project_dir=project_paths.project_root,
        allowed_tools=["Read", "Write"],
        model="gpt-5.5",
        base_url="http://cccai.store",
        api_key="secret://test-key",
        run_id="run-001",
    )

    fake_completed = MagicMock()
    fake_completed.stdout = "OK\n"
    fake_completed.stderr = ""
    fake_completed.returncode = 0

    with patch("cccagents.claude_executor.subprocess.run", return_value=fake_completed) as mock_run:
        result = run_claude_task(request, now="2026-06-15T10:00:00Z")

    assert isinstance(result, ClaudeRunResult)
    assert result.exit_code == 0
    assert result.run_id == "run-001"

    run_dir = project_paths.run_log_dir("run-001")
    assert (run_dir / "prompt.md").exists()
    assert (run_dir / "stdout.txt").exists()
    assert (run_dir / "stderr.txt").exists()
    assert (run_dir / "result.json").exists()

    prompt_content = (run_dir / "prompt.md").read_text()
    assert "只回复 OK" in prompt_content
    assert "DEV" in prompt_content

    call_args = mock_run.call_args
    assert "claude" in call_args.args[0]
    assert "--model" in call_args.args[0]
    assert "gpt-5.5" in call_args.args[0]


def test_run_claude_task_captures_non_zero_exit_code(tmp_path):
    project_paths = ProjectPaths(root=tmp_path, project_id="demo")
    project_paths.project_root.mkdir(parents=True, exist_ok=True)
    project_paths.workspace_root.mkdir(parents=True, exist_ok=True)

    request = ClaudeRunRequest(
        task_id="task-2",
        role="DEV",
        prompt="执行失败的任务",
        workspace_path=project_paths.workspace_root,
        project_dir=project_paths.project_root,
        allowed_tools=["Read"],
        model="gpt-5.5",
        base_url="http://cccai.store",
        api_key="secret://test-key",
        run_id="run-002",
    )

    fake_completed = MagicMock()
    fake_completed.stdout = ""
    fake_completed.stderr = "Error occurred"
    fake_completed.returncode = 1

    with patch("cccagents.claude_executor.subprocess.run", return_value=fake_completed):
        result = run_claude_task(request, now="2026-06-15T10:01:00Z")

    assert result.exit_code == 1
    assert "Error occurred" in result.stderr

    run_dir = project_paths.run_log_dir("run-002")
    result_json = (run_dir / "result.json").read_text()
    assert '"exit_code": 1' in result_json


def test_run_claude_task_rejects_dangerously_skip_permissions(tmp_path):
    project_paths = ProjectPaths(root=tmp_path, project_id="demo")

    request = ClaudeRunRequest(
        task_id="task-3",
        role="DEV",
        prompt="test",
        workspace_path=project_paths.workspace_root,
        project_dir=project_paths.project_root,
        allowed_tools=["Read"],
        model="gpt-5.5",
        base_url="http://cccai.store",
        api_key="secret://test-key",
        run_id="run-003",
    )

    try:
        run_claude_task(request, now="2026-06-15T10:02:00Z", extra_args=["--dangerously-skip-permissions"])
    except ValueError as exc:
        assert "dangerously-skip-permissions" in str(exc)
    else:
        raise AssertionError("expected ValueError")
