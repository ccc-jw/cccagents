# cccagents Phase 1A-1C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 verification foundation for cccagents: local documentation, Linux install checklist, OpenAI-compatible Claude Code CLI gate verification, project/workspace logging, and executable policy prototypes.

**Architecture:** Phase 1 is a verification-first implementation, not the full Hermes platform. The repository will contain focused docs, shell scripts, and Python utilities that can be copied to or run on the Ubuntu server to validate the strict gate before Phase 2. The plan deliberately avoids building Feishu, full Agent Runtime, or long-running async orchestration until Phase 1B passes.

**Tech Stack:** Markdown, Bash, Python 3 standard library, pytest, openpyxl for Excel generation.

---

## File Structure

Create these files:

```text
docs/phase1/
  linux-install-checklist.md
  openai-compat-gate.md
  executor-run-model.md
  command-policy.md
  security-and-redaction.md
  test-checklist-format.md
  feishu-security-notes.md

scripts/phase1/
  install_claude_code_ubuntu.sh
  collect_claude_code_capabilities.sh
  verify_project_workspace.sh

src/cccagents/__init__.py
src/cccagents/paths.py
src/cccagents/command_policy.py
src/cccagents/redaction.py
src/cccagents/command_log.py
src/cccagents/artifacts.py
src/cccagents/test_checklist.py

tests/test_paths.py
tests/test_command_policy.py
tests/test_redaction.py
tests/test_command_log.py
tests/test_artifacts.py
tests/test_test_checklist.py

requirements-dev.txt
```

Responsibilities:

```text
docs/phase1/*.md
- Human-readable Phase 1 operating documents for the Linux server.

scripts/phase1/*.sh
- Copyable Linux commands for installing and verifying Claude Code CLI.

src/cccagents/paths.py
- Project/workspace path resolution and cross-project path guard.

src/cccagents/command_policy.py
- Command classification and policy decision prototype for L0-L3.

src/cccagents/redaction.py
- Sensitive string detection and redaction.

src/cccagents/command_log.py
- JSONL command log record construction and append helpers.

src/cccagents/artifacts.py
- Artifact version path helpers for draft/final/review files.

src/cccagents/test_checklist.py
- Markdown-to-Excel test checklist conversion using one shared schema.
```

## Implementation Tasks

### Task 1: Add Python package skeleton and dev dependencies

**Files:**
- Create: `src/cccagents/__init__.py`
- Create: `requirements-dev.txt`

- [ ] **Step 1: Create package marker**

Create `src/cccagents/__init__.py`:

```python
"""cccagents Phase 1 verification utilities."""
```

- [ ] **Step 2: Add dev dependencies**

Create `requirements-dev.txt`:

```text
pytest==8.3.4
openpyxl==3.1.5
```

- [ ] **Step 3: Verify import path manually**

Run:

```bash
PYTHONPATH=src python -c "import cccagents; print(cccagents.__doc__)"
```

Expected output contains:

```text
cccagents Phase 1 verification utilities.
```

- [ ] **Step 4: Commit**

```bash
git add src/cccagents/__init__.py requirements-dev.txt
git commit -m "chore: add phase 1 python utility skeleton"
```

### Task 2: Implement multi-project path guards

**Files:**
- Create: `src/cccagents/paths.py`
- Test: `tests/test_paths.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_paths.py`:

```python
from pathlib import Path

import pytest

from cccagents.paths import ProjectPaths, assert_within_project


def test_project_paths_are_separated_under_root(tmp_path):
    paths = ProjectPaths(root=tmp_path, project_id="proj_001")

    assert paths.workspace_root == tmp_path / "workspaces" / "proj_001" / "repo"
    assert paths.project_root == tmp_path / "projects" / "proj_001"
    assert paths.command_log == tmp_path / "projects" / "proj_001" / "08-logs" / "command-log.jsonl"


def test_assert_within_project_accepts_workspace_path(tmp_path):
    paths = ProjectPaths(root=tmp_path, project_id="proj_001")
    target = paths.workspace_root / "package.json"

    assert assert_within_project(target, paths) == target.resolve()


def test_assert_within_project_accepts_project_artifact_path(tmp_path):
    paths = ProjectPaths(root=tmp_path, project_id="proj_001")
    target = paths.project_root / "00-meta" / "phase-log.md"

    assert assert_within_project(target, paths) == target.resolve()


def test_assert_within_project_rejects_other_project(tmp_path):
    paths = ProjectPaths(root=tmp_path, project_id="proj_001")
    target = tmp_path / "workspaces" / "proj_002" / "repo" / "README.md"

    with pytest.raises(ValueError, match="outside project scope"):
        assert_within_project(target, paths)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_paths.py -v
```

Expected: FAIL because `cccagents.paths` does not exist.

- [ ] **Step 3: Implement path guards**

Create `src/cccagents/paths.py`:

```python
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


def assert_within_project(path: Path, project_paths: ProjectPaths) -> Path:
    resolved = path.resolve()
    allowed_roots = [
        project_paths.workspace_root.resolve(),
        project_paths.project_root.resolve(),
    ]

    if any(resolved == root or root in resolved.parents for root in allowed_roots):
        return resolved

    raise ValueError(f"Path outside project scope: {resolved}")
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_paths.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/paths.py tests/test_paths.py
git commit -m "feat: add project workspace path guards"
```

### Task 3: Implement command policy engine prototype

**Files:**
- Create: `src/cccagents/command_policy.py`
- Test: `tests/test_command_policy.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_command_policy.py`:

```python
from cccagents.command_policy import classify_command, decide_command


def test_classifies_read_only_commands_as_l0():
    for command in ["ls", "git status", "git diff", "rg TODO", "grep -R foo ."]:
        assert classify_command(command) == "L0"


def test_classifies_local_write_and_tests_as_l1():
    for command in ["pytest", "npm test", "mkdir -p docs", "python scripts/generate.py"]:
        assert classify_command(command) == "L1"


def test_classifies_project_changes_as_l2():
    for command in ["npm install", "pip install requests", "alembic upgrade head", "npm run migrate"]:
        assert classify_command(command) == "L2"


def test_classifies_external_impact_as_l3():
    for command in ["git push", "gh pr create", "kubectl apply -f deploy.yaml", "terraform apply"]:
        assert classify_command(command) == "L3"


def test_dangerous_delete_and_force_require_approval():
    assert classify_command("rm -rf /tmp/demo") == "L3"
    assert classify_command("git push --force") == "L3"


def test_decision_allows_l0_and_l1_but_requires_approval_for_l2_l3():
    assert decide_command("L0") == "allow"
    assert decide_command("L1") == "allow"
    assert decide_command("L2") == "require_approval"
    assert decide_command("L3") == "require_approval"


def test_decision_denies_unbound_write():
    assert decide_command("L1", bound_project=False) == "deny"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_command_policy.py -v
```

Expected: FAIL because `cccagents.command_policy` does not exist.

- [ ] **Step 3: Implement command policy engine**

Create `src/cccagents/command_policy.py`:

```python
import shlex


L3_PREFIXES = (
    ("git", "push"),
    ("gh", "pr", "create"),
    ("kubectl",),
    ("terraform", "apply"),
    ("rm",),
)

L2_PREFIXES = (
    ("npm", "install"),
    ("pip", "install"),
    ("alembic", "upgrade"),
    ("npm", "run", "migrate"),
)

L1_PREFIXES = (
    ("pytest",),
    ("npm", "test"),
    ("mkdir",),
    ("python",),
)

L0_PREFIXES = (
    ("ls",),
    ("git", "status"),
    ("git", "diff"),
    ("rg",),
    ("grep",),
)


def _starts_with(parts: list[str], prefix: tuple[str, ...]) -> bool:
    return len(parts) >= len(prefix) and tuple(parts[: len(prefix)]) == prefix


def classify_command(command: str) -> str:
    parts = shlex.split(command)
    if not parts:
        return "L0"

    if "--force" in parts or "-rf" in parts or "-fr" in parts:
        return "L3"

    for prefix in L3_PREFIXES:
        if _starts_with(parts, prefix):
            return "L3"

    for prefix in L2_PREFIXES:
        if _starts_with(parts, prefix):
            return "L2"

    for prefix in L1_PREFIXES:
        if _starts_with(parts, prefix):
            return "L1"

    for prefix in L0_PREFIXES:
        if _starts_with(parts, prefix):
            return "L0"

    return "L2"


def decide_command(permission_level: str, bound_project: bool = True) -> str:
    if permission_level in {"L1", "L2", "L3"} and not bound_project:
        return "deny"
    if permission_level in {"L0", "L1"}:
        return "allow"
    if permission_level in {"L2", "L3"}:
        return "require_approval"
    return "deny"
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_command_policy.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/command_policy.py tests/test_command_policy.py
git commit -m "feat: add command policy classifier"
```

### Task 4: Implement sensitive value redaction

**Files:**
- Create: `src/cccagents/redaction.py`
- Test: `tests/test_redaction.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_redaction.py`:

```python
from cccagents.redaction import redact_text


def test_redacts_bearer_tokens():
    text = "Authorization: Bearer abcdef1234567890"
    result = redact_text(text)

    assert result.text == "Authorization: Bearer [REDACTED]"
    assert result.redacted is True
    assert "bearer_token" in result.reasons


def test_redacts_api_key_assignments():
    text = "OPENAI_API_KEY=sk-test123456789"
    result = redact_text(text)

    assert result.text == "OPENAI_API_KEY=[REDACTED]"
    assert result.redacted is True
    assert "api_key_assignment" in result.reasons


def test_redacts_password_assignments():
    text = "password = supersecret"
    result = redact_text(text)

    assert result.text == "password=[REDACTED]"
    assert result.redacted is True
    assert "password_assignment" in result.reasons


def test_leaves_safe_text_unchanged():
    text = "npm test completed successfully"
    result = redact_text(text)

    assert result.text == text
    assert result.redacted is False
    assert result.reasons == []
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_redaction.py -v
```

Expected: FAIL because `cccagents.redaction` does not exist.

- [ ] **Step 3: Implement redaction**

Create `src/cccagents/redaction.py`:

```python
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RedactionResult:
    text: str
    redacted: bool
    reasons: list[str]


PATTERNS = [
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    ("api_key_assignment", re.compile(r"(?i)([A-Z0-9_]*API[_-]?KEY)\s*=\s*\S+"), r"\1=[REDACTED]"),
    ("password_assignment", re.compile(r"(?i)(password)\s*=\s*\S+"), r"\1=[REDACTED]"),
]


def redact_text(text: str) -> RedactionResult:
    redacted_text = text
    reasons: list[str] = []

    for reason, pattern, replacement in PATTERNS:
        redacted_text, count = pattern.subn(replacement, redacted_text)
        if count:
            reasons.append(reason)

    return RedactionResult(
        text=redacted_text,
        redacted=bool(reasons),
        reasons=reasons,
    )
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_redaction.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/redaction.py tests/test_redaction.py
git commit -m "feat: add sensitive output redaction"
```

### Task 5: Implement command log record writer

**Files:**
- Create: `src/cccagents/command_log.py`
- Test: `tests/test_command_log.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_command_log.py`:

```python
import json

from cccagents.command_log import CommandLogRecord, append_command_log


def test_append_command_log_writes_json_line(tmp_path):
    path = tmp_path / "projects" / "proj_001" / "08-logs" / "command-log.jsonl"
    record = CommandLogRecord(
        project_id="proj_001",
        task_id="task_001",
        run_id="run_001",
        phase="PHASE_1C",
        agent_role="DEV",
        cwd="/srv/cccagents/workspaces/proj_001/repo",
        command="git status",
        permission_level="L0",
        policy_decision="allow",
        risk_reason="read_only_git_status",
        approval_id=None,
        started_at="2026-05-19T10:00:00+08:00",
        completed_at="2026-05-19T10:00:01+08:00",
        exit_code=0,
        stdout_path="projects/proj_001/08-logs/agent-runs/run_001/stdout.log",
        stderr_path="projects/proj_001/08-logs/agent-runs/run_001/stderr.log",
        redacted=False,
        redaction_reason=None,
    )

    append_command_log(path, record)

    data = json.loads(path.read_text().strip())
    assert data["project_id"] == "proj_001"
    assert data["command"] == "git status"
    assert data["policy_decision"] == "allow"
    assert data["approval_id"] is None
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_command_log.py -v
```

Expected: FAIL because `cccagents.command_log` does not exist.

- [ ] **Step 3: Implement command log writer**

Create `src/cccagents/command_log.py`:

```python
from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class CommandLogRecord:
    project_id: str
    task_id: str
    run_id: str
    phase: str
    agent_role: str
    cwd: str
    command: str
    permission_level: str
    policy_decision: str
    risk_reason: str
    approval_id: str | None
    started_at: str
    completed_at: str
    exit_code: int
    stdout_path: str
    stderr_path: str
    redacted: bool
    redaction_reason: str | None


def append_command_log(path: Path, record: CommandLogRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True))
        handle.write("\n")
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_command_log.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/command_log.py tests/test_command_log.py
git commit -m "feat: add command log jsonl writer"
```

### Task 6: Implement artifact version path helpers

**Files:**
- Create: `src/cccagents/artifacts.py`
- Test: `tests/test_artifacts.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_artifacts.py`:

```python
from pathlib import Path

from cccagents.artifacts import artifact_path


def test_tech_design_draft_path_uses_version():
    path = artifact_path(Path("projects/proj_001"), "tech-design", "tech-design", "draft", 2, "md")

    assert path == Path("projects/proj_001/02-tech-design/tech-design.v2.draft.md")


def test_test_checklist_final_xlsx_path():
    path = artifact_path(Path("projects/proj_001"), "test-cases", "test-checklist", "final", 1, "xlsx")

    assert path == Path("projects/proj_001/03-test-cases/test-checklist.v1.final.xlsx")


def test_review_artifact_path():
    path = artifact_path(Path("projects/proj_001"), "tech-design", "tech-design-review", "review", 3, "md")

    assert path == Path("projects/proj_001/02-tech-design/tech-design-review.v3.review.md")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_artifacts.py -v
```

Expected: FAIL because `cccagents.artifacts` does not exist.

- [ ] **Step 3: Implement artifact path helpers**

Create `src/cccagents/artifacts.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_artifacts.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/artifacts.py tests/test_artifacts.py
git commit -m "feat: add artifact version path helpers"
```

### Task 7: Implement test checklist Markdown-to-Excel conversion

**Files:**
- Create: `src/cccagents/test_checklist.py`
- Test: `tests/test_test_checklist.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_test_checklist.py`:

```python
from openpyxl import load_workbook

from cccagents.test_checklist import CHECKLIST_FIELDS, markdown_table_to_xlsx


def test_markdown_table_to_xlsx_preserves_schema(tmp_path):
    markdown_path = tmp_path / "test-checklist.final.md"
    xlsx_path = tmp_path / "test-checklist.final.xlsx"
    markdown_path.write_text(
        "| case_id | requirement_id | module | scenario | preconditions | steps | expected_result | priority | case_type | execution_status | actual_result | defect_id | remark |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| TC-001 | REQ-001 | login | valid login | user exists | submit credentials | login succeeds | P0 | functional | not_run |  |  |  |\n",
        encoding="utf-8",
    )

    markdown_table_to_xlsx(markdown_path, xlsx_path)

    workbook = load_workbook(xlsx_path)
    sheet = workbook.active
    headers = [cell.value for cell in sheet[1]]
    row = [cell.value for cell in sheet[2]]

    assert headers == CHECKLIST_FIELDS
    assert row[0] == "TC-001"
    assert row[9] == "not_run"


def test_markdown_table_to_xlsx_rejects_wrong_header(tmp_path):
    markdown_path = tmp_path / "bad.md"
    xlsx_path = tmp_path / "bad.xlsx"
    markdown_path.write_text(
        "| case_id | module |\n"
        "| --- | --- |\n"
        "| TC-001 | login |\n",
        encoding="utf-8",
    )

    try:
        markdown_table_to_xlsx(markdown_path, xlsx_path)
    except ValueError as error:
        assert "Checklist header mismatch" in str(error)
    else:
        raise AssertionError("Expected ValueError")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_test_checklist.py -v
```

Expected: FAIL because `cccagents.test_checklist` does not exist.

- [ ] **Step 3: Implement conversion**

Create `src/cccagents/test_checklist.py`:

```python
from pathlib import Path

from openpyxl import Workbook


CHECKLIST_FIELDS = [
    "case_id",
    "requirement_id",
    "module",
    "scenario",
    "preconditions",
    "steps",
    "expected_result",
    "priority",
    "case_type",
    "execution_status",
    "actual_result",
    "defect_id",
    "remark",
]


def _parse_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def markdown_table_to_xlsx(markdown_path: Path, xlsx_path: Path) -> None:
    lines = [line for line in markdown_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("Markdown checklist must contain header and separator")

    header = _parse_markdown_row(lines[0])
    if header != CHECKLIST_FIELDS:
        raise ValueError(f"Checklist header mismatch: {header}")

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "test-checklist"
    sheet.append(CHECKLIST_FIELDS)

    for line in lines[2:]:
        row = _parse_markdown_row(line)
        if len(row) != len(CHECKLIST_FIELDS):
            raise ValueError(f"Checklist row length mismatch: {row}")
        sheet.append(row)

    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(xlsx_path)
```

- [ ] **Step 4: Install dev dependencies**

Run:

```bash
python -m pip install -r requirements-dev.txt
```

Expected: installs `pytest` and `openpyxl` successfully.

- [ ] **Step 5: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_test_checklist.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/cccagents/test_checklist.py tests/test_test_checklist.py requirements-dev.txt
git commit -m "feat: add test checklist excel export"
```

### Task 8: Add Phase 1 Linux install and capability scripts

**Files:**
- Create: `scripts/phase1/install_claude_code_ubuntu.sh`
- Create: `scripts/phase1/collect_claude_code_capabilities.sh`
- Create: `scripts/phase1/verify_project_workspace.sh`

- [ ] **Step 1: Create install script**

Create `scripts/phase1/install_claude_code_ubuntu.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

lsb_release -a
sudo apt update
sudo apt install -y curl git build-essential
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
npm install -g @anthropic-ai/claude-code
claude --version
claude --help
```

- [ ] **Step 2: Create capability collection script**

Create `scripts/phase1/collect_claude_code_capabilities.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPORT_PATH="${1:-docs/phase1/phase1b-capability-report.md}"
mkdir -p "$(dirname "$REPORT_PATH")"

{
  echo "# Phase 1B Claude Code CLI Capability Report"
  echo
  echo "## System"
  echo
  echo '```text'
  date -Is
  uname -a
  echo '```'
  echo
  echo "## Claude Code Version"
  echo
  echo '```text'
  claude --version || true
  echo '```'
  echo
  echo "## Claude Help"
  echo
  echo '```text'
  claude --help || true
  echo '```'
  echo
  echo "## OpenAI-Compatible Gate Checklist"
  echo
  echo "- [ ] Found native base_url configuration"
  echo "- [ ] Found native api_key configuration"
  echo "- [ ] Found native model configuration"
  echo "- [ ] Verified request reached OpenAI-compatible gateway"
  echo "- [ ] No protocol adapter used"
  echo
  echo "## Decision"
  echo
  echo "Status: pending"
} > "$REPORT_PATH"

printf 'Wrote %s\n' "$REPORT_PATH"
```

- [ ] **Step 3: Create workspace verification script**

Create `scripts/phase1/verify_project_workspace.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${1:?project_id required}"
ROOT="${2:-$HOME/cccagents}"

mkdir -p "$ROOT/workspaces/$PROJECT_ID/repo"
mkdir -p "$ROOT/projects/$PROJECT_ID/08-logs/agent-runs"

test -d "$ROOT/workspaces/$PROJECT_ID/repo"
test -d "$ROOT/projects/$PROJECT_ID/08-logs"

printf 'workspace=%s\n' "$ROOT/workspaces/$PROJECT_ID/repo"
printf 'project=%s\n' "$ROOT/projects/$PROJECT_ID"
```

- [ ] **Step 4: Make scripts executable**

Run:

```bash
chmod +x scripts/phase1/install_claude_code_ubuntu.sh scripts/phase1/collect_claude_code_capabilities.sh scripts/phase1/verify_project_workspace.sh
```

Expected: no output.

- [ ] **Step 5: Run shell syntax checks**

Run:

```bash
bash -n scripts/phase1/install_claude_code_ubuntu.sh && bash -n scripts/phase1/collect_claude_code_capabilities.sh && bash -n scripts/phase1/verify_project_workspace.sh
```

Expected: exit code 0.

- [ ] **Step 6: Commit**

```bash
git add scripts/phase1/install_claude_code_ubuntu.sh scripts/phase1/collect_claude_code_capabilities.sh scripts/phase1/verify_project_workspace.sh
git commit -m "feat: add phase 1 linux verification scripts"
```

### Task 9: Add Phase 1 operating documents

**Files:**
- Create: `docs/phase1/linux-install-checklist.md`
- Create: `docs/phase1/openai-compat-gate.md`
- Create: `docs/phase1/executor-run-model.md`
- Create: `docs/phase1/command-policy.md`
- Create: `docs/phase1/security-and-redaction.md`
- Create: `docs/phase1/test-checklist-format.md`
- Create: `docs/phase1/feishu-security-notes.md`

- [ ] **Step 1: Create Linux install checklist**

Create `docs/phase1/linux-install-checklist.md`:

```markdown
# Phase 1A Linux Install Checklist

Target environment:

- Ubuntu 22.04 or 24.04
- Host installation, no Docker in Phase 1
- Normal Linux user for daily execution

Commands:

```bash
lsb_release -a
sudo apt update
sudo apt install -y curl git build-essential
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
npm install -g @anthropic-ai/claude-code
claude --version
claude --help
```

Pass criteria:

- `claude --version` prints a version.
- `claude --help` prints help.
- Commands are saved in the Linux server operation log.
```

- [ ] **Step 2: Create OpenAI compatibility gate document**

Create `docs/phase1/openai-compat-gate.md`:

```markdown
# Phase 1B OpenAI-Compatible Gate

This is the project stop/go gate.

Pass only if Claude Code CLI itself can directly use all of these values without a protocol adapter:

- `base_url`
- `api_key`
- `model`

Fail if any of these is required:

- Anthropic-only protocol
- Claude official model only
- Protocol adapter
- Replacement executor
- Split model source where Claude Code CLI uses a different provider

Evidence to save:

- Claude Code CLI version
- Install source
- Help/config output showing supported configuration
- Redacted configuration snippet
- Command used for the verification run
- Gateway access evidence
- Output artifact path
- Final decision: `pass` or `fail`
```

- [ ] **Step 3: Create executor run model document**

Create `docs/phase1/executor-run-model.md`:

```markdown
# Phase 1 Executor Run Model

Phase 1 uses one Claude Code CLI session per task.

Flow:

```text
Task -> Executor Adapter -> new run_id -> Claude Code CLI -> logs/artifacts -> Task status update
```

Each run must bind:

- `project_id`
- `task_id`
- `run_id`
- `agent_role`
- `phase`
- `workspace_root`

The command working directory must be inside:

```text
workspaces/<project_id>/repo/
projects/<project_id>/
```

Long-running tmux/systemd/queue worker modes are Phase 4 concerns.
```

- [ ] **Step 4: Create command policy document**

Create `docs/phase1/command-policy.md`:

```markdown
# Command Policy

Default automation boundary:

- L0: allow
- L1: allow when bound to a project
- L2: require approval
- L3: require approval

Deny:

- Cross-project workspace access
- Unbound write command
- Command containing visible API keys, tokens, or passwords
- L2/L3 command without approval

Classification examples:

| Command | Level | Decision |
| --- | --- | --- |
| `git status` | L0 | allow |
| `git diff` | L0 | allow |
| `pytest` | L1 | allow |
| `npm test` | L1 | allow |
| `npm install` | L2 | require approval |
| `pip install requests` | L2 | require approval |
| `git push` | L3 | require approval |
| `gh pr create` | L3 | require approval |
| `kubectl apply -f deploy.yaml` | L3 | require approval |
| `rm -rf /tmp/demo` | L3 | require approval |
```

- [ ] **Step 5: Create security and redaction document**

Create `docs/phase1/security-and-redaction.md`:

```markdown
# Security and Redaction

Rules:

- Store model secrets by reference as `model_api_key_ref`.
- Do not write API keys into command logs.
- Do not write API keys into artifacts.
- Do not show secrets in Feishu messages.
- Redact stdout and stderr before storing normal logs.

Initial redaction patterns:

- `Bearer <token>`
- `<NAME>API_KEY=<value>`
- `password=<value>`

If a secret is detected:

- Store the redacted text.
- Set `redacted=true`.
- Store `redaction_reason`.
- Do not send the raw content to Feishu.
```

- [ ] **Step 6: Create test checklist format document**

Create `docs/phase1/test-checklist-format.md`:

```markdown
# Test Checklist Format

Markdown is the source file. Excel is generated from Markdown.

Fields:

| field | meaning |
| --- | --- |
| case_id | Unique test case id |
| requirement_id | Linked requirement id |
| module | Functional module |
| scenario | Test scenario |
| preconditions | Preconditions |
| steps | Test steps |
| expected_result | Expected result |
| priority | P0/P1/P2 |
| case_type | functional/boundary/exception/regression/security |
| execution_status | not_run/pass/fail/blocked |
| actual_result | Actual result |
| defect_id | Linked defect id |
| remark | Extra notes |
```

- [ ] **Step 7: Create Feishu security notes**

Create `docs/phase1/feishu-security-notes.md`:

```markdown
# Feishu Security Notes

Phase 3 must verify:

- Event callback signature verification
- Timestamp validation window
- Replay attack protection
- Feishu user id to approver mapping
- Approval action authorization
- No secret values in card content

Feishu is an entry and approval channel, not the source of truth. Hermes state remains authoritative.
```

- [ ] **Step 8: Commit**

```bash
git add docs/phase1/linux-install-checklist.md docs/phase1/openai-compat-gate.md docs/phase1/executor-run-model.md docs/phase1/command-policy.md docs/phase1/security-and-redaction.md docs/phase1/test-checklist-format.md docs/phase1/feishu-security-notes.md
git commit -m "docs: add phase 1 operating documents"
```

### Task 10: Run full Phase 1 local verification

**Files:**
- Modify only if previous tests reveal issues.

- [ ] **Step 1: Run all Python tests**

Run:

```bash
PYTHONPATH=src pytest tests -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run shell syntax checks**

Run:

```bash
bash -n scripts/phase1/install_claude_code_ubuntu.sh && bash -n scripts/phase1/collect_claude_code_capabilities.sh && bash -n scripts/phase1/verify_project_workspace.sh
```

Expected: exit code 0.

- [ ] **Step 3: Generate local capability report dry run**

Run:

```bash
scripts/phase1/collect_claude_code_capabilities.sh docs/phase1/phase1b-capability-report.md
```

Expected output:

```text
Wrote docs/phase1/phase1b-capability-report.md
```

- [ ] **Step 4: Verify workspace script dry run**

Run:

```bash
scripts/phase1/verify_project_workspace.sh proj_001 /tmp/cccagents-phase1
```

Expected output contains:

```text
workspace=/tmp/cccagents-phase1/workspaces/proj_001/repo
project=/tmp/cccagents-phase1/projects/proj_001
```

- [ ] **Step 5: Commit generated report if useful**

If `docs/phase1/phase1b-capability-report.md` contains useful local evidence, commit it:

```bash
git add docs/phase1/phase1b-capability-report.md
git commit -m "docs: add phase 1 capability report template"
```

If it only contains local machine noise, remove it before committing:

```bash
rm docs/phase1/phase1b-capability-report.md
git status --short
```

- [ ] **Step 6: Final status check**

Run:

```bash
git status --short
```

Expected: no uncommitted changes except intentionally untracked local files.

## Self-Review Notes

Spec coverage:

- Phase 1A install is covered by Task 8 and Task 9.
- Phase 1B gate is covered by Task 8 and Task 9.
- Phase 1C local execution evidence is covered by Task 5, Task 8, and Task 10.
- Multi-project workspace isolation is covered by Task 2.
- Executor run model is documented by Task 9.
- Command Policy Engine is covered by Task 3 and Task 9.
- Secret redaction is covered by Task 4 and Task 9.
- Command log schema is covered by Task 5.
- Artifact versioning is covered by Task 6.
- Test checklist Markdown/Excel conversion is covered by Task 7.
- Feishu security notes are documented by Task 9.

Known out of scope for this plan:

- Full Hermes Agent Runtime implementation.
- Feishu Bot implementation.
- Long-running tmux/systemd/queue worker orchestration.
- Real Claude Code CLI OpenAI-compatible verification on the target Linux server. This requires the user's server and gateway credentials and is performed after this repository foundation exists.
