import json
from pathlib import Path

from cccagents.claude_executor import ClaudeRunRequest, run_claude_task
from cccagents.complexity_classifier import classify_project_request
from cccagents.orchestrator import FakeExecutor, OrchestrationRequest, orchestrate_request
from cccagents.project_state import load_project_state
from cccagents.role_plan import RoleTask


class RealExecutor:
    """Execute tasks using real Claude Code CLI."""

    def __init__(self, model: str, base_url: str, api_key: str):
        self.model = model
        self.base_url = base_url
        self.api_key = api_key

    def run(self, project_dir: Path, task: RoleTask, task_id: str, run_id: str, now: str) -> dict:
        workspace = project_dir.parent.parent / "workspaces" / project_dir.name / "repo"
        workspace.mkdir(parents=True, exist_ok=True)

        prompt = self._build_prompt(task, project_dir)

        request = ClaudeRunRequest(
            task_id=task_id,
            role=task.role,
            prompt=prompt,
            workspace_path=workspace,
            project_dir=project_dir,
            allowed_tools=["Read", "Write"],
            model=self.model,
            base_url=self.base_url,
            api_key=self.api_key,
            run_id=run_id,
        )

        result = run_claude_task(request, now=now)

        return {
            "role": task.role,
            "template": task.template,
            "artifact_paths": [str(p) for p in task.expected_artifacts],
            "passed": result.exit_code == 0,
            "issues": [] if result.exit_code == 0 else [f"exit_code_{result.exit_code}"],
            "exit_code": result.exit_code,
            "run_id": run_id,
        }

    def _build_prompt(self, task: RoleTask, project_dir: Path) -> str:
        return "\n".join(
            [
                f"You are {task.role}.",
                f"Task template: {task.template}",
                "",
                "Instructions:",
                f"- Complete the {task.template} task",
                f"- Write output artifacts to: {', '.join(str(p) for p in task.expected_artifacts)}",
                f"- Project directory: {project_dir}",
                "",
                "Return a completion summary when done.",
            ]
        )


def orchestrate_with_real_executor(
    request: OrchestrationRequest,
    executor: RealExecutor,
    now: str,
) -> dict:
    """Orchestrate a project using real Claude Code CLI execution."""
    decision = classify_project_request(request.text)
    project_dir = request.project_root / request.project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    from cccagents.role_plan import build_role_plan

    plan = build_role_plan(decision)

    (project_dir / "role-plan.json").write_text(
        json.dumps(
            {
                "complexity": decision.complexity,
                "required_roles": decision.required_roles,
                "risk_flags": decision.risk_flags,
                "phases": [
                    {
                        "name": phase.name,
                        "parallel": phase.parallel,
                        "isolation": phase.isolation,
                        "tasks": [
                            {"role": t.role, "template": t.template}
                            for t in phase.tasks
                        ],
                    }
                    for phase in plan.phases
                ],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    executed_roles = []
    run_counter = 0
    for phase in plan.phases:
        for task in phase.tasks:
            run_counter += 1
            run_id = f"run-{run_counter:03d}"
            task_id = f"{request.project_id}-{phase.name}-{task.role}".lower()

            result = executor.run(project_dir, task, task_id, run_id, now)
            executed_roles.append(result["role"])

            if not result["passed"]:
                return {
                    "project_id": request.project_id,
                    "status": "blocked",
                    "complexity": decision.complexity,
                    "executed_roles": executed_roles,
                    "issues": result["issues"],
                }

    return {
        "project_id": request.project_id,
        "status": "done",
        "complexity": decision.complexity,
        "executed_roles": executed_roles,
        "issues": [],
    }
