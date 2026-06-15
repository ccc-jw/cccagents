from pathlib import Path

from cccagents.real_orchestrator import RealExecutor, orchestrate_with_real_executor
from cccagents.orchestrator import OrchestrationRequest


def test_real_orchestrator_completes_s0_with_real_executor(tmp_path, monkeypatch):
    """Test that real orchestrator can complete S0 flow with mocked Claude CLI."""
    from unittest.mock import MagicMock, patch

    project_root = tmp_path
    request = OrchestrationRequest(
        project_id="demo-real-s0",
        text="修复 README 里的 typo",
        project_root=project_root,
        now="2026-06-15T10:00:00Z",
    )

    executor = RealExecutor(
        model="gpt-5.5",
        base_url="http://cccai.store",
        api_key="secret://test-key",
    )

    fake_completed = MagicMock()
    fake_completed.stdout = "OK\n"
    fake_completed.stderr = ""
    fake_completed.returncode = 0

    with patch("cccagents.claude_executor.subprocess.run", return_value=fake_completed):
        result = orchestrate_with_real_executor(request, executor, now="2026-06-15T10:00:00Z")

    assert result["status"] == "done"
    assert result["complexity"] == "S0"
    assert "DEV" in result["executed_roles"]
    assert "PM" in result["executed_roles"]

    project_dir = project_root / "demo-real-s0"
    assert (project_dir / "role-plan.json").exists()
    role_plan = (project_dir / "role-plan.json").read_text()
    assert '"complexity": "S0"' in role_plan

    run_dir = project_dir / "08-logs" / "hermes-runs"
    assert run_dir.exists()
    assert len(list(run_dir.iterdir())) > 0


def test_real_orchestrator_blocks_on_failure(tmp_path, monkeypatch):
    """Test that real orchestrator blocks when Claude CLI fails."""
    from unittest.mock import MagicMock, patch

    project_root = tmp_path
    request = OrchestrationRequest(
        project_id="demo-real-fail",
        text="修复 README 里的 typo",
        project_root=project_root,
        now="2026-06-15T10:00:00Z",
    )

    executor = RealExecutor(
        model="gpt-5.5",
        base_url="http://cccai.store",
        api_key="secret://test-key",
    )

    fake_completed = MagicMock()
    fake_completed.stdout = ""
    fake_completed.stderr = "Error"
    fake_completed.returncode = 1

    with patch("cccagents.claude_executor.subprocess.run", return_value=fake_completed):
        result = orchestrate_with_real_executor(request, executor, now="2026-06-15T10:00:00Z")

    assert result["status"] == "blocked"
    assert len(result["issues"]) > 0
