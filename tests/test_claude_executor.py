import pytest

from cccagents.claude_executor import build_claude_command
from cccagents.phase2_models import AgentModelConfig


def test_build_claude_command_uses_prompt_model_and_text_output():
    config = AgentModelConfig(
        role_code="DEV",
        model_base_url="http://cccai.store",
        model_api_key_ref="secret://models/dev",
        model_name="gpt-5.5",
    )

    command = build_claude_command(config, "只回复 OK")

    assert command == [
        "claude",
        "-p",
        "只回复 OK",
        "--model",
        "gpt-5.5",
        "--output-format",
        "text",
    ]


def test_build_claude_command_rejects_empty_prompt():
    config = AgentModelConfig(
        role_code="DEV",
        model_base_url="http://cccai.store",
        model_api_key_ref="secret://models/dev",
        model_name="gpt-5.5",
    )

    with pytest.raises(ValueError, match="prompt is required"):
        build_claude_command(config, "")
