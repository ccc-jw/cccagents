from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class ProjectState:
    project_id: str
    source: str
    status: str
    complexity: str
    current_phase: str
    required_roles: list[str]
    risk_flags: list[str]
    approval_policy: str
    retry_count_by_phase: dict[str, int]
    created_at: str
    updated_at: str
    last_pm_notification_at: str | None = None


def project_state_path(project_dir: Path) -> Path:
    return project_dir / "project-state.json"


def save_project_state(project_dir: Path, state: ProjectState) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    project_state_path(project_dir).write_text(
        json.dumps(asdict(state), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_project_state(project_dir: Path) -> ProjectState:
    path = project_state_path(project_dir)
    if not path.exists():
        raise KeyError("project-state.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProjectState(**data)
