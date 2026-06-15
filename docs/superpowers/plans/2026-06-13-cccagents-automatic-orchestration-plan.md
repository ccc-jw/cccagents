# cccagents Automatic Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first-round automatic orchestration layer (M0-M3) so cccagents can classify work, dynamically select roles, drive S0/S1/S2 flows with fake execution, review gates, automatic acceptance, and safe recovery foundations.

**Architecture:** Keep the existing PM-only Feishu boundary and existing models, then add focused orchestration modules around them. The first round is deterministic and testable without real Feishu or Claude Code: a rule-based classifier creates a role plan, project state persists to JSON, TaskStore persists tasks in SQLite, a prompt builder creates role prompts, a review engine makes gate decisions, and an orchestrator advances S0/S1/S2 projects using an injected fake executor.

**Tech Stack:** Python 3, dataclasses, pathlib, json, sqlite3, pytest, existing `cccagents` modules.

---

## File Structure

Create or modify these files:

- Modify: `.gitignore` — prevent accidental `.env` commits.
- Modify: `src/cccagents/redaction.py` — expand secret redaction patterns.
- Modify: `src/cccagents/feishu_contracts.py` — fix `validate_card_content()` and add `resume_project` action.
- Modify: `src/cccagents/task_store.py` — add list/update/claim/complete/fail helpers.
- Create: `src/cccagents/complexity_classifier.py` — deterministic S0/S1/S2/S3 classifier and risk flags.
- Create: `src/cccagents/role_plan.py` — role-plan templates for S0/S1/S2/S3 and risk upgrades.
- Create: `src/cccagents/project_state.py` — JSON project-state persistence.
- Create: `src/cccagents/prompt_builder.py` — stable role prompt generation.
- Create: `src/cccagents/review_engine.py` — review result decisions and automatic acceptance logic.
- Create: `src/cccagents/orchestrator.py` — first-round fake-executor orchestration for S0/S1/S2.
- Create: `scripts/phase5/preflight_check.sh` — basic local/server prerequisite checks.
- Modify/Create tests listed in each task.

Keep modules small. Do not connect real Claude Code CLI or real Feishu in M0-M3; those are M4-M5.

---

### Task 1: Fix P0 security regressions

**Files:**
- Modify: `.gitignore`
- Modify: `src/cccagents/redaction.py`
- Modify: `src/cccagents/feishu_contracts.py`
- Test: `tests/test_redaction.py`
- Test: `tests/test_feishu_contracts.py`
- Create: `tests/test_gitignore_security.py`

- [ ] **Step 1: Write failing redaction tests**

Add these tests to `tests/test_redaction.py`:

```python
def test_redacts_feishu_secret_assignments():
    text = "FEISHU_APP_SECRET=real-secret FEISHU_VERIFICATION_TOKEN=real-token FEISHU_ENCRYPT_KEY=real-key"
    result = redact_text(text)

    assert result.text == "FEISHU_APP_SECRET=[REDACTED] FEISHU_VERIFICATION_TOKEN=[REDACTED] FEISHU_ENCRYPT_KEY=[REDACTED]"
    assert result.redacted is True
    assert "secret_assignment" in result.reasons
    assert "token_assignment" in result.reasons


def test_redacts_lowercase_token_and_secret_assignments():
    text = "token=abc123 secret=xyz789 auth=BearerValue"
    result = redact_text(text)

    assert result.text == "token=[REDACTED] secret=[REDACTED] auth=[REDACTED]"
    assert result.redacted is True
    assert "token_assignment" in result.reasons
    assert "secret_assignment" in result.reasons
    assert "auth_assignment" in result.reasons
```

- [ ] **Step 2: Write failing Feishu card tests**

Add these tests to `tests/test_feishu_contracts.py`:

```python
def test_clean_card_content_is_approved():
    decision = validate_card_content("测试完成，所有用例通过")

    assert decision.allowed is True
    assert decision.reason == "approved"


def test_resume_project_approval_action_is_supported():
    action = FeishuApprovalAction(
        project_id="demo",
        approval_id="approval-1",
        action="resume_project",
        feishu_user_id="user-1",
        feishu_message_id="event-1",
        timestamp=1_700_000_000,
        signature="sig-ok",
    )
    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids=set(),
        now=1_700_000_100,
        timestamp_window_seconds=300,
        expected_signature="sig-ok",
    )

    decision = validate_approval_action(action, context)

    assert decision.allowed is True
    assert decision.reason == "approved"
```

- [ ] **Step 3: Write failing gitignore test**

Create `tests/test_gitignore_security.py`:

```python
from pathlib import Path


def test_env_files_are_gitignored():
    content = Path(".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in content
    assert "*.env" in content
```

- [ ] **Step 4: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_redaction.py tests/test_feishu_contracts.py tests/test_gitignore_security.py
```

Expected: FAIL because new redaction patterns are missing, clean card content is rejected, `resume_project` is unsupported, and `.env` entries are absent.

- [ ] **Step 5: Update `.gitignore`**

Append these lines to `.gitignore`:

```gitignore
.env
*.env
```

- [ ] **Step 6: Replace redaction patterns**

Modify `src/cccagents/redaction.py` so `PATTERNS` becomes:

```python
PATTERNS = [
    ("bearer_token", re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+"), "Bearer [REDACTED]"),
    ("api_key_assignment", re.compile(r"(?i)([A-Z0-9_]*API[_-]?KEY)\s*=\s*\S+"), r"\1=[REDACTED]"),
    ("secret_assignment", re.compile(r"(?i)([A-Z0-9_]*SECRET)\s*=\s*\S+"), r"\1=[REDACTED]"),
    ("token_assignment", re.compile(r"(?i)([A-Z0-9_]*TOKEN)\s*=\s*\S+"), r"\1=[REDACTED]"),
    ("encrypt_key_assignment", re.compile(r"(?i)([A-Z0-9_]*ENCRYPT[_-]?KEY)\s*=\s*\S+"), r"\1=[REDACTED]"),
    ("password_assignment", re.compile(r"(?i)(password)\s*=\s*\S+"), r"\1=[REDACTED]"),
    ("auth_assignment", re.compile(r"(?i)(auth)\s*=\s*\S+"), r"\1=[REDACTED]"),
]
```

Keep `redact_text()` unchanged.

- [ ] **Step 7: Fix Feishu card validation and approval actions**

Modify `src/cccagents/feishu_contracts.py`:

```python
ALLOWED_APPROVAL_ACTIONS = {"approve", "reject", "comment", "pause_project", "resume_project"}
```

Replace `validate_card_content()` with:

```python
def validate_card_content(content: str) -> FeishuDecision:
    redacted = redact_text(content)
    if redacted.redacted:
        return FeishuDecision(False, "secret_like_content")
    return FeishuDecision(True, "approved")
```

- [ ] **Step 8: Run focused security tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_redaction.py tests/test_feishu_contracts.py tests/test_gitignore_security.py
```

Expected: PASS.

- [ ] **Step 9: Run all tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add .gitignore src/cccagents/redaction.py src/cccagents/feishu_contracts.py tests/test_redaction.py tests/test_feishu_contracts.py tests/test_gitignore_security.py
git commit -m "fix: harden Feishu card and secret handling"
```

---

### Task 2: Add complexity classifier

**Files:**
- Create: `src/cccagents/complexity_classifier.py`
- Test: `tests/test_complexity_classifier.py`

- [ ] **Step 1: Write failing classifier tests**

Create `tests/test_complexity_classifier.py`:

```python
from cccagents.complexity_classifier import classify_project_request


def test_classifies_typo_or_readme_change_as_s0():
    decision = classify_project_request("修复 README 里的一个 typo")

    assert decision.complexity == "S0"
    assert decision.required_roles == ["PM", "DEV"]
    assert decision.requires_user_approval is False
    assert "docs_only" in decision.risk_flags


def test_classifies_small_bug_as_s1_with_test():
    decision = classify_project_request("修复登录按钮点击后没有 loading 的局部 bug，并跑本地测试")

    assert decision.complexity == "S1"
    assert decision.required_roles == ["PM", "DEV", "TEST"]
    assert "local_test_required" in decision.risk_flags


def test_classifies_new_feature_as_s2():
    decision = classify_project_request("新增一个导出订单 CSV 的功能，包含接口和测试用例")

    assert decision.complexity == "S2"
    assert decision.required_roles == ["PM", "PDM", "ARCH", "DEV", "TEST"]
    assert "feature_change" in decision.risk_flags


def test_classifies_security_or_deploy_as_s3_with_sec_and_approval():
    decision = classify_project_request("修改认证权限并部署到生产，涉及 FEISHU_APP_SECRET 配置")

    assert decision.complexity == "S3"
    assert decision.required_roles == ["PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC"]
    assert decision.requires_user_approval is True
    assert "security_sensitive" in decision.risk_flags
    assert "external_side_effect" in decision.risk_flags


def test_explicit_research_request_adds_res():
    decision = classify_project_request("调研三种向量数据库方案并给出技术选型")

    assert decision.complexity == "S3"
    assert "RES" in decision.required_roles
    assert "research_required" in decision.risk_flags
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_complexity_classifier.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cccagents.complexity_classifier'`.

- [ ] **Step 3: Create classifier implementation**

Create `src/cccagents/complexity_classifier.py`:

```python
from dataclasses import dataclass


ROLE_PLANS = {
    "S0": ["PM", "DEV"],
    "S1": ["PM", "DEV", "TEST"],
    "S2": ["PM", "PDM", "ARCH", "DEV", "TEST"],
    "S3": ["PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC"],
}

S0_KEYWORDS = ("typo", "README", "readme", "文案", "注释", "拼写")
S1_KEYWORDS = ("bug", "局部", "简单", "函数", "本地测试", "loading")
S2_KEYWORDS = ("新增", "功能", "接口", "跨文件", "模块", "测试用例", "CSV")
S3_KEYWORDS = (
    "认证",
    "权限",
    "密钥",
    "secret",
    "SECRET",
    "token",
    "TOKEN",
    "deploy",
    "部署",
    "生产",
    "数据库",
    "migration",
    "删除",
    "force",
    "支付",
    "外部 API",
    "FEISHU_APP_SECRET",
)
RESEARCH_KEYWORDS = ("调研", "选型", "对比", "方案比较", "向量数据库")


@dataclass(frozen=True)
class ComplexityDecision:
    complexity: str
    required_roles: list[str]
    risk_flags: list[str]
    requires_user_approval: bool
    reason: str


def classify_project_request(text: str) -> ComplexityDecision:
    risk_flags: list[str] = []
    normalized = text.strip()

    if _contains(normalized, S3_KEYWORDS):
        risk_flags.extend(["security_sensitive", "external_side_effect"])
        if _contains(normalized, RESEARCH_KEYWORDS):
            risk_flags.append("research_required")
        return ComplexityDecision(
            complexity="S3",
            required_roles=ROLE_PLANS["S3"],
            risk_flags=_unique(risk_flags),
            requires_user_approval=True,
            reason="请求涉及安全、权限、部署、生产、数据库、删除或外部副作用，需要完整团队和人工审批",
        )

    if _contains(normalized, RESEARCH_KEYWORDS):
        return ComplexityDecision(
            complexity="S3",
            required_roles=ROLE_PLANS["S3"],
            risk_flags=["research_required"],
            requires_user_approval=False,
            reason="请求需要调研或技术选型，需要 RES 参与",
        )

    if _contains(normalized, S2_KEYWORDS):
        return ComplexityDecision(
            complexity="S2",
            required_roles=ROLE_PLANS["S2"],
            risk_flags=["feature_change", "test_case_required"],
            requires_user_approval=False,
            reason="请求是中型功能或跨文件变更，需要需求、方案、开发和测试协作",
        )

    if _contains(normalized, S1_KEYWORDS):
        return ComplexityDecision(
            complexity="S1",
            required_roles=ROLE_PLANS["S1"],
            risk_flags=["code_change", "local_test_required"],
            requires_user_approval=False,
            reason="请求是小型代码变更，需要开发和测试验证",
        )

    if _contains(normalized, S0_KEYWORDS):
        return ComplexityDecision(
            complexity="S0",
            required_roles=ROLE_PLANS["S0"],
            risk_flags=["docs_only"],
            requires_user_approval=False,
            reason="请求是极小低风险变更，只需要 PM 和 DEV",
        )

    return ComplexityDecision(
        complexity="S2",
        required_roles=ROLE_PLANS["S2"],
        risk_flags=["unclear_scope", "needs_requirement_clarification"],
        requires_user_approval=False,
        reason="请求范围不够明确，默认按中型功能处理并要求 PDM 澄清",
    )


def _contains(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _unique(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
```

- [ ] **Step 4: Run classifier tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_complexity_classifier.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/complexity_classifier.py tests/test_complexity_classifier.py
git commit -m "feat: classify project orchestration complexity"
```

---

### Task 3: Add role plan templates

**Files:**
- Create: `src/cccagents/role_plan.py`
- Test: `tests/test_role_plan.py`

- [ ] **Step 1: Write failing role-plan tests**

Create `tests/test_role_plan.py`:

```python
from cccagents.complexity_classifier import ComplexityDecision
from cccagents.role_plan import build_role_plan


def test_s0_role_plan_has_dev_only_flow():
    decision = ComplexityDecision("S0", ["PM", "DEV"], ["docs_only"], False, "small")

    plan = build_role_plan(decision)

    assert [phase.name for phase in plan.phases] == ["DEV_IMPLEMENTATION", "DEV_SELF_TEST", "PM_AUTO_ACCEPTANCE"]
    assert plan.phases[0].tasks[0].role == "DEV"
    assert plan.requires_user_approval is False


def test_s1_role_plan_adds_test_validation():
    decision = ComplexityDecision("S1", ["PM", "DEV", "TEST"], ["code_change"], False, "bug")

    plan = build_role_plan(decision)

    assert [phase.name for phase in plan.phases] == ["DEV_IMPLEMENTATION", "DEV_SELF_TEST", "TEST_VALIDATION", "PM_AUTO_ACCEPTANCE"]
    assert plan.phases[2].tasks[0].role == "TEST"


def test_s2_role_plan_has_parallel_design_and_testcase_with_isolation():
    decision = ComplexityDecision("S2", ["PM", "PDM", "ARCH", "DEV", "TEST"], ["feature_change"], False, "feature")

    plan = build_role_plan(decision)

    parallel = plan.phase_by_name("PARALLEL_DESIGN_AND_TESTCASE")
    assert parallel.parallel is True
    assert parallel.isolation is True
    assert [task.role for task in parallel.tasks] == ["ARCH", "TEST"]
    assert parallel.tasks[0].template == "draft_tech_design"
    assert parallel.tasks[1].template == "draft_test_cases"


def test_security_risk_requires_user_approval_even_for_lower_complexity():
    decision = ComplexityDecision("S1", ["PM", "DEV", "TEST", "SEC"], ["security_sensitive"], True, "secret")

    plan = build_role_plan(decision)

    assert plan.requires_user_approval is True
    assert "SECURITY_REVIEW" in [phase.name for phase in plan.phases]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_role_plan.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cccagents.role_plan'`.

- [ ] **Step 3: Create role plan implementation**

Create `src/cccagents/role_plan.py`:

```python
from dataclasses import dataclass

from cccagents.complexity_classifier import ComplexityDecision


@dataclass(frozen=True)
class RoleTask:
    role: str
    template: str
    expected_artifacts: list[str]


@dataclass(frozen=True)
class PhasePlan:
    name: str
    parallel: bool
    isolation: bool
    tasks: list[RoleTask]


@dataclass(frozen=True)
class RolePlan:
    complexity: str
    required_roles: list[str]
    risk_flags: list[str]
    requires_user_approval: bool
    phases: list[PhasePlan]

    def phase_by_name(self, name: str) -> PhasePlan:
        for phase in self.phases:
            if phase.name == name:
                return phase
        raise KeyError(name)


def build_role_plan(decision: ComplexityDecision) -> RolePlan:
    phases = _base_phases(decision.complexity)
    if "security_sensitive" in decision.risk_flags and not any(phase.name == "SECURITY_REVIEW" for phase in phases):
        phases.append(
            PhasePlan(
                name="SECURITY_REVIEW",
                parallel=False,
                isolation=False,
                tasks=[RoleTask("SEC", "security_review", ["06-security/security-review.md"])],
            )
        )
    return RolePlan(
        complexity=decision.complexity,
        required_roles=decision.required_roles,
        risk_flags=decision.risk_flags,
        requires_user_approval=decision.requires_user_approval,
        phases=phases,
    )


def _base_phases(complexity: str) -> list[PhasePlan]:
    if complexity == "S0":
        return [
            PhasePlan("DEV_IMPLEMENTATION", False, False, [RoleTask("DEV", "implement_small_change", ["05-development/dev-summary.md"])]),
            PhasePlan("DEV_SELF_TEST", False, False, [RoleTask("DEV", "self_test", ["05-development/self-test.md"])]),
            PhasePlan("PM_AUTO_ACCEPTANCE", False, False, [RoleTask("PM", "auto_acceptance", ["07-acceptance/acceptance-report.md"])]),
        ]
    if complexity == "S1":
        return [
            PhasePlan("DEV_IMPLEMENTATION", False, False, [RoleTask("DEV", "implement_code_change", ["05-development/dev-summary.md"])]),
            PhasePlan("DEV_SELF_TEST", False, False, [RoleTask("DEV", "self_test", ["05-development/self-test.md"])]),
            PhasePlan("TEST_VALIDATION", False, False, [RoleTask("TEST", "validate_change", ["04-test-cases/test-result.md"])]),
            PhasePlan("PM_AUTO_ACCEPTANCE", False, False, [RoleTask("PM", "auto_acceptance", ["07-acceptance/acceptance-report.md"])]),
        ]
    if complexity == "S2":
        return [
            PhasePlan("REQUIREMENT_DRAFTING", False, False, [RoleTask("PDM", "draft_prd", ["02-requirements/prd.md"])]),
            PhasePlan("REQUIREMENT_REVIEW", False, False, [RoleTask("PM", "review_requirement", ["02-requirements/prd-review.md"])]),
            PhasePlan(
                "PARALLEL_DESIGN_AND_TESTCASE",
                True,
                True,
                [
                    RoleTask("ARCH", "draft_tech_design", ["03-architecture/tech-design.md"]),
                    RoleTask("TEST", "draft_test_cases", ["04-test-cases/test-cases.md", "04-test-cases/test-cases.xlsx"]),
                ],
            ),
            PhasePlan("DESIGN_AND_TESTCASE_REVIEW", False, False, [RoleTask("PM", "review_design_and_testcase", ["03-architecture/tech-design-review.md"])]),
            PhasePlan("DEVELOPMENT", False, False, [RoleTask("DEV", "implement_feature", ["05-development/dev-summary.md"])]),
            PhasePlan("DEV_SELF_TEST", False, False, [RoleTask("DEV", "self_test", ["05-development/self-test.md"])]),
            PhasePlan("TEST_VALIDATION", False, False, [RoleTask("TEST", "validate_feature", ["04-test-cases/test-result.md"])]),
            PhasePlan("PRODUCT_ACCEPTANCE", False, False, [RoleTask("PDM", "product_acceptance", ["07-acceptance/acceptance-report.md"])]),
        ]
    if complexity == "S3":
        return [
            PhasePlan("REQUIREMENT_DRAFTING", False, False, [RoleTask("PDM", "draft_prd", ["02-requirements/prd.md"])]),
            PhasePlan("RESEARCH", False, False, [RoleTask("RES", "research_options", ["01-input/research-report.md"])]),
            PhasePlan(
                "PARALLEL_DESIGN_TEST_SECURITY",
                True,
                True,
                [
                    RoleTask("ARCH", "draft_tech_design", ["03-architecture/tech-design.md"]),
                    RoleTask("TEST", "draft_test_cases", ["04-test-cases/test-cases.md", "04-test-cases/test-cases.xlsx"]),
                    RoleTask("SEC", "security_plan", ["06-security/security-review.md"]),
                ],
            ),
            PhasePlan("DEVELOPMENT", False, False, [RoleTask("DEV", "implement_feature", ["05-development/dev-summary.md"])]),
            PhasePlan("TEST_VALIDATION", False, False, [RoleTask("TEST", "validate_feature", ["04-test-cases/test-result.md"])]),
            PhasePlan("SECURITY_REVIEW", False, False, [RoleTask("SEC", "security_review", ["06-security/security-review.md"])]),
            PhasePlan("PRODUCT_ACCEPTANCE", False, False, [RoleTask("PDM", "product_acceptance", ["07-acceptance/acceptance-report.md"])]),
        ]
    raise ValueError(f"Unknown complexity: {complexity}")
```

- [ ] **Step 4: Run role-plan tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_role_plan.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/role_plan.py tests/test_role_plan.py
git commit -m "feat: build dynamic role plans"
```

---

### Task 4: Add project state persistence

**Files:**
- Create: `src/cccagents/project_state.py`
- Test: `tests/test_project_state.py`

- [ ] **Step 1: Write failing project-state tests**

Create `tests/test_project_state.py`:

```python
from cccagents.project_state import ProjectState, load_project_state, save_project_state


def test_save_and_load_project_state(tmp_path):
    state = ProjectState(
        project_id="demo",
        source="feishu",
        status="running",
        complexity="S2",
        current_phase="DEVELOPMENT",
        required_roles=["PM", "PDM", "ARCH", "DEV", "TEST"],
        risk_flags=["feature_change"],
        approval_policy="auto_if_l0_l1_and_all_reviews_pass",
        retry_count_by_phase={"TEST_VALIDATION": 1},
        created_at="2026-06-13T10:00:00Z",
        updated_at="2026-06-13T11:00:00Z",
        last_pm_notification_at="2026-06-13T10:30:00Z",
    )

    save_project_state(tmp_path, state)
    loaded = load_project_state(tmp_path)

    assert loaded == state


def test_load_missing_project_state_raises_key_error(tmp_path):
    try:
        load_project_state(tmp_path)
    except KeyError as exc:
        assert str(exc) == "'project-state.json'"
    else:
        raise AssertionError("expected KeyError")
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_project_state.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cccagents.project_state'`.

- [ ] **Step 3: Create project-state implementation**

Create `src/cccagents/project_state.py`:

```python
from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class ProjectState:
    project_id: str
    source: str
    status: str
    complexity: str
    current_phase: str
    required_roles: list[str]
    risk_flags: list[str]
    approval_policy: str
    retry_count_by_phase: dict[str, int]
    created_at: str
    updated_at: str
    last_pm_notification_at: str | None = None


def project_state_path(project_dir: Path) -> Path:
    return project_dir / "project-state.json"


def save_project_state(project_dir: Path, state: ProjectState) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    project_state_path(project_dir).write_text(
        json.dumps(asdict(state), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_project_state(project_dir: Path) -> ProjectState:
    path = project_state_path(project_dir)
    if not path.exists():
        raise KeyError("project-state.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProjectState(**data)
```

- [ ] **Step 4: Run project-state tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_project_state.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/project_state.py tests/test_project_state.py
git commit -m "feat: persist orchestration project state"
```

---

### Task 5: Extend TaskStore for orchestration

**Files:**
- Modify: `src/cccagents/task_store.py`
- Test: `tests/test_task_store.py`

- [ ] **Step 1: Add failing TaskStore tests**

Append to `tests/test_task_store.py`:

```python
from dataclasses import replace

from cccagents.phase2_models import Task, TaskStatus
from cccagents.task_store import TaskStore


def test_task_store_lists_and_updates_tasks(tmp_path):
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    first = Task(
        id="task-1",
        project_id="demo",
        phase="DEV_IMPLEMENTATION",
        flow="main",
        assignee_role="DEV",
        title="Implement",
        description="Implement change",
        created_at="2026-06-13T10:00:00Z",
    )
    second = replace(first, id="task-2", phase="TEST_VALIDATION", assignee_role="TEST")
    store.save_task(first)
    store.save_task(second)

    store.update_status("task-1", TaskStatus.RUNNING)
    running = store.list_tasks("demo", TaskStatus.RUNNING)
    pending = store.list_tasks("demo", TaskStatus.PENDING)

    assert [task.id for task in running] == ["task-1"]
    assert [task.id for task in pending] == ["task-2"]


def test_task_store_claim_complete_and_fail(tmp_path):
    store = TaskStore(tmp_path / "tasks.db")
    store.initialize()
    task = Task(
        id="task-1",
        project_id="demo",
        phase="DEV_IMPLEMENTATION",
        flow="main",
        assignee_role="DEV",
        title="Implement",
        description="Implement change",
        created_at="2026-06-13T10:00:00Z",
    )
    store.save_task(task)

    claimed = store.claim_task("task-1", started_at="2026-06-13T10:01:00Z")
    store.complete_task("task-1", ["artifact-1"], completed_at="2026-06-13T10:02:00Z")
    completed = store.get_task("task-1")

    assert claimed.status == TaskStatus.RUNNING
    assert completed.status == TaskStatus.COMPLETED
    assert completed.output_artifact_ids == ["artifact-1"]
    assert completed.completed_at == "2026-06-13T10:02:00Z"

    failed_task = replace(task, id="task-2")
    store.save_task(failed_task)
    store.fail_task("task-2", ["issue-1"], updated_at="2026-06-13T10:03:00Z")
    failed = store.get_task("task-2")

    assert failed.status == TaskStatus.FAILED
    assert failed.issue_ids == ["issue-1"]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_task_store.py
```

Expected: FAIL because `list_tasks`, `update_status`, `claim_task`, `complete_task`, and `fail_task` do not exist.

- [ ] **Step 3: Add TaskStore methods**

Append these methods inside `TaskStore` in `src/cccagents/task_store.py`:

```python
    def list_tasks(self, project_id: str, status: TaskStatus | None = None) -> list[Task]:
        query = "SELECT * FROM tasks WHERE project_id = ?"
        params: tuple[str, ...]
        if status is None:
            params = (project_id,)
        else:
            query += " AND status = ?"
            params = (project_id, status.value)
        query += " ORDER BY created_at, id"
        with sqlite3.connect(self.db_path) as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._task_from_row(row) for row in rows]

    def update_status(self, task_id: str, status: TaskStatus, updated_at: str | None = None) -> Task:
        task = self.get_task(task_id)
        updated = Task(
            **{
                **task.__dict__,
                "status": status,
                "updated_at": updated_at or task.updated_at,
            }
        )
        self.save_task(updated)
        return updated

    def claim_task(self, task_id: str, started_at: str) -> Task:
        task = self.get_task(task_id)
        updated = Task(
            **{
                **task.__dict__,
                "status": TaskStatus.RUNNING,
                "started_at": started_at,
                "updated_at": started_at,
            }
        )
        self.save_task(updated)
        return updated

    def complete_task(self, task_id: str, output_artifact_ids: list[str], completed_at: str) -> Task:
        task = self.get_task(task_id)
        updated = Task(
            **{
                **task.__dict__,
                "status": TaskStatus.COMPLETED,
                "output_artifact_ids": output_artifact_ids,
                "completed_at": completed_at,
                "updated_at": completed_at,
            }
        )
        self.save_task(updated)
        return updated

    def fail_task(self, task_id: str, issue_ids: list[str], updated_at: str) -> Task:
        task = self.get_task(task_id)
        updated = Task(
            **{
                **task.__dict__,
                "status": TaskStatus.FAILED,
                "issue_ids": issue_ids,
                "updated_at": updated_at,
            }
        )
        self.save_task(updated)
        return updated

    def _task_from_row(self, row: tuple) -> Task:
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

Then simplify `get_task()` to use `_task_from_row()`:

```python
    def get_task(self, task_id: str) -> Task:
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        return self._task_from_row(row)
```

- [ ] **Step 4: Run TaskStore tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_task_store.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/task_store.py tests/test_task_store.py
git commit -m "feat: extend task store for orchestration"
```

---

### Task 6: Add prompt builder

**Files:**
- Create: `src/cccagents/prompt_builder.py`
- Test: `tests/test_prompt_builder.py`

- [ ] **Step 1: Write failing prompt builder tests**

Create `tests/test_prompt_builder.py`:

```python
from pathlib import Path

from cccagents.phase2_models import Task
from cccagents.prompt_builder import PromptContext, build_role_prompt


def test_dev_prompt_contains_role_project_paths_and_forbidden_rules():
    task = Task(
        id="task-dev-1",
        project_id="demo",
        phase="DEV_IMPLEMENTATION",
        flow="main",
        assignee_role="DEV",
        title="Implement change",
        description="Add README line",
        created_at="2026-06-13T10:00:00Z",
    )
    context = PromptContext(
        workspace_path=Path("/home/ubuntu/cccagents/workspaces/demo/repo"),
        project_dir=Path("/home/ubuntu/cccagents/projects/demo"),
        input_artifact_paths=[Path("02-requirements/prd.md")],
        expected_output_paths=[Path("05-development/dev-summary.md")],
        allowed_tools=["Read", "Write"],
        forbidden_operations=["Do not contact Feishu user", "Do not perform L2/L3 operations"],
    )

    prompt = build_role_prompt(task, context)

    assert "You are DEV" in prompt
    assert "Read hermes/roles/dev.md" in prompt
    assert "project_id: demo" in prompt
    assert "task_id: task-dev-1" in prompt
    assert "/home/ubuntu/cccagents/workspaces/demo/repo" in prompt
    assert "05-development/dev-summary.md" in prompt
    assert "Do not contact Feishu user" in prompt
    assert "Return a completion summary" in prompt


def test_parallel_isolation_prompt_excludes_other_branch_artifacts():
    task = Task(
        id="task-test-1",
        project_id="demo",
        phase="TEST_CASE_DRAFTING",
        flow="testcase",
        assignee_role="TEST",
        title="Draft test cases",
        description="Write test cases from PRD",
        created_at="2026-06-13T10:00:00Z",
    )
    context = PromptContext(
        workspace_path=Path("/home/ubuntu/cccagents/workspaces/demo/repo"),
        project_dir=Path("/home/ubuntu/cccagents/projects/demo"),
        input_artifact_paths=[Path("02-requirements/prd.md")],
        expected_output_paths=[Path("04-test-cases/test-cases.md"), Path("04-test-cases/test-cases.xlsx")],
        allowed_tools=["Read", "Write"],
        forbidden_operations=["Do not read 03-architecture during testcase drafting"],
    )

    prompt = build_role_prompt(task, context)

    assert "02-requirements/prd.md" in prompt
    assert "04-test-cases/test-cases.xlsx" in prompt
    assert "Do not read 03-architecture during testcase drafting" in prompt
    assert "03-architecture/tech-design.md" not in prompt
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_prompt_builder.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cccagents.prompt_builder'`.

- [ ] **Step 3: Create prompt builder implementation**

Create `src/cccagents/prompt_builder.py`:

```python
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
```

- [ ] **Step 4: Run prompt-builder tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_prompt_builder.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/prompt_builder.py tests/test_prompt_builder.py
git commit -m "feat: build deterministic role prompts"
```

---

### Task 7: Add review engine

**Files:**
- Create: `src/cccagents/review_engine.py`
- Test: `tests/test_review_engine.py`

- [ ] **Step 1: Write failing review engine tests**

Create `tests/test_review_engine.py`:

```python
from cccagents.review_engine import ReviewInput, automatic_acceptance_allowed, evaluate_review


def test_quality_review_passes_when_exit_code_zero_and_artifacts_exist():
    result = evaluate_review(
        ReviewInput(
            review_type="quality",
            phase="TEST_VALIDATION",
            exit_code=0,
            expected_artifacts_present=True,
            secret_scan_clean=True,
            permission_level="L1",
            issues=[],
        )
    )

    assert result.passed is True
    assert result.next_phase == "PRODUCT_ACCEPTANCE"
    assert result.next_handler_role == "PDM"


def test_quality_review_fails_on_exit_code():
    result = evaluate_review(
        ReviewInput(
            review_type="quality",
            phase="TEST_VALIDATION",
            exit_code=1,
            expected_artifacts_present=True,
            secret_scan_clean=True,
            permission_level="L1",
            issues=["pytest failed"],
        )
    )

    assert result.passed is False
    assert result.next_phase == "FIXING"
    assert result.next_handler_role == "DEV"
    assert "pytest failed" in result.issues


def test_security_review_fails_on_secret_scan():
    result = evaluate_review(
        ReviewInput(
            review_type="security",
            phase="SECURITY_REVIEW",
            exit_code=0,
            expected_artifacts_present=True,
            secret_scan_clean=False,
            permission_level="L1",
            issues=[],
        )
    )

    assert result.passed is False
    assert result.next_handler_role == "DEV"
    assert "secret_scan_failed" in result.issues


def test_automatic_acceptance_allowed_for_low_risk_s2():
    assert automatic_acceptance_allowed(
        complexity="S2",
        permission_level="L1",
        risk_flags=["feature_change"],
        reviews_passed={"requirement", "tech_design", "test_case", "self_test", "quality", "acceptance"},
    ) is True


def test_automatic_acceptance_denied_for_l2_or_security_risk():
    assert automatic_acceptance_allowed(
        complexity="S2",
        permission_level="L2",
        risk_flags=["feature_change"],
        reviews_passed={"requirement", "tech_design", "test_case", "self_test", "quality", "acceptance"},
    ) is False
    assert automatic_acceptance_allowed(
        complexity="S1",
        permission_level="L1",
        risk_flags=["security_sensitive"],
        reviews_passed={"self_test", "quality"},
    ) is False
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_review_engine.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cccagents.review_engine'`.

- [ ] **Step 3: Create review engine implementation**

Create `src/cccagents/review_engine.py`:

```python
from dataclasses import dataclass

from cccagents.review_gate import review_decision


@dataclass(frozen=True)
class ReviewInput:
    review_type: str
    phase: str
    exit_code: int
    expected_artifacts_present: bool
    secret_scan_clean: bool
    permission_level: str
    issues: list[str]


@dataclass(frozen=True)
class ReviewResult:
    review_type: str
    phase: str
    passed: bool
    issues: list[str]
    next_phase: str
    next_handler_role: str | None
    reason: str


REQUIRED_REVIEWS = {
    "S0": {"self_test"},
    "S1": {"self_test", "quality"},
    "S2": {"requirement", "tech_design", "test_case", "self_test", "quality", "acceptance"},
    "S3": {"requirement", "tech_design", "test_case", "self_test", "quality", "security", "acceptance"},
}


def evaluate_review(review_input: ReviewInput) -> ReviewResult:
    issues = list(review_input.issues)
    if review_input.exit_code != 0:
        issues.append("exit_code_failed")
    if not review_input.expected_artifacts_present:
        issues.append("expected_artifacts_missing")
    if not review_input.secret_scan_clean:
        issues.append("secret_scan_failed")

    passed = len(issues) == 0
    gate_type = _gate_type(review_input.review_type)
    decision = review_decision(gate_type, passed)
    return ReviewResult(
        review_type=review_input.review_type,
        phase=review_input.phase,
        passed=passed,
        issues=issues,
        next_phase=decision.next_phase,
        next_handler_role=decision.next_handler_role,
        reason=decision.reason,
    )


def automatic_acceptance_allowed(
    complexity: str,
    permission_level: str,
    risk_flags: list[str],
    reviews_passed: set[str],
) -> bool:
    if permission_level in {"L2", "L3"}:
        return False
    if any(flag in risk_flags for flag in {"security_sensitive", "external_side_effect"}):
        return False
    required = REQUIRED_REVIEWS[complexity]
    return required.issubset(reviews_passed)


def _gate_type(review_type: str) -> str:
    if review_type == "quality":
        return "quality_security"
    if review_type == "security":
        return "quality_security"
    return review_type
```

- [ ] **Step 4: Run review-engine tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_review_engine.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/review_engine.py tests/test_review_engine.py
git commit -m "feat: evaluate orchestration review gates"
```

---

### Task 8: Add fake-executor orchestrator for S0 and S1

**Files:**
- Create: `src/cccagents/orchestrator.py`
- Test: `tests/test_orchestrator_s0_s1.py`

- [ ] **Step 1: Write failing S0/S1 orchestrator tests**

Create `tests/test_orchestrator_s0_s1.py`:

```python
from cccagents.orchestrator import FakeExecutor, OrchestrationRequest, orchestrate_request
from cccagents.project_state import load_project_state


def test_orchestrator_completes_s0_with_dev_only(tmp_path):
    result = orchestrate_request(
        OrchestrationRequest(
            project_id="demo-s0",
            text="修复 README 里的 typo",
            project_root=tmp_path,
            now="2026-06-13T10:00:00Z",
        ),
        executor=FakeExecutor(),
    )

    state = load_project_state(tmp_path / "demo-s0")

    assert result.status == "done"
    assert state.status == "done"
    assert state.complexity == "S0"
    assert result.executed_roles == ["DEV", "DEV", "PM"]
    assert (tmp_path / "demo-s0" / "05-development" / "dev-summary.md").exists()
    assert (tmp_path / "demo-s0" / "07-acceptance" / "acceptance-report.md").exists()


def test_orchestrator_completes_s1_with_dev_and_test(tmp_path):
    result = orchestrate_request(
        OrchestrationRequest(
            project_id="demo-s1",
            text="修复登录按钮 loading 的局部 bug，并跑本地测试",
            project_root=tmp_path,
            now="2026-06-13T10:00:00Z",
        ),
        executor=FakeExecutor(),
    )

    state = load_project_state(tmp_path / "demo-s1")

    assert result.status == "done"
    assert state.status == "done"
    assert state.complexity == "S1"
    assert result.executed_roles == ["DEV", "DEV", "TEST", "PM"]
    assert (tmp_path / "demo-s1" / "04-test-cases" / "test-result.md").exists()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_orchestrator_s0_s1.py
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cccagents.orchestrator'`.

- [ ] **Step 3: Create orchestrator implementation for S0/S1**

Create `src/cccagents/orchestrator.py` with this initial implementation:

```python
from dataclasses import dataclass
from pathlib import Path

from cccagents.complexity_classifier import classify_project_request
from cccagents.project_state import ProjectState, save_project_state
from cccagents.role_plan import RolePlan, RoleTask, build_role_plan


@dataclass(frozen=True)
class OrchestrationRequest:
    project_id: str
    text: str
    project_root: Path
    now: str


@dataclass(frozen=True)
class ExecutionResult:
    role: str
    template: str
    artifact_paths: list[Path]
    passed: bool
    issues: list[str]


@dataclass(frozen=True)
class OrchestrationResult:
    project_id: str
    status: str
    complexity: str
    executed_roles: list[str]
    issues: list[str]


class FakeExecutor:
    def run(self, project_dir: Path, task: RoleTask) -> ExecutionResult:
        artifact_paths: list[Path] = []
        for relative in task.expected_artifacts:
            path = project_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {task.role} {task.template}\n\nGenerated by fake executor.\n", encoding="utf-8")
            artifact_paths.append(path)
        return ExecutionResult(
            role=task.role,
            template=task.template,
            artifact_paths=artifact_paths,
            passed=True,
            issues=[],
        )


def orchestrate_request(request: OrchestrationRequest, executor: FakeExecutor) -> OrchestrationResult:
    decision = classify_project_request(request.text)
    plan = build_role_plan(decision)
    project_dir = request.project_root / request.project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    _save_initial_state(request, decision.complexity, decision.required_roles, decision.risk_flags, "running")

    executed_roles: list[str] = []
    issues: list[str] = []
    for phase in plan.phases:
        for task in phase.tasks:
            result = executor.run(project_dir, task)
            executed_roles.append(result.role)
            issues.extend(result.issues)
            if not result.passed:
                _save_initial_state(request, decision.complexity, decision.required_roles, decision.risk_flags, "blocked")
                return OrchestrationResult(request.project_id, "blocked", decision.complexity, executed_roles, issues)

    _save_initial_state(request, decision.complexity, decision.required_roles, decision.risk_flags, "done")
    return OrchestrationResult(request.project_id, "done", decision.complexity, executed_roles, issues)


def _save_initial_state(
    request: OrchestrationRequest,
    complexity: str,
    required_roles: list[str],
    risk_flags: list[str],
    status: str,
) -> None:
    save_project_state(
        request.project_root / request.project_id,
        ProjectState(
            project_id=request.project_id,
            source="feishu",
            status=status,
            complexity=complexity,
            current_phase="DONE" if status == "done" else "RUNNING",
            required_roles=required_roles,
            risk_flags=risk_flags,
            approval_policy="auto_if_l0_l1_and_all_reviews_pass",
            retry_count_by_phase={},
            created_at=request.now,
            updated_at=request.now,
            last_pm_notification_at=None,
        ),
    )
```

- [ ] **Step 4: Run S0/S1 orchestrator tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_orchestrator_s0_s1.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/cccagents/orchestrator.py tests/test_orchestrator_s0_s1.py
git commit -m "feat: orchestrate S0 and S1 fake flows"
```

---

### Task 9: Extend orchestrator for S2 parallel isolation and role-plan persistence

**Files:**
- Modify: `src/cccagents/orchestrator.py`
- Test: `tests/test_orchestrator_s2.py`

- [ ] **Step 1: Write failing S2 tests**

Create `tests/test_orchestrator_s2.py`:

```python
import json

from cccagents.orchestrator import FakeExecutor, OrchestrationRequest, orchestrate_request
from cccagents.project_state import load_project_state


def test_orchestrator_completes_s2_with_parallel_design_and_testcase(tmp_path):
    result = orchestrate_request(
        OrchestrationRequest(
            project_id="demo-s2",
            text="新增一个导出订单 CSV 的功能，包含接口和测试用例",
            project_root=tmp_path,
            now="2026-06-13T10:00:00Z",
        ),
        executor=FakeExecutor(),
    )

    project_dir = tmp_path / "demo-s2"
    state = load_project_state(project_dir)
    role_plan = json.loads((project_dir / "role-plan.json").read_text(encoding="utf-8"))

    assert result.status == "done"
    assert state.complexity == "S2"
    assert result.executed_roles == ["PDM", "PM", "ARCH", "TEST", "PM", "DEV", "DEV", "TEST", "PDM"]
    assert (project_dir / "02-requirements" / "prd.md").exists()
    assert (project_dir / "03-architecture" / "tech-design.md").exists()
    assert (project_dir / "04-test-cases" / "test-cases.md").exists()
    assert (project_dir / "04-test-cases" / "test-cases.xlsx").exists()
    assert role_plan["phases"][2]["parallel"] is True
    assert role_plan["phases"][2]["isolation"] is True


def test_s2_parallel_isolation_evidence_is_written(tmp_path):
    orchestrate_request(
        OrchestrationRequest(
            project_id="demo-s2",
            text="新增一个导出订单 CSV 的功能，包含接口和测试用例",
            project_root=tmp_path,
            now="2026-06-13T10:00:00Z",
        ),
        executor=FakeExecutor(),
    )

    isolation_log = tmp_path / "demo-s2" / "08-logs" / "parallel-isolation.jsonl"

    assert isolation_log.exists()
    content = isolation_log.read_text(encoding="utf-8")
    assert "ARCH" in content
    assert "TEST" in content
    assert "no_cross_branch_artifacts" in content
```

- [ ] **Step 2: Run S2 tests and verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_orchestrator_s2.py
```

Expected: FAIL because `role-plan.json` and parallel isolation evidence are not written.

- [ ] **Step 3: Add role-plan persistence and isolation logging**

Modify `src/cccagents/orchestrator.py` imports:

```python
from dataclasses import asdict, dataclass
import json
```

Add these helper functions:

```python
def _save_role_plan(project_dir: Path, plan: RolePlan) -> None:
    (project_dir / "role-plan.json").write_text(
        json.dumps(asdict(plan), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _append_parallel_isolation(project_dir: Path, phase_name: str, role: str) -> None:
    log_dir = project_dir / "08-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "phase": phase_name,
        "role": role,
        "rule": "no_cross_branch_artifacts",
    }
    with (log_dir / "parallel-isolation.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
```

Inside `orchestrate_request()` after `project_dir.mkdir(...)`, add:

```python
    _save_role_plan(project_dir, plan)
```

Inside the phase loop before executor run, add:

```python
            if phase.parallel and phase.isolation:
                _append_parallel_isolation(project_dir, phase.name, task.role)
```

- [ ] **Step 4: Run S2 tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_orchestrator_s2.py
```

Expected: PASS.

- [ ] **Step 5: Run all orchestrator tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_orchestrator_s0_s1.py tests/test_orchestrator_s2.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/cccagents/orchestrator.py tests/test_orchestrator_s2.py
git commit -m "feat: orchestrate S2 fake flow with isolation evidence"
```

---

### Task 10: Add phase5 preflight script

**Files:**
- Create: `scripts/phase5/preflight_check.sh`
- Test: `tests/test_phase5_scripts.py`

- [ ] **Step 1: Write failing script tests**

Create `tests/test_phase5_scripts.py`:

```python
from pathlib import Path


def test_phase5_preflight_script_exists_and_checks_core_dependencies():
    script = Path("scripts/phase5/preflight_check.sh")
    content = script.read_text(encoding="utf-8")

    assert "python3 --version" in content
    assert "node --version" in content
    assert "npm --version" in content
    assert "claude --version" in content
    assert "hermes --help" in content
    assert "cccai.store" in content
    assert "GATEWAY_ALLOW_ALL_USERS=false" in content
    assert "gpt-5.5" in content
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_phase5_scripts.py
```

Expected: FAIL because the script does not exist.

- [ ] **Step 3: Create preflight script**

Create `scripts/phase5/preflight_check.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

HERMES_ENV="${HERMES_ENV:-/home/ubuntu/.hermes/.env}"
HERMES_CONFIG="${HERMES_CONFIG:-/home/ubuntu/.hermes/config.yaml}"

python3 --version
node --version
npm --version
claude --version
hermes --help >/dev/null

python3 - <<'PY'
import socket
socket.create_connection(("cccai.store", 80), timeout=5).close()
print("cccai.store reachable")
PY

test -f "$HERMES_ENV"
test -f "$HERMES_CONFIG"
test "$(stat -c '%a' "$HERMES_ENV" 2>/dev/null || stat -f '%Lp' "$HERMES_ENV")" = "600"

grep -q "gpt-5.5" "$HERMES_CONFIG"
grep -q "cccai.store/v1" "$HERMES_CONFIG"
grep -q "terminal" "$HERMES_CONFIG"
grep -q "GATEWAY_ALLOW_ALL_USERS=false" "$HERMES_ENV"

printf 'phase5 preflight PASS\n'
```

- [ ] **Step 4: Make script executable**

Run:

```bash
chmod +x scripts/phase5/preflight_check.sh
```

Expected: no output.

- [ ] **Step 5: Run script test**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests/test_phase5_scripts.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/phase5/preflight_check.sh tests/test_phase5_scripts.py
git commit -m "chore: add phase5 preflight check script"
```

---

### Task 11: Final verification for M0-M3 plan scope

**Files:**
- No new files.

- [ ] **Step 1: Run full test suite**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q tests
```

Expected: PASS.

- [ ] **Step 2: Verify old active model string is absent from active paths**

Run:

```bash
grep -R "qwen3.6-plus" docs/final-new-server-deployment-guide.md docs/project-overview-and-operations-guide.md docs/new-project-startup-guide.md docs/phase1/openai-compat-gate.md docs/phase2/hermes-openai-compat-gate.md tests src hermes scripts || true
```

Expected: no output, except historical docs are intentionally not included in this command.

- [ ] **Step 3: Run secret scan**

Run:

```bash
grep -R "FEISHU_APP_SECRET=.*[A-Za-z0-9]\|FEISHU_VERIFICATION_TOKEN=.*[A-Za-z0-9]\|FEISHU_ENCRYPT_KEY=.*[A-Za-z0-9]\|sk-\|ANTHROPIC_API_KEY=.*[A-Za-z0-9]" docs src tests hermes scripts || true
```

Expected: only redacted examples or test strings. No real API keys, Feishu secrets, Authorization tokens, Feishu user IDs, chat IDs, or message IDs.

- [ ] **Step 4: Check git status**

Run:

```bash
git status --short
```

Expected: no uncommitted source changes after all prior task commits.

- [ ] **Step 5: Summarize M0-M3 completion**

Write a short final note to the user with:

```text
M0 security hardening: complete
M1 complexity and role planning: complete
M2 S0/S1 fake orchestration: complete
M3 S2 fake orchestration and isolation evidence: complete
Verification: pytest and scans passed
Next scope: M4 real Claude Code CLI integration and M5 Feishu approval/recovery smoke
```

No commit is needed for this step.

---

## Self-Review Notes

Spec coverage:

- M0 security fixes are covered by Task 1 and Task 10.
- M1 complexity classification and dynamic role planning are covered by Task 2 and Task 3.
- M2 project state, TaskStore, prompt builder, and S0/S1 orchestration are covered by Task 4, Task 5, Task 6, and Task 8.
- M3 S2 parallel design/testcase flow, isolation evidence, and review engine are covered by Task 7 and Task 9.
- First-round fake executor strategy is covered by Task 8 and Task 9.
- Full verification is covered by Task 11.

Deliberate exclusions from this plan:

- Real Claude Code CLI execution is M4.
- Real Feishu approval handling is M5.
- Distributed worker queues and production deployment execution are out of first-round scope.
