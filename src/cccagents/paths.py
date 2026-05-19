from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    project_id: str

    @property
    def workspace_root(self) -> Path:
        return self.root / "workspaces" / self.project_id / "repo"

    @property
    def project_root(self) -> Path:
        return self.root / "projects" / self.project_id

    @property
    def command_log(self) -> Path:
        return self.project_root / "08-logs" / "command-log.jsonl"

    def run_log_dir(self, run_id: str) -> Path:
        return self.project_root / "08-logs" / "hermes-runs" / run_id


def assert_within_project(path: Path, project_paths: ProjectPaths) -> Path:
    resolved = path.resolve()
    allowed_roots = [
        project_paths.workspace_root.resolve(),
        project_paths.project_root.resolve(),
    ]

    if any(resolved == root or root in resolved.parents for root in allowed_roots):
        return resolved

    raise ValueError(f"Path outside project scope: {resolved}")
