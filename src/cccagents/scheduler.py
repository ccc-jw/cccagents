from dataclasses import dataclass
from pathlib import Path

from cccagents.paths import ProjectPaths, assert_within_project


@dataclass(frozen=True)
class DispatchRequest:
    project_id: str
    cwd: Path
    repo_root: Path
    permission_level: str
    mutates_project: bool


@dataclass(frozen=True)
class ProjectLockState:
    active_write_project_ids: set[str]
    global_running_count: int
    global_limit: int


@dataclass(frozen=True)
class DispatchDecision:
    allowed: bool
    reason: str


def decide_dispatch(request: DispatchRequest, locks: ProjectLockState) -> DispatchDecision:
    if locks.global_running_count >= locks.global_limit:
        return DispatchDecision(False, "global_limit_reached")

    project_paths = ProjectPaths(root=request.repo_root, project_id=request.project_id)
    try:
        assert_within_project(request.cwd, project_paths)
    except ValueError:
        return DispatchDecision(False, "cwd_outside_project")

    if request.mutates_project and request.project_id in locks.active_write_project_ids:
        return DispatchDecision(False, "same_project_write_lock")

    return DispatchDecision(True, "dispatch_allowed")
