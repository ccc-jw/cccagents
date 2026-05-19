from cccagents.phase2_models import (
    AGENT_ROLES,
    Artifact,
    ArtifactStatus,
    Task,
    TaskStatus,
)


def test_agent_roles_include_all_phase2_roles():
    assert AGENT_ROLES == ("PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC")


def test_task_defaults_to_pending_without_started_time():
    task = Task(
        id="task_001",
        project_id="proj_001",
        phase="REQUIREMENT_DRAFTING",
        flow="main",
        assignee_role="PDM",
        title="Draft PRD",
        description="Create PRD draft",
        created_at="2026-05-19T10:00:00Z",
    )

    assert task.status == TaskStatus.PENDING
    assert task.started_at is None
    assert task.next_handler_role == "PDM"


def test_artifact_records_path_version_and_status():
    artifact = Artifact(
        id="artifact_001",
        project_id="proj_001",
        phase="requirements",
        owner_role="PDM",
        type="prd",
        path="projects/proj_001/01-requirements/prd.v1.draft.md",
        version=1,
        status=ArtifactStatus.DRAFT,
        created_at="2026-05-19T10:00:00Z",
    )

    assert artifact.version == 1
    assert artifact.status == ArtifactStatus.DRAFT
