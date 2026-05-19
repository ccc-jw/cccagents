from pathlib import Path

from cccagents.scheduler import DispatchRequest, ProjectLockState, decide_dispatch


def test_allows_project_write_when_no_same_project_lock(tmp_path):
    request = DispatchRequest(
        project_id="project_a",
        cwd=tmp_path / "workspaces" / "project_a" / "repo",
        repo_root=tmp_path,
        permission_level="L1",
        mutates_project=True,
    )
    locks = ProjectLockState(active_write_project_ids=set(), global_running_count=0, global_limit=2)

    decision = decide_dispatch(request, locks)

    assert decision.allowed is True
    assert decision.reason == "dispatch_allowed"


def test_denies_same_project_concurrent_write(tmp_path):
    request = DispatchRequest(
        project_id="project_a",
        cwd=tmp_path / "workspaces" / "project_a" / "repo",
        repo_root=tmp_path,
        permission_level="L1",
        mutates_project=True,
    )
    locks = ProjectLockState(active_write_project_ids={"project_a"}, global_running_count=0, global_limit=2)

    decision = decide_dispatch(request, locks)

    assert decision.allowed is False
    assert decision.reason == "same_project_write_lock"


def test_allows_different_project_write_under_global_limit(tmp_path):
    request = DispatchRequest(
        project_id="project_b",
        cwd=tmp_path / "workspaces" / "project_b" / "repo",
        repo_root=tmp_path,
        permission_level="L1",
        mutates_project=True,
    )
    locks = ProjectLockState(active_write_project_ids={"project_a"}, global_running_count=1, global_limit=2)

    decision = decide_dispatch(request, locks)

    assert decision.allowed is True
    assert decision.reason == "dispatch_allowed"


def test_denies_dispatch_outside_project_scope(tmp_path):
    request = DispatchRequest(
        project_id="project_a",
        cwd=Path("/tmp/outside"),
        repo_root=tmp_path,
        permission_level="L1",
        mutates_project=True,
    )
    locks = ProjectLockState(active_write_project_ids=set(), global_running_count=0, global_limit=2)

    decision = decide_dispatch(request, locks)

    assert decision.allowed is False
    assert decision.reason == "cwd_outside_project"


def test_denies_when_global_limit_reached(tmp_path):
    request = DispatchRequest(
        project_id="project_a",
        cwd=tmp_path / "workspaces" / "project_a" / "repo",
        repo_root=tmp_path,
        permission_level="L0",
        mutates_project=False,
    )
    locks = ProjectLockState(active_write_project_ids=set(), global_running_count=2, global_limit=2)

    decision = decide_dispatch(request, locks)

    assert decision.allowed is False
    assert decision.reason == "global_limit_reached"
