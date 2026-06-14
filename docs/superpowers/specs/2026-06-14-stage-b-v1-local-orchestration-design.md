# cccagents Stage B v1 本地编排内核设计

Date: 2026-06-14

## 目标

实现 Stage B 第一版：**S0/S1 本地自动编排内核**。本阶段让现有 pending tests 变绿，建立可测试、可扩展的 PM 编排核心，但不接入 Feishu 自动触发，不执行真实 Claude/Hermes 子任务。

## 范围

支持两类请求：

- **S0**：极小改动，如 README typo。流程：PM 分类 → DEV 执行 → DEV 自检 → PM 验收。
- **S1**：局部 bug / 小修复。流程：PM 分类 → DEV 执行 → DEV 自检 → TEST 验证 → PM 验收。

本阶段不做：

- S2/S3 完整执行。
- 真实部署、重启、commit、push。
- Feishu 消息触发编排。
- 真实多 Agent / Claude / Hermes 调度。
- 审批流执行；只保留后续扩展所需的状态字段和返回结构。

## 当前背景

Stage A 已完成：Feishu Bot 稳定表现为 cccagents PM Agent，并具备 PM-only 用户边界、安全确认和密钥拒绝能力。

Stage B v1 之前，仓库里已经有测试先行文件：

- `tests/test_complexity_classifier.py`
- `tests/test_orchestrator_s0_s1.py`
- `tests/test_task_store.py`

这些测试引用了尚未实现或尚未补齐的模块：

- `src/cccagents/complexity_classifier.py`
- `src/cccagents/orchestrator.py`
- `src/cccagents/project_state.py`
- `src/cccagents/task_store.py` 的 `list_tasks/update_status/claim_task/complete_task/fail_task`

## 组件设计

### 1. complexity_classifier.py

职责：把用户自然语言请求分类成 S0/S1/S2/S3，并返回结构化决策。

核心类型：

```python
@dataclass(frozen=True)
class ComplexityDecision:
    complexity: str
    required_roles: list[str]
    requires_user_approval: bool
    risk_flags: list[str]
```

公开函数：

```python
def classify_project_request(text: str) -> ComplexityDecision:
    ...
```

第一版使用关键词规则，不调用模型。

分类规则：

- 包含 `typo`、`README`、`文档`、`docs` 等小文档信号 → S0
  - roles: `PM`, `DEV`
  - flags: `docs_only`
  - approval: false
- 包含 `bug`、`loading`、`局部`、`本地测试`、`修复` 等局部修复信号 → S1
  - roles: `PM`, `DEV`, `TEST`
  - flags: `local_test_required`
  - approval: false
- 包含 `新增`、`功能`、`接口`、`测试用例`、`CSV` 等新功能信号 → S2
  - roles: `PM`, `PDM`, `ARCH`, `DEV`, `TEST`
  - flags: `feature_change`
  - approval: false
- 包含 `调研`、`方案`、`选型`、`安全`、`认证`、`权限`、`部署`、`生产`、`secret`、`FEISHU_APP_SECRET` 等高风险或研究信号 → S3
  - roles: `PM`, `PDM`, `RES`, `ARCH`, `DEV`, `TEST`, `SEC`
  - flags: `research_required`、`security_sensitive`、`external_side_effect` 等按输入命中添加
  - approval: true when security/deploy/external-side-effect exists

优先级：S3 > S2 > S1 > S0。高风险词出现时不能被低风险词降级。

### 2. project_state.py

职责：读写项目轻量状态文件。

路径：

```text
<project_root>/<project_id>/project-state.json
```

核心类型：

```python
@dataclass(frozen=True)
class ProjectState:
    project_id: str
    status: str
    complexity: str
    executed_roles: list[str]
    artifacts: list[str]
    updated_at: str
```

公开函数：

```python
def save_project_state(project_dir: Path, state: ProjectState) -> None:
    ...

def load_project_state(project_dir: Path) -> ProjectState:
    ...
```

`project_state.py` 只负责状态文件，不负责任务调度、不调用模型、不处理 Feishu。

### 3. task_store.py 增量补齐

现有 `TaskStore` 已支持 SQLite 初始化、保存和读取任务。本阶段补齐测试要求的方法：

```python
def list_tasks(self, project_id: str, status: TaskStatus | None = None) -> list[Task]
def update_status(self, task_id: str, status: TaskStatus, updated_at: str | None = None) -> Task
def claim_task(self, task_id: str, started_at: str) -> Task
def complete_task(self, task_id: str, artifact_ids: list[str], completed_at: str) -> Task
def fail_task(self, task_id: str, issue_ids: list[str], updated_at: str) -> Task
```

行为：

- `list_tasks` 按 `created_at` 和 `id` 稳定排序，保证测试可预测。
- `update_status` 读取旧任务，用 `dataclasses.replace` 更新状态并保存。
- `claim_task` 设置 `status=RUNNING`、`started_at`、`updated_at`。
- `complete_task` 设置 `status=COMPLETED`、`output_artifact_ids`、`completed_at`、`updated_at`。
- `fail_task` 设置 `status=FAILED`、`issue_ids`、`updated_at`。
- 找不到任务时沿用 `get_task` 的 `KeyError`。

### 4. orchestrator.py

职责：编排 S0/S1 本地流程，并用 `FakeExecutor` 生成稳定产物。

核心类型：

```python
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
```

公开函数：

```python
def orchestrate_request(request: OrchestrationRequest, executor: FakeExecutor) -> OrchestrationResult:
    ...
```

`FakeExecutor` 行为：

- `run_dev(project_dir, request_text, now)` 写入：
  - `05-development/dev-summary.md`
- `run_dev_self_check(project_dir, request_text, now)` 可更新同一个 DEV summary 或写入自检段落；执行角色仍记录为第二个 `DEV`。
- `run_test(project_dir, request_text, now)` 写入：
  - `04-test-cases/test-result.md`
- `run_pm_acceptance(project_dir, request_text, now)` 写入：
  - `07-acceptance/acceptance-report.md`

S0 执行顺序：

```text
DEV → DEV → PM
```

输出文件：

```text
05-development/dev-summary.md
07-acceptance/acceptance-report.md
```

S1 执行顺序：

```text
DEV → DEV → TEST → PM
```

输出文件：

```text
05-development/dev-summary.md
04-test-cases/test-result.md
07-acceptance/acceptance-report.md
```

S2/S3 在本阶段不执行完整编排。若传入 S2/S3 请求，返回 `status="blocked"`，写入 `project-state.json`，并不生成 DEV/TEST/PM 产物。

## 数据流

1. 调用方创建：`OrchestrationRequest(project_id, text, project_root, now)`。
2. `orchestrate_request` 创建项目目录：`<project_root>/<project_id>/`。
3. 调用 `classify_project_request(text)` 得到复杂度和角色建议。
4. S0/S1 根据复杂度调用 `FakeExecutor`。
5. 收集执行角色和产物路径。
6. 写入 `project-state.json`。
7. 返回 `OrchestrationResult`。

## 错误处理

- 项目目录无法创建：让文件系统异常直接抛出，调用方处理。
- `TaskStore.get_task` 找不到任务：继续抛 `KeyError`。
- S2/S3：不抛异常，返回 `blocked`，便于后续 Stage B v2 或 Stage C 接管。
- 不做重试、不加锁、不调用远程服务、不增加 fallback。

## 测试计划

优先跑 Stage B v1 相关测试：

```bash
PYTHONPATH=src pytest -q tests/test_complexity_classifier.py tests/test_orchestrator_s0_s1.py tests/test_task_store.py
```

期望：全部通过。

然后跑全量测试：

```bash
PYTHONPATH=src pytest -q tests
```

期望：除非存在与本阶段无关的历史失败，否则全部通过。若出现与 Stage B v1 无关的失败，记录失败测试和原因，不扩大本阶段范围。

## 验收标准

- `tests/test_complexity_classifier.py` 全部通过。
- `tests/test_orchestrator_s0_s1.py` 全部通过。
- `tests/test_task_store.py` 全部通过。
- S0 产物存在：`05-development/dev-summary.md`、`07-acceptance/acceptance-report.md`。
- S1 产物存在：`05-development/dev-summary.md`、`04-test-cases/test-result.md`、`07-acceptance/acceptance-report.md`。
- `project-state.json` 能被 `load_project_state` 读取，且 `status="done"`、复杂度正确。
- 不接入 Feishu 自动触发，不执行真实外部动作。

## 后续扩展

Stage B v1 完成后，下一步可以设计：

1. **Stage B v2：Feishu 触发 S0/S1 编排**
   - Feishu PM 收到任务后创建 project_id，调用 orchestrator，并将结果摘要回传用户。
2. **Stage C：S2/S3 完整角色编排**
   - 接入 PDM/RES/ARCH/DEV/TEST/SEC、审批、review gate、安全门禁和 PM 汇总通知。
