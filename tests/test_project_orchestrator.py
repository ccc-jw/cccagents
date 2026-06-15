from pathlib import Path

from cccagents.orchestrator import FakeExecutor, OrchestrationRequest
from cccagents.project_orchestrator import orchestrate_project, reconcile_and_orchestrate
from cccagents.project_state import ProjectState, load_project_state, save_project_state


def test_orchestrate_project_completes_s0(tmp_path):
    project_dir = tmp_path / "demo-orch"
    request = OrchestrationRequest(
        project_id="demo-orch",
        text="修复 README 里的 typo",
        project_root=tmp_path,
        now="2026-06-15T10:00:00Z",
    )

    result = orchestrate_project(project_dir, request, FakeExecutor(), now="2026-06-15T10:00:00Z")

    assert result["status"] == "done"
    assert result["complexity"] == "S0"

    state = load_project_state(project_dir)
    assert state.status == "done"


def test_orchestrate_s3_requires_approval(tmp_path):
    project_dir = tmp_path / "demo-s3-approval"
    request = OrchestrationRequest(
        project_id="demo-s3-approval",
        text="修改认证权限并部署到生产，涉及 FEISHU_APP_SECRET 配置",
        project_root=tmp_path,
        now="2026-06-15T10:00:00Z",
    )

    result = orchestrate_project(project_dir, request, FakeExecutor(), now="2026-06-15T10:00:00Z")

    assert result["status"] == "pending_approval"
    assert result["complexity"] == "S3"

    state = load_project_state(project_dir)
    assert state.status == "pending_approval"
    assert state.current_phase == "FEISHU_USER_APPROVAL"


def test_reconcile_interrupted_project_auto_retries(tmp_path):
    project_dir = tmp_path / "demo-retry"
    project_dir.mkdir(parents=True, exist_ok=True)

    interrupted_state = ProjectState(
        project_id="demo-retry",
        source="feishu",
        status="interrupted",
        complexity="S1",
        current_phase="DEV_IMPLEMENTATION",
        required_roles=["PM", "DEV", "TEST"],
        risk_flags=["code_change"],
        approval_policy="auto_if_l0_l1_and_all_reviews_pass",
        retry_count_by_phase={},
        created_at="2026-06-15T09:00:00Z",
        updated_at="2026-06-15T09:30:00Z",
        last_pm_notification_at="2026-06-15T09:30:00Z",
    )
    save_project_state(project_dir, interrupted_state)

    request = OrchestrationRequest(
        project_id="demo-retry",
        text="修复登录按钮 loading 的局部 bug",
        project_root=tmp_path,
        now="2026-06-15T10:00:00Z",
    )

    result = reconcile_and_orchestrate(project_dir, request, FakeExecutor(), now="2026-06-15T10:00:00Z")

    assert result["status"] == "done"

    state = load_project_state(project_dir)
    assert state.status == "done"

    recovery_log = project_dir / "08-logs" / "restart-recovery.jsonl"
    assert recovery_log.exists()
    content = recovery_log.read_text()
    assert "reconcile_interrupted" in content


def test_reconcile_interrupted_s3_requires_manual_decision(tmp_path):
    project_dir = tmp_path / "demo-s3-interrupted"
    project_dir.mkdir(parents=True, exist_ok=True)

    interrupted_state = ProjectState(
        project_id="demo-s3-interrupted",
        source="feishu",
        status="interrupted",
        complexity="S3",
        current_phase="SECURITY_REVIEW",
        required_roles=["PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC"],
        risk_flags=["security_sensitive"],
        approval_policy="manual_approval_required",
        retry_count_by_phase={},
        created_at="2026-06-15T09:00:00Z",
        updated_at="2026-06-15T09:30:00Z",
        last_pm_notification_at="2026-06-15T09:30:00Z",
    )
    save_project_state(project_dir, interrupted_state)

    request = OrchestrationRequest(
        project_id="demo-s3-interrupted",
        text="修改认证权限并部署到生产",
        project_root=tmp_path,
        now="2026-06-15T10:00:00Z",
    )

    result = reconcile_and_orchestrate(project_dir, request, FakeExecutor(), now="2026-06-15T10:00:00Z")

    assert result["status"] == "interrupted"
    assert "manual decision" in result["message"]


def test_paused_project_is_not_orchestrated(tmp_path):
    project_dir = tmp_path / "demo-paused"
    project_dir.mkdir(parents=True, exist_ok=True)

    paused_state = ProjectState(
        project_id="demo-paused",
        source="feishu",
        status="paused",
        complexity="S2",
        current_phase="DEVELOPMENT",
        required_roles=["PM", "PDM", "ARCH", "DEV", "TEST"],
        risk_flags=["feature_change"],
        approval_policy="auto_if_l0_l1_and_all_reviews_pass",
        retry_count_by_phase={},
        created_at="2026-06-15T09:00:00Z",
        updated_at="2026-06-15T09:30:00Z",
        last_pm_notification_at="2026-06-15T09:30:00Z",
    )
    save_project_state(project_dir, paused_state)

    request = OrchestrationRequest(
        project_id="demo-paused",
        text="新增一个导出订单 CSV 的功能",
        project_root=tmp_path,
        now="2026-06-15T10:00:00Z",
    )

    result = orchestrate_project(project_dir, request, FakeExecutor(), now="2026-06-15T10:00:00Z")

    assert result["status"] == "paused"
    assert "paused" in result["message"]
