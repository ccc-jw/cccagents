from pathlib import Path


def test_executor_protocol_documents_required_fields_and_security_rules():
    content = Path("docs/phase2/hermes-claude-executor-protocol.md").read_text(encoding="utf-8")

    for required in [
        "project_id",
        "task_id",
        "run_id",
        "agent_role",
        "phase",
        "cwd",
        "prompt",
        "allowed_tools",
        "permission_mode",
        "env_refs",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "command-log.jsonl",
        "真实 API Key 不得写入",
    ]:
        assert required in content
