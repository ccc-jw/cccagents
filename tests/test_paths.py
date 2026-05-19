from pathlib import Path

import pytest

from cccagents.paths import ProjectPaths, assert_within_project


def test_project_paths_are_separated_under_root(tmp_path):
    paths = ProjectPaths(root=tmp_path, project_id="proj_001")

    assert paths.workspace_root == tmp_path / "workspaces" / "proj_001" / "repo"
    assert paths.project_root == tmp_path / "projects" / "proj_001"
    assert paths.command_log == tmp_path / "projects" / "proj_001" / "08-logs" / "command-log.jsonl"


def test_assert_within_project_accepts_workspace_path(tmp_path):
    paths = ProjectPaths(root=tmp_path, project_id="proj_001")
    target = paths.workspace_root / "package.json"

    assert assert_within_project(target, paths) == target.resolve()


def test_assert_within_project_accepts_project_artifact_path(tmp_path):
    paths = ProjectPaths(root=tmp_path, project_id="proj_001")
    target = paths.project_root / "00-meta" / "phase-log.md"

    assert assert_within_project(target, paths) == target.resolve()


def test_assert_within_project_rejects_other_project(tmp_path):
    paths = ProjectPaths(root=tmp_path, project_id="proj_001")
    target = tmp_path / "workspaces" / "proj_002" / "repo" / "README.md"

    with pytest.raises(ValueError, match="outside project scope"):
        assert_within_project(target, paths)
