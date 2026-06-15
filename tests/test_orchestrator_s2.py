import json

from cccagents.orchestrator import FakeExecutor, OrchestrationRequest, orchestrate_request
from cccagents.project_state import load_project_state


def test_orchestrator_completes_s2_with_parallel_design_and_testcase(tmp_path):
    result = orchestrate_request(
        OrchestrationRequest(
            project_id="demo-s2",
            text="新增一个导出订单 CSV 的功能，包含接口和测试用例",
            project_root=tmp_path,
            now="2026-06-13T10:00:00Z",
        ),
        executor=FakeExecutor(),
    )

    project_dir = tmp_path / "demo-s2"
    state = load_project_state(project_dir)
    role_plan = json.loads((project_dir / "role-plan.json").read_text(encoding="utf-8"))

    assert result.status == "done"
    assert state.complexity == "S2"
    assert result.executed_roles == ["PDM", "PM", "ARCH", "TEST", "PM", "DEV", "DEV", "TEST", "PDM"]
    assert (project_dir / "02-requirements" / "prd.md").exists()
    assert (project_dir / "03-architecture" / "tech-design.md").exists()
    assert (project_dir / "04-test-cases" / "test-cases.md").exists()
    assert (project_dir / "04-test-cases" / "test-cases.xlsx").exists()
    assert role_plan["phases"][2]["parallel"] is True
    assert role_plan["phases"][2]["isolation"] is True


def test_s2_parallel_isolation_evidence_is_written(tmp_path):
    orchestrate_request(
        OrchestrationRequest(
            project_id="demo-s2",
            text="新增一个导出订单 CSV 的功能，包含接口和测试用例",
            project_root=tmp_path,
            now="2026-06-13T10:00:00Z",
        ),
        executor=FakeExecutor(),
    )

    isolation_log = tmp_path / "demo-s2" / "08-logs" / "parallel-isolation.jsonl"

    assert isolation_log.exists()
    content = isolation_log.read_text(encoding="utf-8")
    assert "ARCH" in content
    assert "TEST" in content
    assert "no_cross_branch_artifacts" in content
