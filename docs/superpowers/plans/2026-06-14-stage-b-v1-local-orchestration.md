# Stage B v1 Local Orchestration Kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the local S0/S1 orchestration kernel so pending classifier, task store, project state, and orchestrator tests pass without Feishu triggering or real agent execution.

**Architecture:** Add small focused modules: `complexity_classifier.py` classifies requests with deterministic keyword rules; `project_state.py` persists lightweight JSON state; `task_store.py` gains status transition helpers; `orchestrator.py` coordinates S0/S1 flows through a deterministic `FakeExecutor`. S2/S3 classification exists, but orchestration returns `blocked` instead of executing.

**Tech Stack:** Python 3.12, dataclasses, pathlib, json, sqlite3, pytest

---

## File Structure

- Create: `src/cccagents/complexity_classifier.py` — deterministic keyword-based S0/S1/S2/S3 classifier.
- Create: `src/cccagents/project_state.py` — JSON persistence for `project-state.json`.
- Modify: `src/cccagents/task_store.py` — add list/status/claim/complete/fail methods.
- Create: `src/cccagents/orchestrator.py` — S0/S1 local orchestration and `FakeExecutor` artifact generation.
- Existing tests to satisfy:
  - `tests/test_complexity_classifier.py`
  - `tests/test_task_store.py`
  - `tests/test_orchestrator_s0_s1.py`

---

## Task 1: Complexity Classifier

**Files:**
- Create: `src/cccagents/complexity_classifier.py`
- Test: `tests/test_complexity_classifier.py`

- [ ] **Step 1: Run the existing failing classifier tests**

Run:

```bash
PYTHONPATH=src pytest -q tests/test_complexity_classifier.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cccagents.complexity_classifier'`.

- [ ] **Step 2: Create classifier module**

Create `src/cccagents/complexity_classifier.py` with:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ComplexityDecision:
    complexity: str
    required_roles: list[str]
    requires_user_approval: bool
    risk_flags: list[str]


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def classify_project_request(text: str) -> ComplexityDecision:
    if _has_any(text, ("调研", "向量数据库", "技术选型", "方案")):
        return ComplexityDecision(
            complexity="S3",
            required_roles=["PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC"],
            requires_user_approval=False,
            risk_flags=["research_required"],
        )

    if _has_any(text, ("安全", "认证", "权限", "部署", "生产", "secret", "feishu_app_secret")):
        flags = []
        if _has_any(text, ("安全", "认证", "权限", "secret", "feishu_app_secret")):
            flags.append("security_sensitive")
        if _has_any(text, ("部署", "生产")):
            flags.append("external_side_effect")
        return ComplexityDecision(
            complexity="S3",
            required_roles=["PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC"],
            requires_user_approval=True,
            risk_flags=flags,
        )

    if _has_any(text, ("新增", "功能", "接口", "测试用例", "csv")):
        return ComplexityDecision(
            complexity="S2",
            required_roles=["PM", "PDM", "ARCH", "DEV", "TEST"],
            requires_user_approval=False,
            risk_flags=["feature_change"],
        )

    if _has_any(text, ("bug", "loading", "局部", "本地测试")):
        return ComplexityDecision(
            complexity="S1",
            required_roles=["PM", "DEV", "TEST"],
            requires_user_approval=False,
            risk_flags=["local_test_required"],
        )

    if _has_any(text, ("typo", "readme", "文档", "docs")):
        return ComplexityDecision(
            complexity="S0",
            required_roles=["PM", "DEV"],
            requires_user_approval=False,
            risk_flags=["docs_only"],
        )

    return ComplexityDecision(
        complexity="S1",
        required_roles=["PM", "DEV", "TEST"],
        requires_user_approval=False,
        risk_flags=["local_test_required"],
    )
```

- [ ] **Step 3: Run classifier tests**

Run:

```bash
PYTHONPATH=src pytest -q tests/test_complexity_classifier.py
```

Expected: `5 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/cccagents/complexity_classifier.py tests/test_complexity_classifier.py
git commit -m "feat: add deterministic complexity classifier"
```

---

## Task 2: Project State Persistence

**Files:**
- Create: `src/cccagents/project_state.py`
- Test: `tests/test_orchestrator_s0_s1.py`

- [ ] **Step 1: Run orchestrator tests to see current project_state failure**

Run:

```bash
PYTHONPATH=src pytest -q tests/test_orchestrator_s0_s1.py
```

Expected: FAIL with missing `cccagents.orchestrator` or `cccagents.project_state`. This task implements only `project_state.py`; orchestrator remains missing until Task 4.

- [ ] **Step 2: Create project_state module**

Create `src/cccagents/project_state.py` with:

```python
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
```

- [ ] **Step 3: Add a focused project_state test**

Create `tests/test_project_state.py` with:

```python
from cccagents.project_state import ProjectState, load_project_state, save_project_state


def test_project_state_round_trips(tmp_path):
    project_dir = tmp_path / "demo"
    state = ProjectState(
        project_id="demo",
        status="done",
        complexity="S0",
        executed_roles=["DEV", "PM"],
        artifacts=["05-development/dev-summary.md"],
        updated_at="2026-06-14T00:00:00Z",
    )

    save_project_state(project_dir, state)
    loaded = load_project_state(project_dir)

    assert loaded == state
```

- [ ] **Step 4: Run project_state test**

Run:

```bash
PYTHONPATH=src pytest -q tests/test_project_state.py
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/project_state.py tests/test_project_state.py
git commit -m "feat: add project state persistence"
```

---

## Task 3: TaskStore Status Transitions

**Files:**
- Modify: `src/cccagents/task_store.py`
- Test: `tests/test_task_store.py`

- [ ] **Step 1: Run task store tests to verify current failures**

Run:

```bash
PYTHONPATH=src pytest -q tests/test_task_store.py
```

Expected: FAIL with missing `update_status`, `list_tasks`, `claim_task`, `complete_task`, or `fail_task`.

- [ ] **Step 2: Add imports and methods to TaskStore**

Modify `src/cccagents/task_store.py`:

Add import near the top:

```python
from dataclasses import replace
```

Add these methods inside `TaskStore` after `get_task`:

```python
    def list_tasks(self, project_id: str, status: TaskStatus | None = None) -> list[Task]:
        query = "SELECT id FROM tasks WHERE project_id = ?"
        params: list[str] = [project_id]
        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY created_at, id"
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [self.get_task(row[0]) for row in rows]

    def update_status(self, task_id: str, status: TaskStatus, updated_at: str | None = None) -> Task:
        task = self.get_task(task_id)
        updated = replace(task, status=status, updated_at=updated_at or task.updated_at)
        self.save_task(updated)
        return updated

    def claim_task(self, task_id: str, started_at: str) -> Task:
        task = self.get_task(task_id)
        updated = replace(task, status=TaskStatus.RUNNING, started_at=started_at, updated_at=started_at)
        self.save_task(updated)
        return updated

    def complete_task(self, task_id: str, artifact_ids: list[str], completed_at: str) -> Task:
        task = self.get_task(task_id)
        updated = replace(
            task,
            status=TaskStatus.COMPLETED,
            output_artifact_ids=artifact_ids,
            completed_at=completed_at,
            updated_at=completed_at,
        )
        self.save_task(updated)
        return updated

    def fail_task(self, task_id: str, issue_ids: list[str], updated_at: str) -> Task:
        task = self.get_task(task_id)
        updated = replace(task, status=TaskStatus.FAILED, issue_ids=issue_ids, updated_at=updated_at)
        self.save_task(updated)
        return updated
```

- [ ] **Step 3: Run task store tests**

Run:

```bash
PYTHONPATH=src pytest -q tests/test_task_store.py
```

Expected: `3 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/cccagents/task_store.py tests/test_task_store.py
git commit -m "feat: add task store status transitions"
```

---

## Task 4: S0/S1 Local Orchestrator

**Files:**
- Create: `src/cccagents/orchestrator.py`
- Test: `tests/test_orchestrator_s0_s1.py`

- [ ] **Step 1: Run orchestrator tests to verify failure**

Run:

```bash
PYTHONPATH=src pytest -q tests/test_orchestrator_s0_s1.py
```

Expected: FAIL with missing `cccagents.orchestrator`.

- [ ] **Step 2: Create orchestrator module**

Create `src/cccagents/orchestrator.py` with:

```python
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
```

- [ ] **Step 3: Run orchestrator tests**

Run:

```bash
PYTHONPATH=src pytest -q tests/test_orchestrator_s0_s1.py
```

Expected: `2 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/cccagents/orchestrator.py tests/test_orchestrator_s0_s1.py
git commit -m "feat: add S0 S1 local orchestrator"
```

---

## Task 5: Stage B v1 Verification

**Files:**
- Modify: `docs/deployment-log.md`

- [ ] **Step 1: Run focused Stage B v1 tests**

Run:

```bash
PYTHONPATH=src pytest -q tests/test_complexity_classifier.py tests/test_orchestrator_s0_s1.py tests/test_task_store.py tests/test_project_state.py
```

Expected: all tests pass.

- [ ] **Step 2: Run full test suite**

Run:

```bash
PYTHONPATH=src pytest -q tests
```

Expected: all tests pass, unless unrelated pre-existing failures appear. If unrelated failures appear, record exact failing tests and do not expand scope.

- [ ] **Step 3: Update deployment log**

Append to `docs/deployment-log.md`:

```markdown
### 16. Stage B v1 本地编排内核 ✅

实施时间：2026-06-14

**完成内容：**

1. `complexity_classifier.py` 支持 S0/S1/S2/S3 关键词分类。
2. `project_state.py` 支持 `project-state.json` 读写。
3. `task_store.py` 支持 list/status/claim/complete/fail。
4. `orchestrator.py` 支持 S0/S1 本地编排。
5. `FakeExecutor` 生成 DEV、TEST、PM 验收产物。

**验证：**

```text
PYTHONPATH=src pytest -q tests/test_complexity_classifier.py tests/test_orchestrator_s0_s1.py tests/test_task_store.py tests/test_project_state.py
```

结果：全部通过。

**当前边界：**

Stage B v1 不接 Feishu 自动触发，不执行真实多 Agent，不执行部署/重启/commit/push。后续 Stage B v2 再设计 Feishu 触发 S0/S1 编排。
```

- [ ] **Step 4: Commit verification log**

```bash
git add docs/deployment-log.md
git commit -m "docs: record Stage B v1 local orchestration verification"
```

---

## Self-Review Checklist

- Spec coverage:
  - Complexity classifier: Task 1.
  - Project state persistence: Task 2.
  - TaskStore transitions: Task 3.
  - S0/S1 orchestrator and FakeExecutor: Task 4.
  - Focused and full tests plus deployment log: Task 5.
- Placeholder scan: no `TBD`, `TODO`, `implement later`, or unspecified steps.
- Type consistency: `ComplexityDecision`, `ProjectState`, `OrchestrationRequest`, and `OrchestrationResult` match the design spec; `TaskStore` method signatures match tests.
