# cccagents Phase 2 Workflow Implementation Plan

> Paused on 2026-05-19: 本计划 Task 8-10 不再继续执行，直到确认这些本地 Python 组件作为 Hermes 适配层仍然需要。新的 Phase 2 执行计划见 `docs/superpowers/plans/2026-05-19-cccagents-phase2-hermes-integration-plan.md`。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Phase 2 workflow prototype that can represent Hermes multi-agent roles, project tasks, artifacts, review gates, workflow transitions, and Claude Code CLI executor requests without Feishu or long-running workers.

**Architecture:** Keep Phase 2 as a local Python utility layer over filesystem artifacts and SQLite state. The implementation should encode the workflow rules from `docs/superpowers/specs/2026-05-19-cccagents-phase2-workflow-design.md` while reusing Phase 1 helpers for project paths, command policy, command logs, artifact paths, and checklist export. No network services or background daemons are introduced in Phase 2.

**Tech Stack:** Python 3 standard library, sqlite3, dataclasses, pathlib, pytest, existing Phase 1 modules.

---

## File Structure

Create these files:

```text
src/cccagents/phase2_models.py
src/cccagents/project_init.py
src/cccagents/artifact_store.py
src/cccagents/task_store.py
src/cccagents/workflow.py
src/cccagents/review_gate.py
src/cccagents/agent_config.py
src/cccagents/executor_request.py
src/cccagents/phase2_dry_run.py

tests/test_phase2_models.py
tests/test_project_init.py
tests/test_artifact_store.py
tests/test_task_store.py
tests/test_workflow.py
tests/test_review_gate.py
tests/test_agent_config.py
tests/test_executor_request.py
tests/test_phase2_dry_run.py
```

Responsibilities:

```text
phase2_models.py
- Shared enums/constants and dataclasses for Project, Task, Review, Artifact, Issue, AgentModelConfig.

project_init.py
- Initialize the Phase 2 project directory structure under projects/<project_id>/ and workspaces/<project_id>/repo/.

artifact_store.py
- Register artifact metadata and generate phase-specific artifact paths.

task_store.py
- SQLite-backed local Task Store for Project, Task, Review, Artifact, Issue rows.

workflow.py
- State transition rules for main workflow and parallel tech/test flows.

review_gate.py
- Review pass/fail handling and next_handler_role decisions.

agent_config.py
- Agent role model configuration and secret-reference validation.

executor_request.py
- Build Claude Code CLI execution requests with ANTHROPIC_* env mapping.

phase2_dry_run.py
- Local dry run that creates a project and advances through requirement approval into parallel design/test flows and development gate.
```

## Implementation Tasks

### Task 1: Define Phase 2 models

**Files:**
- Create: `src/cccagents/phase2_models.py`
- Test: `tests/test_phase2_models.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_phase2_models.py`:

```python
from cccagents.phase2_models import (
    AGENT_ROLES,
    Artifact,
    ArtifactStatus,
    Task,
    TaskStatus,
)


def test_agent_roles_include_all_phase2_roles():
    assert AGENT_ROLES == ("PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC")


def test_task_defaults_to_pending_without_started_time():
    task = Task(
        id="task_001",
        project_id="proj_001",
        phase="REQUIREMENT_DRAFTING",
        flow="main",
        assignee_role="PDM",
        title="Draft PRD",
        description="Create PRD draft",
        created_at="2026-05-19T10:00:00Z",
    )

    assert task.status == TaskStatus.PENDING
    assert task.started_at is None
    assert task.next_handler_role == "PDM"


def test_artifact_records_path_version_and_status():
    artifact = Artifact(
        id="artifact_001",
        project_id="proj_001",
        phase="requirements",
        owner_role="PDM",
        type="prd",
        path="projects/proj_001/01-requirements/prd.v1.draft.md",
        version=1,
        status=ArtifactStatus.DRAFT,
        created_at="2026-05-19T10:00:00Z",
    )

    assert artifact.version == 1
    assert artifact.status == ArtifactStatus.DRAFT
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_phase2_models.py -v
```

Expected: FAIL because `cccagents.phase2_models` does not exist.

- [ ] **Step 3: Implement models**

Create `src/cccagents/phase2_models.py`:

```python
from dataclasses import dataclass, field
from enum import StrEnum


AGENT_ROLES = ("PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC")


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class ArtifactStatus(StrEnum):
    DRAFT = "draft"
    FINAL = "final"
    REVIEW = "review"
    REPORT = "report"
    LOG = "log"


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    status: str
    current_phase: str
    owner: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Task:
    id: str
    project_id: str
    phase: str
    flow: str
    assignee_role: str
    title: str
    description: str
    created_at: str
    parent_task_id: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    input_artifact_ids: list[str] = field(default_factory=list)
    output_artifact_ids: list[str] = field(default_factory=list)
    issue_ids: list[str] = field(default_factory=list)
    started_at: str | None = None
    updated_at: str | None = None
    due_at: str | None = None
    completed_at: str | None = None
    next_handler_role: str | None = None
    next_handler_reason: str | None = None

    def __post_init__(self) -> None:
        if self.next_handler_role is None:
            object.__setattr__(self, "next_handler_role", self.assignee_role)


@dataclass(frozen=True)
class Review:
    id: str
    project_id: str
    phase: str
    review_type: str
    status: str
    participants: list[str]
    required_roles: list[str]
    issues: list[str]
    decision_summary: str
    created_at: str
    completed_at: str | None = None


@dataclass(frozen=True)
class Artifact:
    id: str
    project_id: str
    phase: str
    owner_role: str
    type: str
    path: str
    version: int
    status: ArtifactStatus
    created_at: str
    updated_at: str | None = None
    source_artifact_id: str | None = None


@dataclass(frozen=True)
class Issue:
    id: str
    project_id: str
    source: str
    severity: str
    title: str
    description: str
    owner_role: str
    status: str
    created_at: str
    related_task_id: str | None = None
    related_artifact_id: str | None = None
    updated_at: str | None = None
    closed_at: str | None = None


@dataclass(frozen=True)
class AgentModelConfig:
    role_code: str
    model_base_url: str
    model_api_key_ref: str
    model_name: str
    executor_type: str = "claude_code_cli"
    enabled: bool = True
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_phase2_models.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/phase2_models.py tests/test_phase2_models.py
git commit -m "feat: add phase 2 workflow models"
```

### Task 2: Initialize project directories

**Files:**
- Create: `src/cccagents/project_init.py`
- Test: `tests/test_project_init.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_project_init.py`:

```python
from cccagents.paths import ProjectPaths
from cccagents.project_init import initialize_project_structure


def test_initialize_project_structure_creates_workspace_and_artifact_dirs(tmp_path):
    paths = ProjectPaths(root=tmp_path, project_id="proj_001")

    created = initialize_project_structure(paths)

    assert paths.workspace_root.is_dir()
    assert (paths.project_root / "00-meta").is_dir()
    assert (paths.project_root / "01-requirements").is_dir()
    assert (paths.project_root / "02-tech-design").is_dir()
    assert (paths.project_root / "03-test-cases").is_dir()
    assert (paths.project_root / "08-logs" / "agent-runs").is_dir()
    assert paths.command_log.parent.is_dir()
    assert paths.workspace_root in created
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_project_init.py -v
```

Expected: FAIL because `cccagents.project_init` does not exist.

- [ ] **Step 3: Implement initializer**

Create `src/cccagents/project_init.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_project_init.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/project_init.py tests/test_project_init.py
git commit -m "feat: add project structure initializer"
```

### Task 3: Add artifact store registration

**Files:**
- Create: `src/cccagents/artifact_store.py`
- Test: `tests/test_artifact_store.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_artifact_store.py`:

```python
from pathlib import Path

from cccagents.artifact_store import register_artifact
from cccagents.phase2_models import ArtifactStatus


def test_register_artifact_returns_versioned_path_and_metadata():
    artifact = register_artifact(
        project_id="proj_001",
        project_root=Path("projects/proj_001"),
        phase="requirements",
        owner_role="PDM",
        artifact_type="prd",
        name="prd",
        status=ArtifactStatus.DRAFT,
        version=1,
        extension="md",
        created_at="2026-05-19T10:00:00Z",
    )

    assert artifact.path == "projects/proj_001/01-requirements/prd.v1.draft.md"
    assert artifact.owner_role == "PDM"
    assert artifact.version == 1
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_artifact_store.py -v
```

Expected: FAIL because `cccagents.artifact_store` does not exist.

- [ ] **Step 3: Implement artifact registration**

Create `src/cccagents/artifact_store.py`:

```python
from pathlib import Path
from uuid import uuid4

from cccagents.artifacts import artifact_path
from cccagents.phase2_models import Artifact, ArtifactStatus


def register_artifact(
    project_id: str,
    project_root: Path,
    phase: str,
    owner_role: str,
    artifact_type: str,
    name: str,
    status: ArtifactStatus,
    version: int,
    extension: str,
    created_at: str,
    source_artifact_id: str | None = None,
) -> Artifact:
    path = artifact_path(project_root, phase, name, status.value, version, extension)
    return Artifact(
        id=f"artifact_{uuid4().hex}",
        project_id=project_id,
        phase=phase,
        owner_role=owner_role,
        type=artifact_type,
        path=str(path),
        version=version,
        status=status,
        source_artifact_id=source_artifact_id,
        created_at=created_at,
    )
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_artifact_store.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/artifact_store.py tests/test_artifact_store.py
git commit -m "feat: add artifact registration helper"
```

### Task 4: Add SQLite task store

**Files:**
- Create: `src/cccagents/task_store.py`
- Test: `tests/test_task_store.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_task_store.py`:

```python
from cccagents.phase2_models import Task, TaskStatus
from cccagents.task_store import TaskStore


def test_task_store_saves_and_loads_task(tmp_path):
    store = TaskStore(tmp_path / "state.db")
    store.initialize()
    task = Task(
        id="task_001",
        project_id="proj_001",
        phase="REQUIREMENT_DRAFTING",
        flow="main",
        assignee_role="PDM",
        title="Draft PRD",
        description="Create PRD draft",
        created_at="2026-05-19T10:00:00Z",
    )

    store.save_task(task)
    loaded = store.get_task("task_001")

    assert loaded.id == "task_001"
    assert loaded.status == TaskStatus.PENDING
    assert loaded.next_handler_role == "PDM"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_task_store.py -v
```

Expected: FAIL because `cccagents.task_store` does not exist.

- [ ] **Step 3: Implement TaskStore**

Create `src/cccagents/task_store.py`:

```python
import json
import sqlite3
from pathlib import Path

from cccagents.phase2_models import Task, TaskStatus


class TaskStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    flow TEXT NOT NULL,
                    assignee_role TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    parent_task_id TEXT,
                    input_artifact_ids TEXT NOT NULL,
                    output_artifact_ids TEXT NOT NULL,
                    issue_ids TEXT NOT NULL,
                    started_at TEXT,
                    updated_at TEXT,
                    due_at TEXT,
                    completed_at TEXT,
                    next_handler_role TEXT,
                    next_handler_reason TEXT
                )
                """
            )

    def save_task(self, task: Task) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.project_id,
                    task.phase,
                    task.flow,
                    task.assignee_role,
                    task.title,
                    task.description,
                    task.created_at,
                    task.status.value,
                    task.parent_task_id,
                    json.dumps(task.input_artifact_ids),
                    json.dumps(task.output_artifact_ids),
                    json.dumps(task.issue_ids),
                    task.started_at,
                    task.updated_at,
                    task.due_at,
                    task.completed_at,
                    task.next_handler_role,
                    task.next_handler_reason,
                ),
            )

    def get_task(self, task_id: str) -> Task:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)

        return Task(
            id=row[0],
            project_id=row[1],
            phase=row[2],
            flow=row[3],
            assignee_role=row[4],
            title=row[5],
            description=row[6],
            created_at=row[7],
            status=TaskStatus(row[8]),
            parent_task_id=row[9],
            input_artifact_ids=json.loads(row[10]),
            output_artifact_ids=json.loads(row[11]),
            issue_ids=json.loads(row[12]),
            started_at=row[13],
            updated_at=row[14],
            due_at=row[15],
            completed_at=row[16],
            next_handler_role=row[17],
            next_handler_reason=row[18],
        )
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_task_store.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/task_store.py tests/test_task_store.py
git commit -m "feat: add sqlite task store"
```

### Task 5: Add workflow transition rules

**Files:**
- Create: `src/cccagents/workflow.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_workflow.py`:

```python
import pytest

from cccagents.workflow import can_enter_development, next_main_phase


def test_next_main_phase_advances_requirement_flow():
    assert next_main_phase("CREATED") == "REQUIREMENT_DRAFTING"
    assert next_main_phase("REQUIREMENT_DRAFTING") == "REQUIREMENT_REVIEW"
    assert next_main_phase("REQUIREMENT_REVIEW", review_passed=True) == "REQUIREMENT_APPROVED"


def test_requirement_review_failure_returns_to_drafting():
    assert next_main_phase("REQUIREMENT_REVIEW", review_passed=False) == "REQUIREMENT_DRAFTING"


def test_can_enter_development_requires_both_parallel_flows():
    assert can_enter_development("TECH_DESIGN_APPROVED", "TEST_CASE_APPROVED") is True
    assert can_enter_development("TECH_DESIGN_APPROVED", "TEST_CASE_REVIEW") is False


def test_unknown_phase_is_rejected():
    with pytest.raises(ValueError, match="Unknown main phase"):
        next_main_phase("NOPE")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_workflow.py -v
```

Expected: FAIL because `cccagents.workflow` does not exist.

- [ ] **Step 3: Implement workflow rules**

Create `src/cccagents/workflow.py`:

```python
MAIN_TRANSITIONS = {
    "CREATED": "REQUIREMENT_DRAFTING",
    "REQUIREMENT_DRAFTING": "REQUIREMENT_REVIEW",
    "REQUIREMENT_APPROVED": "PARALLEL_DESIGN_AND_TESTCASE",
    "PARALLEL_DESIGN_AND_TESTCASE": "DEVELOPMENT",
    "DEVELOPMENT": "DEV_SELF_TEST",
    "DEV_SELF_TEST": "TESTING_AND_SECURITY",
    "TESTING_AND_SECURITY": "PRODUCT_ACCEPTANCE",
    "PRODUCT_ACCEPTANCE": "DONE",
}


def next_main_phase(current_phase: str, review_passed: bool | None = None) -> str:
    if current_phase == "REQUIREMENT_REVIEW":
        if review_passed is None:
            raise ValueError("review_passed is required for REQUIREMENT_REVIEW")
        return "REQUIREMENT_APPROVED" if review_passed else "REQUIREMENT_DRAFTING"

    if current_phase not in MAIN_TRANSITIONS:
        raise ValueError(f"Unknown main phase: {current_phase}")

    return MAIN_TRANSITIONS[current_phase]


def can_enter_development(tech_design_state: str, test_case_state: str) -> bool:
    return tech_design_state == "TECH_DESIGN_APPROVED" and test_case_state == "TEST_CASE_APPROVED"
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_workflow.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/workflow.py tests/test_workflow.py
git commit -m "feat: add phase 2 workflow transitions"
```

### Task 6: Add review gate decisions

**Files:**
- Create: `src/cccagents/review_gate.py`
- Test: `tests/test_review_gate.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_review_gate.py`:

```python
from cccagents.review_gate import review_decision


def test_requirement_review_fail_routes_to_pdm():
    decision = review_decision("requirement", passed=False)

    assert decision.next_phase == "REQUIREMENT_DRAFTING"
    assert decision.next_handler_role == "PDM"


def test_tech_design_review_fail_routes_to_arch():
    decision = review_decision("tech_design", passed=False)

    assert decision.next_phase == "TECH_DESIGN_DRAFTING"
    assert decision.next_handler_role == "ARCH"


def test_test_case_review_fail_routes_to_test():
    decision = review_decision("test_case", passed=False)

    assert decision.next_phase == "TEST_CASE_DRAFTING"
    assert decision.next_handler_role == "TEST"


def test_acceptance_pass_finishes_project():
    decision = review_decision("acceptance", passed=True)

    assert decision.next_phase == "DONE"
    assert decision.next_handler_role is None
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_review_gate.py -v
```

Expected: FAIL because `cccagents.review_gate` does not exist.

- [ ] **Step 3: Implement review gate decisions**

Create `src/cccagents/review_gate.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewDecision:
    next_phase: str
    next_handler_role: str | None
    reason: str


PASS_DECISIONS = {
    "requirement": ReviewDecision("REQUIREMENT_APPROVED", "PM", "requirement_review_passed"),
    "tech_design": ReviewDecision("TECH_DESIGN_APPROVED", "PM", "tech_design_review_passed"),
    "test_case": ReviewDecision("TEST_CASE_APPROVED", "PM", "test_case_review_passed"),
    "self_test": ReviewDecision("TESTING_AND_SECURITY", "TEST", "self_test_passed"),
    "quality_security": ReviewDecision("PRODUCT_ACCEPTANCE", "PDM", "quality_security_passed"),
    "acceptance": ReviewDecision("DONE", None, "acceptance_passed"),
}

FAIL_DECISIONS = {
    "requirement": ReviewDecision("REQUIREMENT_DRAFTING", "PDM", "requirement_review_failed"),
    "tech_design": ReviewDecision("TECH_DESIGN_DRAFTING", "ARCH", "tech_design_review_failed"),
    "test_case": ReviewDecision("TEST_CASE_DRAFTING", "TEST", "test_case_review_failed"),
    "self_test": ReviewDecision("DEVELOPMENT", "DEV", "self_test_failed"),
    "quality_security": ReviewDecision("FIXING", "DEV", "quality_security_failed"),
    "acceptance": ReviewDecision("FIXING", "DEV", "acceptance_failed"),
}


def review_decision(review_type: str, passed: bool) -> ReviewDecision:
    decisions = PASS_DECISIONS if passed else FAIL_DECISIONS
    if review_type not in decisions:
        raise ValueError(f"Unknown review type: {review_type}")
    return decisions[review_type]
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_review_gate.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/review_gate.py tests/test_review_gate.py
git commit -m "feat: add review gate decisions"
```

### Task 7: Add agent model config mapping

**Files:**
- Create: `src/cccagents/agent_config.py`
- Test: `tests/test_agent_config.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_agent_config.py`:

```python
import pytest

from cccagents.agent_config import executor_env
from cccagents.phase2_models import AgentModelConfig


def test_executor_env_maps_agent_model_config_to_anthropic_env():
    config = AgentModelConfig(
        role_code="DEV",
        model_base_url="http://cccai.store",
        model_api_key_ref="secret://models/dev",
        model_name="qwen3.6-plus",
    )

    env = executor_env(config, api_key="secret-value")

    assert env == {
        "ANTHROPIC_BASE_URL": "http://cccai.store",
        "ANTHROPIC_API_KEY": "secret-value",
        "ANTHROPIC_MODEL": "qwen3.6-plus",
    }


def test_executor_env_rejects_empty_secret():
    config = AgentModelConfig(
        role_code="DEV",
        model_base_url="http://cccai.store",
        model_api_key_ref="secret://models/dev",
        model_name="qwen3.6-plus",
    )

    with pytest.raises(ValueError, match="api_key is required"):
        executor_env(config, api_key="")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_agent_config.py -v
```

Expected: FAIL because `cccagents.agent_config` does not exist.

- [ ] **Step 3: Implement env mapping**

Create `src/cccagents/agent_config.py`:

```python
from cccagents.phase2_models import AgentModelConfig


def executor_env(config: AgentModelConfig, api_key: str) -> dict[str, str]:
    if not api_key:
        raise ValueError("api_key is required")
    return {
        "ANTHROPIC_BASE_URL": config.model_base_url,
        "ANTHROPIC_API_KEY": api_key,
        "ANTHROPIC_MODEL": config.model_name,
    }
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_agent_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/agent_config.py tests/test_agent_config.py
git commit -m "feat: map agent model config to executor env"
```

### Task 8: Add executor run request builder

**Files:**
- Create: `src/cccagents/executor_request.py`
- Test: `tests/test_executor_request.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_executor_request.py`:

```python
from pathlib import Path

import pytest

from cccagents.executor_request import build_executor_request
from cccagents.paths import ProjectPaths


def test_build_executor_request_binds_project_and_env(tmp_path):
    paths = ProjectPaths(root=tmp_path, project_id="proj_001")
    paths.workspace_root.mkdir(parents=True)

    request = build_executor_request(
        project_paths=paths,
        task_id="task_001",
        run_id="run_001",
        agent_role="DEV",
        phase="DEVELOPMENT",
        cwd=paths.workspace_root,
        prompt="Run tests",
        allowed_tools=["Bash(pytest *)"],
        permission_mode="acceptEdits",
        env={"ANTHROPIC_MODEL": "qwen3.6-plus"},
    )

    assert request["project_id"] == "proj_001"
    assert request["cwd"] == str(paths.workspace_root.resolve())
    assert request["env"]["ANTHROPIC_MODEL"] == "qwen3.6-plus"


def test_build_executor_request_rejects_cross_project_cwd(tmp_path):
    paths = ProjectPaths(root=tmp_path, project_id="proj_001")
    other = tmp_path / "workspaces" / "proj_002" / "repo"
    other.mkdir(parents=True)

    with pytest.raises(ValueError, match="outside project scope"):
        build_executor_request(
            project_paths=paths,
            task_id="task_001",
            run_id="run_001",
            agent_role="DEV",
            phase="DEVELOPMENT",
            cwd=other,
            prompt="Run tests",
            allowed_tools=["Bash(pytest *)"],
            permission_mode="acceptEdits",
            env={},
        )
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_executor_request.py -v
```

Expected: FAIL because `cccagents.executor_request` does not exist.

- [ ] **Step 3: Implement request builder**

Create `src/cccagents/executor_request.py`:

```python
from pathlib import Path
from typing import Any

from cccagents.paths import ProjectPaths, assert_within_project


def build_executor_request(
    project_paths: ProjectPaths,
    task_id: str,
    run_id: str,
    agent_role: str,
    phase: str,
    cwd: Path,
    prompt: str,
    allowed_tools: list[str],
    permission_mode: str,
    env: dict[str, str],
) -> dict[str, Any]:
    resolved_cwd = assert_within_project(cwd, project_paths)
    return {
        "project_id": project_paths.project_id,
        "task_id": task_id,
        "run_id": run_id,
        "agent_role": agent_role,
        "phase": phase,
        "cwd": str(resolved_cwd),
        "prompt": prompt,
        "allowed_tools": allowed_tools,
        "permission_mode": permission_mode,
        "env": env,
    }
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_executor_request.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/executor_request.py tests/test_executor_request.py
git commit -m "feat: add executor run request builder"
```

### Task 9: Add Phase 2 local dry run

**Files:**
- Create: `src/cccagents/phase2_dry_run.py`
- Test: `tests/test_phase2_dry_run.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_phase2_dry_run.py`:

```python
from cccagents.phase2_dry_run import run_phase2_dry_run


def test_phase2_dry_run_reaches_development_gate(tmp_path):
    result = run_phase2_dry_run(tmp_path, project_id="proj_001")

    assert result["project_id"] == "proj_001"
    assert result["requirement_state"] == "REQUIREMENT_APPROVED"
    assert result["tech_design_state"] == "TECH_DESIGN_APPROVED"
    assert result["test_case_state"] == "TEST_CASE_APPROVED"
    assert result["can_enter_development"] is True
    assert (tmp_path / "projects" / "proj_001" / "01-requirements").is_dir()
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest tests/test_phase2_dry_run.py -v
```

Expected: FAIL because `cccagents.phase2_dry_run` does not exist.

- [ ] **Step 3: Implement dry run**

Create `src/cccagents/phase2_dry_run.py`:

```python
from pathlib import Path

from cccagents.paths import ProjectPaths
from cccagents.project_init import initialize_project_structure
from cccagents.review_gate import review_decision
from cccagents.workflow import can_enter_development


def run_phase2_dry_run(root: Path, project_id: str) -> dict[str, object]:
    paths = ProjectPaths(root=root, project_id=project_id)
    initialize_project_structure(paths)

    requirement = review_decision("requirement", passed=True)
    tech_design = review_decision("tech_design", passed=True)
    test_case = review_decision("test_case", passed=True)

    return {
        "project_id": project_id,
        "requirement_state": requirement.next_phase,
        "tech_design_state": tech_design.next_phase,
        "test_case_state": test_case.next_phase,
        "can_enter_development": can_enter_development(tech_design.next_phase, test_case.next_phase),
    }
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src pytest tests/test_phase2_dry_run.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/phase2_dry_run.py tests/test_phase2_dry_run.py
git commit -m "feat: add phase 2 workflow dry run"
```

### Task 10: Run full Phase 2 verification

**Files:**
- Modify only if verification reveals issues.

- [ ] **Step 1: Run all tests**

Run:

```bash
PYTHONPATH=src pytest tests -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run Phase 2 dry run manually**

Run:

```bash
PYTHONPATH=src python - <<'PY'
from pathlib import Path
from cccagents.phase2_dry_run import run_phase2_dry_run

print(run_phase2_dry_run(Path('/tmp/cccagents-phase2'), 'proj_001'))
PY
```

Expected output contains:

```text
'can_enter_development': True
```

- [ ] **Step 3: Check git status**

Run:

```bash
git status --short
```

Expected: no uncommitted changes except intentionally untracked local files.

- [ ] **Step 4: Commit any verification fixes**

If Step 1 or Step 2 required fixes, commit them with a focused message.
