import pytest

from cccagents.agent_config import executor_env
from cccagents.phase2_models import AgentModelConfig


def test_executor_env_maps_agent_model_config_to_anthropic_env():
    config = AgentModelConfig(
        role_code="DEV",
        model_base_url="http://cccai.store",
        model_api_key_ref="secret://models/dev",
        model_name="gpt-5.5",
    )

    env = executor_env(config, api_key="secret-value")

    assert env == {
        "ANTHROPIC_BASE_URL": "http://cccai.store",
        "ANTHROPIC_API_KEY": "secret-value",
        "ANTHROPIC_MODEL": "gpt-5.5",
    }


def test_executor_env_rejects_empty_secret():
    config = AgentModelConfig(
        role_code="DEV",
        model_base_url="http://cccai.store",
        model_api_key_ref="secret://models/dev",
        model_name="gpt-5.5",
    )

    with pytest.raises(ValueError, match="api_key is required"):
        executor_env(config, api_key="")
