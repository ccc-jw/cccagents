from dataclasses import dataclass
from pathlib import Path

from cccagents.phase2_models import Task


@dataclass(frozen=True)
class PromptContext:
    workspace_path: Path
    project_dir: Path
    input_artifact_paths: list[Path]
    expected_output_paths: list[Path]
    allowed_tools: list[str]
    forbidden_operations: list[str]


def build_role_prompt(task: Task, context: PromptContext) -> str:
    role_lower = task.assignee_role.lower()
    return "\n".join(
        [
            f"You are {task.assignee_role}.",
            f"Read hermes/roles/{role_lower}.md before acting.",
            "",
            "Task metadata:",
            f"- project_id: {task.project_id}",
            f"- task_id: {task.id}",
            f"- phase: {task.phase}",
            f"- title: {task.title}",
            f"- description: {task.description}",
            "",
            "Workspace boundary:",
            f"- Work only inside: {context.workspace_path}",
            f"- Project evidence directory: {context.project_dir}",
            "",
            "Input artifacts:",
            *_format_paths(context.input_artifact_paths),
            "",
            "Expected output artifacts:",
            *_format_paths(context.expected_output_paths),
            "",
            "Allowed tools:",
            *_format_items(context.allowed_tools),
            "",
            "Forbidden operations:",
            *_format_items(context.forbidden_operations),
            "",
            "Completion format:",
            "Return a completion summary with status, files changed, tests run, risks, and output artifact paths.",
        ]
    )


def _format_paths(paths: list[Path]) -> list[str]:
    if not paths:
        return ["- none"]
    return [f"- {path}" for path in paths]


def _format_items(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]
