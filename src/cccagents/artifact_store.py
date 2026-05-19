from pathlib import Path
from uuid import uuid4

from cccagents.artifacts import artifact_path
from cccagents.phase2_models import Artifact, ArtifactStatus


def register_artifact(
    project_id: str,
    project_root: Path,
    phase: str,
    owner_role: str,
    artifact_type: str,
    name: str,
    status: ArtifactStatus,
    version: int,
    extension: str,
    created_at: str,
    source_artifact_id: str | None = None,
) -> Artifact:
    path = artifact_path(project_root, phase, name, status.value, version, extension)
    return Artifact(
        id=f"artifact_{uuid4().hex}",
        project_id=project_id,
        phase=phase,
        owner_role=owner_role,
        type=artifact_type,
        path=str(path),
        version=version,
        status=status,
        source_artifact_id=source_artifact_id,
        created_at=created_at,
    )
