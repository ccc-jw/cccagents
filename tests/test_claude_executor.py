import pytest

from cccagents.claude_executor import ClaudeRunRequest, _build_openai_payload
from pathlib import Path


def _request(prompt: str = "只回复 OK") -> ClaudeRunRequest:
    return ClaudeRunRequest(
        task_id="task-1",
        role="DEV",
        prompt=prompt,
        workspace_path=Path("/tmp/workspace"),
        project_dir=Path("/tmp/project"),
        allowed_tools=["Read", "Write"],
        model="gpt-5.5",
        base_url="https://cccai.store/v1",
        api_key="secret://test-key",
        run_id="run-001",
    )


def test_build_openai_payload_uses_model_and_prompt():
    payload = _build_openai_payload(_request(), "只回复 OK")

    assert payload == {
        "model": "gpt-5.5",
        "messages": [
            {
                "role": "user",
                "content": "只回复 OK",
            }
        ],
    }


def test_build_openai_payload_rejects_empty_prompt():
    with pytest.raises(ValueError, match="prompt is required"):
        _build_openai_payload(_request(prompt=""), "")
