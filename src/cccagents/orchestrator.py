from dataclasses import dataclass
from pathlib import Path

from cccagents.complexity_classifier import classify_project_request
from cccagents.project_state import ProjectState, save_project_state


@dataclass(frozen=True)
class OrchestrationRequest:
    project_id: str
    text: str
    project_root: Path
    now: str


@dataclass(frozen=True)
class OrchestrationResult:
    project_id: str
    status: str
    complexity: str
    executed_roles: list[str]
    project_dir: Path


class FakeExecutor:
    def run_dev(self, project_dir: Path, request_text: str, now: str) -> str:
        path = project_dir / "05-development" / "dev-summary.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# DEV Summary\n\nRequest: {request_text}\n\nImplemented at: {now}\n",
            encoding="utf-8",
        )
        return "05-development/dev-summary.md"

    def run_dev_self_check(self, project_dir: Path, request_text: str, now: str) -> str:
        path = project_dir / "05-development" / "dev-summary.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n## DEV Self Check\n\nChecked at: {now}\n")
        return "05-development/dev-summary.md"

    def run_test(self, project_dir: Path, request_text: str, now: str) -> str:
        path = project_dir / "04-test-cases" / "test-result.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# TEST Result\n\nRequest: {request_text}\n\nValidated at: {now}\n",
            encoding="utf-8",
        )
        return "04-test-cases/test-result.md"

    def run_pm_acceptance(self, project_dir: Path, request_text: str, now: str) -> str:
        path = project_dir / "07-acceptance" / "acceptance-report.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# PM Acceptance\n\nRequest: {request_text}\n\nAccepted at: {now}\n",
            encoding="utf-8",
        )
        return "07-acceptance/acceptance-report.md"


def orchestrate_request(request: OrchestrationRequest, executor: FakeExecutor) -> OrchestrationResult:
    project_dir = request.project_root / request.project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    decision = classify_project_request(request.text)
    executed_roles: list[str] = []
    artifacts: list[str] = []

    if decision.complexity == "S0":
        artifacts.append(executor.run_dev(project_dir, request.text, request.now))
        executed_roles.append("DEV")
        executor.run_dev_self_check(project_dir, request.text, request.now)
        executed_roles.append("DEV")
        artifacts.append(executor.run_pm_acceptance(project_dir, request.text, request.now))
        executed_roles.append("PM")
        status = "done"
    elif decision.complexity == "S1":
        artifacts.append(executor.run_dev(project_dir, request.text, request.now))
        executed_roles.append("DEV")
        executor.run_dev_self_check(project_dir, request.text, request.now)
        executed_roles.append("DEV")
        artifacts.append(executor.run_test(project_dir, request.text, request.now))
        executed_roles.append("TEST")
        artifacts.append(executor.run_pm_acceptance(project_dir, request.text, request.now))
        executed_roles.append("PM")
        status = "done"
    else:
        status = "blocked"

    state = ProjectState(
        project_id=request.project_id,
        status=status,
        complexity=decision.complexity,
        executed_roles=executed_roles,
        artifacts=artifacts,
        updated_at=request.now,
    )
    save_project_state(project_dir, state)

    return OrchestrationResult(
        project_id=request.project_id,
        status=status,
        complexity=decision.complexity,
        executed_roles=executed_roles,
        project_dir=project_dir,
    )
