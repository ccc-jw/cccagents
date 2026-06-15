from pathlib import Path

from cccagents.phase2_models import Task
from cccagents.prompt_builder import PromptContext, build_role_prompt


def test_dev_prompt_contains_role_project_paths_and_forbidden_rules():
    task = Task(
        id="task-dev-1",
        project_id="demo",
        phase="DEV_IMPLEMENTATION",
        flow="main",
        assignee_role="DEV",
        title="Implement change",
        description="Add README line",
        created_at="2026-06-13T10:00:00Z",
    )
    context = PromptContext(
        workspace_path=Path("/home/ubuntu/cccagents/workspaces/demo/repo"),
        project_dir=Path("/home/ubuntu/cccagents/projects/demo"),
        input_artifact_paths=[Path("02-requirements/prd.md")],
        expected_output_paths=[Path("05-development/dev-summary.md")],
        allowed_tools=["Read", "Write"],
        forbidden_operations=["Do not contact Feishu user", "Do not perform L2/L3 operations"],
    )

    prompt = build_role_prompt(task, context)

    assert "You are DEV" in prompt
    assert "Read hermes/roles/dev.md" in prompt
    assert "project_id: demo" in prompt
    assert "task_id: task-dev-1" in prompt
    assert "/home/ubuntu/cccagents/workspaces/demo/repo" in prompt
    assert "05-development/dev-summary.md" in prompt
    assert "Do not contact Feishu user" in prompt
    assert "Return a completion summary" in prompt


def test_parallel_isolation_prompt_excludes_other_branch_artifacts():
    task = Task(
        id="task-test-1",
        project_id="demo",
        phase="TEST_CASE_DRAFTING",
        flow="testcase",
        assignee_role="TEST",
        title="Draft test cases",
        description="Write test cases from PRD",
        created_at="2026-06-13T10:00:00Z",
    )
    context = PromptContext(
        workspace_path=Path("/home/ubuntu/cccagents/workspaces/demo/repo"),
        project_dir=Path("/home/ubuntu/cccagents/projects/demo"),
        input_artifact_paths=[Path("02-requirements/prd.md")],
        expected_output_paths=[Path("04-test-cases/test-cases.md"), Path("04-test-cases/test-cases.xlsx")],
        allowed_tools=["Read", "Write"],
        forbidden_operations=["Do not read 03-architecture during testcase drafting"],
    )

    prompt = build_role_prompt(task, context)

    assert "02-requirements/prd.md" in prompt
    assert "04-test-cases/test-cases.xlsx" in prompt
    assert "Do not read 03-architecture during testcase drafting" in prompt
    assert "03-architecture/tech-design.md" not in prompt
