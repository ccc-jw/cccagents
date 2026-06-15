from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class ProjectState:
    project_id: str
    status: str
    complexity: str
    executed_roles: list[str]
    artifacts: list[str]
    updated_at: str


def save_project_state(project_dir: Path, state: ProjectState) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / "project-state.json"
    path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_project_state(project_dir: Path) -> ProjectState:
    path = project_dir / "project-state.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProjectState(
        project_id=data["project_id"],
        status=data["status"],
        complexity=data["complexity"],
        executed_roles=list(data["executed_roles"]),
        artifacts=list(data["artifacts"]),
        updated_at=data["updated_at"],
    )
