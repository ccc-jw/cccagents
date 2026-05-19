from cccagents.phase2_models import AgentModelConfig


def executor_env(config: AgentModelConfig, api_key: str) -> dict[str, str]:
    if not api_key:
        raise ValueError("api_key is required")
    return {
        "ANTHROPIC_BASE_URL": config.model_base_url,
        "ANTHROPIC_API_KEY": api_key,
        "ANTHROPIC_MODEL": config.model_name,
    }
