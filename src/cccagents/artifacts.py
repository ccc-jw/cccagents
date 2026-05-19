from pathlib import Path


PHASE_DIRS = {
    "requirements": "01-requirements",
    "tech-design": "02-tech-design",
    "test-cases": "03-test-cases",
    "development": "04-development",
    "quality-validation": "05-quality-validation",
    "security": "06-security",
    "acceptance": "07-acceptance",
    "logs": "08-logs",
}


def artifact_path(project_root: Path, phase: str, name: str, status: str, version: int, extension: str) -> Path:
    if phase not in PHASE_DIRS:
        raise ValueError(f"Unknown phase: {phase}")
    if status not in {"draft", "final", "review"}:
        raise ValueError(f"Unknown artifact status: {status}")
    if version < 1:
        raise ValueError("version must be greater than zero")

    return project_root / PHASE_DIRS[phase] / f"{name}.v{version}.{status}.{extension}"
