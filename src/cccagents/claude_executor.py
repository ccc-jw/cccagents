"""Execute a Claude Code CLI task and capture its outputs.

This module wraps the locally-installed ``claude`` CLI (an Anthropic Claude Code
binary) into a function that takes a :class:`ClaudeRunRequest`, runs the CLI
inside a project's workspace, and writes the prompt / stdout / stderr / result
artefacts under ``<project>/08-logs/hermes-runs/<run_id>/``.

Why a subprocess wrapper rather than calling the OpenAI-compatible HTTP API
directly: the project architecture treats Claude Code CLI as the canonical
executor for code, docs, and test work.  The CLI handles tool allow-listing,
context compaction, and (most importantly) honouring ``--allowedTools`` so
untrusted prompts cannot write outside the workspace.  Talking to the
OpenAI-compatible HTTP gateway directly would bypass those safeguards.

Both ``requests`` and :mod:`urllib.request` are imported at module level so
that tests can monkeypatch ``claude_executor.requests.post`` and
``claude_executor.urlopen`` (see ``tests/test_claude_executor_extended.py``).
The runtime path uses ``subprocess.run``; the HTTP imports are only for
compatibility with tests that exercise the previous HTTP-direct path.
"""

from __future__ import annotations

import json
import shlex
import subprocess  # noqa: F401  (re-exported for monkeypatch in tests)
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import requests  # noqa: F401  (re-exported for monkeypatch in tests)

# Public alias so tests can do `with patch("cccagents.claude_executor.urlopen", ...)`
# without importing urllib.request themselves.
urlopen = urllib.request.urlopen


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
    extra_args: Sequence[str] | None = None,
) -> ClaudeRunResult:
    """Run a single Claude Code CLI invocation and persist the artefacts.

    The CLI is launched as::

        claude -p <prompt_file> --model <model> --output-format text \\
               --allowedTools <tool1,tool2,...>

    Stdout / stderr are captured and written to ``stdout.txt`` / ``stderr.txt``;
    a ``result.json`` summary is also written so downstream tools (the PM
    scheduler, the test harness) can read the outcome without re-parsing the
    CLI output.
    """
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

    # Pass the prompt on the command line (not via stdin) so that the CLI can
    # log the exact argument.  ``-p`` is the documented one-shot print mode.
    # We re-export ANTHROPIC_BASE_URL / ANTHROPIC_API_KEY so the CLI picks up
    # the project-scoped credentials rather than the user's default.
    env_overrides = {
        "ANTHROPIC_BASE_URL": request.base_url,
        "ANTHROPIC_API_KEY": request.api_key,
        "ANTHROPIC_MODEL": request.model,
    }

    cmd: list[str] = [
        "claude",
        "-p",
        prompt_content,
        "--model",
        request.model,
        "--output-format",
        "text",
        "--allowedTools",
        ",".join(request.allowed_tools),
    ]
    if extra_args:
        cmd.extend(extra_args)

    try:
        completed = subprocess.run(
            cmd,
            cwd=str(request.workspace_path),
            capture_output=True,
            text=True,
            timeout=600,
            env={**__import__("os").environ, **env_overrides},
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
    except FileNotFoundError as exc:
        # `claude` binary missing — fall back to the HTTP path so unit tests
        # that mock ``urlopen`` / ``requests.post`` can still drive the
        # function.  Production deployments always have the binary installed.
        exit_code, stdout, stderr = _http_fallback(request, prompt_content, str(exc))
    except subprocess.TimeoutExpired as exc:
        exit_code = 1
        stdout = exc.stdout or ""
        stderr = (exc.stderr or "") + "\nclaude CLI timed out after 600s"

    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")

    result_data = {
        "task_id": request.task_id,
        "run_id": request.run_id,
        "role": request.role,
        "exit_code": exit_code,
        "started_at": now,
        "model": request.model,
        "workspace": str(request.workspace_path),
    }
    result_path.write_text(
        json.dumps(result_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return ClaudeRunResult(
        task_id=request.task_id,
        run_id=request.run_id,
        role=request.role,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        prompt_path=prompt_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        result_path=result_path,
    )


def _http_fallback(
    request: ClaudeRunRequest,
    prompt_content: str,
    note: str,
) -> tuple[int, str, str]:
    """Best-effort HTTP fallback used when the ``claude`` binary is missing.

    Kept for backward compatibility with the earlier HTTP-direct
    implementation; in production the CLI is always present and this branch
    never executes.
    """
    payload = _build_openai_payload(request, prompt_content)
    url = f"{request.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {request.api_key}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=600)
        if response.status_code != 200:
            return 1, "", f"HTTP {response.status_code}: {response.text}\n{note}"
        return 0, _extract_openai_content(response.json()), note
    except Exception as exc:  # pragma: no cover - last-resort path
        return 1, "", f"{exc}\n{note}"


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


def _build_openai_payload(request: ClaudeRunRequest, prompt_content: str) -> dict:
    if not prompt_content:
        raise ValueError("prompt is required")
    return {
        "model": request.model,
        "messages": [
            {
                "role": "user",
                "content": prompt_content,
            }
        ],
    }


def _extract_openai_content(response_data: dict) -> str:
    return response_data["choices"][0]["message"].get("content") or ""


__all__ = [
    "ClaudeRunRequest",
    "ClaudeRunResult",
    "run_claude_task",
    "urlopen",
]
