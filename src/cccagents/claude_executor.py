from dataclasses import asdict, dataclass
import json
import subprocess
from pathlib import Path

from cccagents.paths import ProjectPaths


@dataclass(frozen=True)
class ClaudeRunRequest:
    task_id: str
    role: str
    prompt: str
    workspace_path: Path
    project_dir: Path
    allowed_tools: list[str]
    model: str
    base_url: str
    api_key: str
    run_id: str


@dataclass(frozen=True)
class ClaudeRunResult:
    task_id: str
    run_id: str
    role: str
    exit_code: int
    stdout: str
    stderr: str
    prompt_path: Path
    stdout_path: Path
    stderr_path: Path
    result_path: Path


def run_claude_task(
    request: ClaudeRunRequest,
    now: str,
    extra_args: list[str] | None = None,
) -> ClaudeRunResult:
    if extra_args and "--dangerously-skip-permissions" in extra_args:
        raise ValueError("--dangerously-skip-permissions is not allowed")

    run_dir = request.project_dir / "08-logs" / "hermes-runs" / request.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = run_dir / "prompt.md"
    stdout_path = run_dir / "stdout.txt"
    stderr_path = run_dir / "stderr.txt"
    result_path = run_dir / "result.json"

    prompt_content = _build_prompt_content(request, now)
    prompt_path.write_text(prompt_content, encoding="utf-8")

    command = _build_command(request, prompt_content)

    env = {
        "ANTHROPIC_BASE_URL": request.base_url,
        "ANTHROPIC_API_KEY": request.api_key,
        "ANTHROPIC_MODEL": request.model,
    }

    completed = subprocess.run(
        command,
        cwd=str(request.workspace_path),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )

    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")

    result_data = {
        "task_id": request.task_id,
        "run_id": request.run_id,
        "role": request.role,
        "exit_code": completed.returncode,
        "started_at": now,
        "model": request.model,
        "workspace": str(request.workspace_path),
    }
    result_path.write_text(json.dumps(result_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return ClaudeRunResult(
        task_id=request.task_id,
        run_id=request.run_id,
        role=request.role,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        prompt_path=prompt_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        result_path=result_path,
    )


def _build_prompt_content(request: ClaudeRunRequest, now: str) -> str:
    return "\n".join(
        [
            f"# Task for {request.role}",
            "",
            f"Task ID: {request.task_id}",
            f"Run ID: {request.run_id}",
            f"Timestamp: {now}",
            "",
            "## Instructions",
            "",
            request.prompt,
            "",
            "## Allowed Tools",
            *[f"- {tool}" for tool in request.allowed_tools],
            "",
            "## Workspace",
            f"Work inside: {request.workspace_path}",
            "",
        ]
    )


def _build_command(request: ClaudeRunRequest, prompt_content: str) -> list[str]:
    if not prompt_content:
        raise ValueError("prompt is required")
    return [
        "claude",
        "-p",
        prompt_content,
        "--model",
        request.model,
        "--output-format",
        "text",
    ]
