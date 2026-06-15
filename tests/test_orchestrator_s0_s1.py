from cccagents.orchestrator import FakeExecutor, OrchestrationRequest, orchestrate_request
from cccagents.project_state import load_project_state


def test_orchestrator_completes_s0_with_dev_only(tmp_path):
    result = orchestrate_request(
        OrchestrationRequest(
            project_id="demo-s0",
            text="修复 README 里的 typo",
            project_root=tmp_path,
            now="2026-06-13T10:00:00Z",
        ),
        executor=FakeExecutor(),
    )

    state = load_project_state(tmp_path / "demo-s0")

    assert result.status == "done"
    assert state.status == "done"
    assert state.complexity == "S0"
    assert result.executed_roles == ["DEV", "DEV", "PM"]
    assert (tmp_path / "demo-s0" / "05-development" / "dev-summary.md").exists()
    assert (tmp_path / "demo-s0" / "07-acceptance" / "acceptance-report.md").exists()


def test_orchestrator_completes_s1_with_dev_and_test(tmp_path):
    result = orchestrate_request(
        OrchestrationRequest(
            project_id="demo-s1",
            text="修复登录按钮 loading 的局部 bug，并跑本地测试",
            project_root=tmp_path,
            now="2026-06-13T10:00:00Z",
        ),
        executor=FakeExecutor(),
    )

    state = load_project_state(tmp_path / "demo-s1")

    assert result.status == "done"
    assert state.status == "done"
    assert state.complexity == "S1"
    assert result.executed_roles == ["DEV", "DEV", "TEST", "PM"]
    assert (tmp_path / "demo-s1" / "04-test-cases" / "test-result.md").exists()
