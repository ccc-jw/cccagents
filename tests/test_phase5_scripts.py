from pathlib import Path


def test_phase5_preflight_script_exists_and_checks_core_dependencies():
    script = Path("scripts/phase5/preflight_check.sh")
    content = script.read_text(encoding="utf-8")

    assert "python3 --version" in content
    assert "node --version" in content
    assert "npm --version" in content
    assert "claude --version" in content
    assert "hermes --help" in content
    assert "cccai.store" in content
    assert "GATEWAY_ALLOW_ALL_USERS=false" in content
    assert "gpt-5.5" in content
