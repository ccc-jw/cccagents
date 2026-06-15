import pytest

from cccagents.claude_executor import ClaudeRunRequest, _build_command
from pathlib import Path


def test_build_command_uses_prompt_model_and_text_output():
    request = ClaudeRunRequest(
        task_id="task-1",
        role="DEV",
        prompt="只回复 OK",
        workspace_path=Path("/tmp/workspace"),
        project_dir=Path("/tmp/project"),
        allowed_tools=["Read", "Write"],
        model="gpt-5.5",
        base_url="http://cccai.store",
        api_key="secret://test-key",
        run_id="run-001",
    )

    command = _build_command(request, "只回复 OK")

    assert command == [
        "claude",
        "-p",
        "只回复 OK",
        "--model",
        "gpt-5.5",
        "--output-format",
        "text",
    ]


def test_build_command_rejects_empty_prompt():
    request = ClaudeRunRequest(
        task_id="task-1",
        role="DEV",
        prompt="",
        workspace_path=Path("/tmp/workspace"),
        project_dir=Path("/tmp/project"),
        allowed_tools=["Read"],
        model="gpt-5.5",
        base_url="http://cccai.store",
        api_key="secret://test-key",
        run_id="run-001",
    )

    with pytest.raises(ValueError, match="prompt is required"):
        _build_command(request, "")
