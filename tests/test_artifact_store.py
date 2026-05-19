from pathlib import Path

from cccagents.artifact_store import register_artifact
from cccagents.phase2_models import ArtifactStatus


def test_register_artifact_returns_versioned_path_and_metadata():
    artifact = register_artifact(
        project_id="proj_001",
        project_root=Path("projects/proj_001"),
        phase="requirements",
        owner_role="PDM",
        artifact_type="prd",
        name="prd",
        status=ArtifactStatus.DRAFT,
        version=1,
        extension="md",
        created_at="2026-05-19T10:00:00Z",
    )

    assert artifact.path == "projects/proj_001/01-requirements/prd.v1.draft.md"
    assert artifact.owner_role == "PDM"
    assert artifact.version == 1
