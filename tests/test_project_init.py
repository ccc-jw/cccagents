from cccagents.paths import ProjectPaths
from cccagents.project_init import initialize_project_structure


def test_initialize_project_structure_creates_workspace_and_artifact_dirs(tmp_path):
    paths = ProjectPaths(root=tmp_path, project_id="proj_001")

    created = initialize_project_structure(paths)

    assert paths.workspace_root.is_dir()
    assert (paths.project_root / "00-meta").is_dir()
    assert (paths.project_root / "01-requirements").is_dir()
    assert (paths.project_root / "02-tech-design").is_dir()
    assert (paths.project_root / "03-test-cases").is_dir()
    assert (paths.project_root / "08-logs" / "agent-runs").is_dir()
    assert paths.command_log.parent.is_dir()
    assert paths.workspace_root in created
