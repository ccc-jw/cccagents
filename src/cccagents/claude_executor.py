from cccagents.phase2_models import AgentModelConfig


def build_claude_command(config: AgentModelConfig, prompt: str) -> list[str]:
    if not prompt:
        raise ValueError("prompt is required")
    return [
        "claude",
        "-p",
        prompt,
        "--model",
        config.model_name,
        "--output-format",
        "text",
    ]
