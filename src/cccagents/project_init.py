from pathlib import Path

from cccagents.paths import ProjectPaths


PROJECT_DIRS = (
    "00-meta",
    "01-requirements",
    "02-tech-design",
    "03-test-cases",
    "04-development",
    "05-quality-validation",
    "06-security",
    "07-acceptance",
    "08-logs/agent-runs",
)


def initialize_project_structure(paths: ProjectPaths) -> list[Path]:
    created: list[Path] = []
    directories = [paths.workspace_root, *(paths.project_root / item for item in PROJECT_DIRS)]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        created.append(directory)

    return created
