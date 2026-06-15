# cccagents 全自动多角色编排设计

## 1. 背景与目标

当前 cccagents 已完成从飞书到 Hermes PM Agent、再到 Claude Code CLI 执行器的最小闭环验证。现有系统已经具备：

- Claude Code CLI 在 Linux 上运行并直连 OpenAI-compatible 网关。
- Hermes Gateway 接入 Feishu websocket。
- Feishu 用户入口绑定 PM-only 边界。
- PM -> DEV -> Claude Code CLI -> 本地产物 -> PM -> Feishu 的最小闭环。
- systemd 服务化、allowlist、项目隔离、权限分级、重启恢复、脱敏和 PM 通知基础能力。

新的目标是把系统从 MVP 升级为完整自动编排系统：

```text
飞书 -> PM -> PDM/ARCH/DEV/TEST/SEC 全自动协作
     -> 多轮评审
     -> 自动验收/人工审批
     -> 长周期恢复
```

核心约束：

- 用户只通过 Feishu 与 PM Agent 交互。
- PDM、RES、ARCH、DEV、TEST、SEC 不直接联系 Feishu 用户。
- Claude Code CLI 负责实际工程执行。
- Hermes 角色负责产物生成、评审和协作。
- 程序状态机负责流程推进、角色组队、评审门禁、恢复和审计。
- 简单低风险任务自动验收；高风险、L2/L3、外部副作用任务必须人工审批。

## 2. 总体原则

第一期采用混合编排方案：

```text
程序决定流程和组队，Agent 负责产物。
```

程序层负责：

- 项目复杂度分类。
- 动态角色组队。
- 任务创建和阶段推进。
- 并行分支控制。
- 评审门禁和失败回流。
- 自动验收与飞书审批分流。
- 长周期重启恢复。
- 审计日志和证据落盘。

Agent 层负责：

- PDM 写 PRD 和产品验收说明。
- RES 做调研和方案对比。
- ARCH 写技术方案。
- DEV 写代码、自测和修复。
- TEST 写测试用例、Excel、测试报告。
- SEC 做安全审查。
- PM 汇总状态、风险、结果和用户通知。

Claude Code CLI 作为每个角色的执行器，执行明确 prompt，并把 stdout、stderr、结果、产物和命令日志保存到项目目录。

## 3. 动态复杂度分级与角色组队

不是所有项目都强制七角色全员参与。Orchestrator 在入口阶段先根据用户请求和项目上下文做复杂度分类。

### 3.1 S0 极小变更

适用：

- 文案修改。
- README 或注释小改。
- typo。
- 不涉及代码逻辑、安全、外部系统的极小变更。

参与角色：

```text
PM + DEV
```

流程：

```text
PM 确认目标 -> DEV 修改 -> DEV 自测或说明无需测试 -> PM 自动验收 -> Feishu 通知
```

### 3.2 S1 小型代码变更

适用：

- 局部 bug。
- 简单函数或局部逻辑。
- 小范围代码变更。
- 本地测试即可验证。

参与角色：

```text
PM + DEV + TEST
```

流程：

```text
PM 拆任务 -> DEV 修改并自测 -> TEST 验证 -> PM 自动验收/通知
```

### 3.3 S2 中型功能或跨文件变更

适用：

- 明确的新功能。
- 跨文件或跨模块修改。
- 需要 PRD、技术方案、测试用例和产品验收。

参与角色：

```text
PM + PDM + ARCH + DEV + TEST
```

流程：

```text
PDM 明确需求
-> ARCH/DEV 技术方案 与 TEST 测试用例并行
-> PM 评审两个分支
-> DEV 开发
-> TEST 验证
-> PDM/PM 验收
-> PM 通知
```

### 3.4 S3 高风险或复杂项目

适用：

- 新系统或大功能。
- 认证、权限、密钥、支付、外部 API。
- 数据库迁移、部署、服务重启、生产变更。
- 多仓库、多项目、长周期任务。
- 需要调研和安全审查。

参与角色：

```text
PM + PDM + RES + ARCH + DEV + TEST + SEC
```

流程：

```text
PDM 需求澄清
-> RES 调研（如需要）
-> ARCH/DEV 技术方案 + TEST 测试用例 + SEC 安全计划/审查并行
-> 多角色评审
-> DEV 开发
-> TEST 验证
-> SEC 安全审查
-> PDM 产品验收
-> PM 最终评审
-> Feishu 审批或通知
```

### 3.5 动态升级规则

复杂度分类之外，还需要风险触发器：

| 条件 | 自动动作 |
| --- | --- |
| 需求不清、目标含糊 | 加入 PDM |
| 需要外部资料、技术选型、方案对比 | 加入 RES |
| 跨模块、架构变化、数据库变化 | 加入 ARCH |
| 任何实现工作 | 加入 DEV |
| 需要测试用例、验证、回归 | 加入 TEST |
| 密钥、认证、权限、支付、外部 API、部署、删除、force | 加入 SEC 并触发审批 |
| L2/L3 操作 | PM 请求 Feishu 人工审批 |

例如：S1 小改如果发现涉及 secret，应升级为 `S1 + SEC + Feishu approval`。

## 4. 生命周期状态机

入口统一为：

```text
Feishu 用户消息
-> PMRoute
-> Project Orchestrator
-> Complexity Classifier
-> 选择 S0/S1/S2/S3 流程模板
```

分类结果落盘，示例：

```json
{
  "complexity": "S1",
  "required_roles": ["PM", "DEV", "TEST"],
  "risk_flags": ["code_change", "local_test_required"],
  "requires_user_approval": false,
  "reason": "局部代码变更，需要开发和测试验证，但不涉及权限/外部系统/部署"
}
```

### 4.1 S0 状态机

```text
CREATED
-> CLASSIFIED(S0)
-> DEV_IMPLEMENTATION
-> DEV_SELF_TEST
-> PM_AUTO_ACCEPTANCE
-> PM_NOTIFY_USER
-> DONE
```

失败回流：

```text
DEV_SELF_TEST failed -> DEV_IMPLEMENTATION
```

自动回流最多 1 次。

### 4.2 S1 状态机

```text
CREATED
-> CLASSIFIED(S1)
-> DEV_IMPLEMENTATION
-> DEV_SELF_TEST
-> TEST_VALIDATION
-> PM_AUTO_ACCEPTANCE
-> PM_NOTIFY_USER
-> DONE
```

失败回流：

```text
TEST_VALIDATION failed -> DEV_FIXING -> DEV_SELF_TEST -> TEST_VALIDATION
```

自动回流最多 2 次。

### 4.3 S2 状态机

```text
CREATED
-> CLASSIFIED(S2)
-> REQUIREMENT_DRAFTING(PDM)
-> REQUIREMENT_REVIEW(PM)
-> PARALLEL_DESIGN_AND_TESTCASE
   ├── TECH_DESIGN_DRAFTING(ARCH/DEV)
   └── TEST_CASE_DRAFTING(TEST)
-> DESIGN_AND_TESTCASE_REVIEW(PM)
-> DEVELOPMENT(DEV)
-> DEV_SELF_TEST
-> TEST_VALIDATION(TEST)
-> PRODUCT_ACCEPTANCE(PDM/PM)
-> PM_NOTIFY_USER
-> DONE
```

S2 要求技术方案和测试用例并行隔离：

- ARCH/DEV 负责技术方案。
- TEST 负责测试用例。
- 草稿期间双方不互读草稿。
- 有需求问题，各自创建 PDM clarification task。
- 两边都评审通过后才能进入开发。

### 4.4 S3 状态机

```text
CREATED
-> CLASSIFIED(S3)
-> REQUIREMENT_DRAFTING(PDM)
-> RESEARCH(RES)
-> REQUIREMENT_REVIEW(PM/PDM)
-> PARALLEL_DESIGN_TEST_SECURITY
   ├── TECH_DESIGN_DRAFTING(ARCH/DEV)
   ├── TEST_CASE_DRAFTING(TEST)
   └── SECURITY_PLAN_OR_REVIEW(SEC)
-> MULTI_REVIEW_GATE(PM)
-> DEVELOPMENT(DEV)
-> DEV_SELF_TEST
-> TEST_VALIDATION(TEST)
-> SECURITY_REVIEW(SEC)
-> PRODUCT_ACCEPTANCE(PDM)
-> PM_FINAL_REVIEW
-> FEISHU_USER_APPROVAL_OR_NOTIFY
-> DONE
```

S3 默认需要 TEST、SEC、PDM、PM 全部通过。若有 L2/L3、部署、提交、PR、外部系统或高安全风险，必须 Feishu 人工审批。

## 5. 核心模块设计

现有代码中已经有状态机、评审、恢复、调度、任务模型等基础模块。本设计新增编排胶水层，复用已有零件。

### 5.1 `complexity_classifier.py`

职责：把用户请求分类为 S0/S1/S2/S3，并输出角色和风险 flag。

第一期使用规则引擎，不依赖 LLM：

- 文档、typo -> S0。
- 局部 bug、小函数 -> S1。
- 新功能、跨文件、接口变化 -> S2。
- auth、secret、deploy、db、migration、external API、delete、force -> S3。

输出：

```python
ComplexityDecision(
    complexity="S2",
    required_roles=["PM", "PDM", "ARCH", "DEV", "TEST"],
    risk_flags=["code_change", "cross_file_change"],
    requires_user_approval=False,
    reason="新增中型功能，需要需求澄清、技术方案和测试用例",
)
```

### 5.2 `role_plan.py`

职责：根据复杂度和风险生成角色任务计划。

输出：

```python
RolePlan(
    phases=[
        PhasePlan(
            "REQUIREMENT_DRAFTING",
            parallel=False,
            tasks=[RoleTask(role="PDM", template="draft_prd")],
        ),
        PhasePlan(
            "PARALLEL_DESIGN_AND_TESTCASE",
            parallel=True,
            tasks=[
                RoleTask(role="ARCH", template="draft_tech_design"),
                RoleTask(role="TEST", template="draft_test_cases"),
            ],
        ),
        PhasePlan(
            "DEVELOPMENT",
            parallel=False,
            tasks=[RoleTask(role="DEV", template="implement_feature")],
        ),
    ]
)
```

它决定：

- 哪些角色参与。
- 哪些任务可以并行。
- 哪些任务互相隔离。
- 哪些任务等待评审。
- 哪些任务需要用户审批。

### 5.3 `orchestrator.py`

核心模块。每次 tick 推进一个或多个项目。

流程：

```text
load project state
load pending/running/reviewing tasks
reconcile interrupted tasks
if no classification: classify request
if no role plan: create role plan
find runnable tasks
for each runnable task:
    dispatch through scheduler.decide_dispatch()
    build Claude Code prompt
    execute or enqueue run
collect completed task outputs
register artifacts
run review gate
advance phase
send PM notification / approval request if needed
persist everything
```

第一期可以同步执行，不引入复杂 worker queue。

### 5.4 扩展 `pm_scheduler.py`

当前主循环是空转守护。目标改为：

```python
while True:
    for project in list_projects(project_root):
        reconcile_project_after_restart(project)
        orchestrate_project(project)
    time.sleep(interval_seconds)
```

要求：

- 扫描项目。
- 调用恢复逻辑。
- 调用编排器。
- 记录 tick 日志。
- 捕获异常，不让服务崩溃。
- 对异常项目通知 PM。

### 5.5 扩展 `claude_executor.py`

新增：

```python
ClaudeRunRequest
ClaudeRunResult
run_claude_task()
```

职责：

- 注入环境变量。
- 设置 cwd。
- 设置 allowed tools。
- 捕获 stdout/stderr。
- 写 run evidence。
- 写 command log。
- 返回 exit code 和产物摘要。
- 默认不允许 `--dangerously-skip-permissions`。

每次执行落盘：

```text
projects/<project_id>/08-logs/hermes-runs/<run_id>/
  prompt.md
  stdout.txt
  stderr.txt
  result.json
```

### 5.6 `prompt_builder.py`

职责：根据角色和任务生成稳定 prompt。

每个 prompt 必须包含：

- role file reference。
- project_id。
- phase。
- task_id。
- workspace path。
- input artifact paths。
- expected output paths。
- allowed operations。
- forbidden operations。
- completion report format。

这样避免每次靠自由聊天。

### 5.7 `review_engine.py`

职责：把任务结果转成评审记录，并调用 `review_gate.py`。

评审来源分三类：

- rule-based review：程序检查文件、exit code、测试结果、secret scan、权限。
- role-based review：TEST、SEC、PDM 等角色给出报告。
- user approval review：Feishu 审批结果。

输出：

```python
ReviewResult(
    review_type="quality",
    passed=True,
    issues=[],
    next_phase="PRODUCT_ACCEPTANCE",
    next_handler_role="PDM",
)
```

### 5.8 `project_state.py`

项目级状态文件：

```text
projects/<project_id>/project-state.json
```

字段：

- project_id。
- complexity。
- required_roles。
- current_phase。
- risk_flags。
- approval_policy。
- retry_count。
- created_at。
- updated_at。
- last_pm_notification_at。

### 5.9 扩展 `TaskStore`

新增：

```python
list_tasks(project_id, status=None)
claim_task(task_id)
complete_task(task_id, output_artifact_ids)
fail_task(task_id, issues)
update_status(task_id, status)
```

Orchestrator 只调度 `pending` 且依赖满足的任务。

### 5.10 安全 P0 修复

自动编排前先修：

1. `validate_card_content` 类型比较。
2. 安全内容放行测试。
3. `.gitignore` 加 `.env`、`*.env`。
4. 扩展常见 secret 脱敏模式。

## 6. 持久化结构

项目目录：

```text
/home/ubuntu/cccagents/
  workspaces/
    <project_id>/
      repo/
  projects/
    <project_id>/
      project-state.json
      tasks.db
      role-plan.json
      reviews.jsonl
      approvals.jsonl
      artifacts.jsonl
      run-records.jsonl
      issues.jsonl
      01-input/
        feishu-message.json
      02-requirements/
        prd.md
        prd-review.md
      03-architecture/
        tech-design.md
        tech-design-review.md
      04-test-cases/
        test-cases.md
        test-cases.xlsx
        test-result.md
      05-development/
        dev-summary.md
        self-test.md
      06-security/
        security-review.md
      07-acceptance/
        acceptance-report.md
      08-logs/
        command-log.jsonl
        pm-notifications.jsonl
        scheduler-ticks.jsonl
        restart-recovery.jsonl
        hermes-runs/
          <run_id>/
            prompt.md
            stdout.txt
            stderr.txt
            result.json
```

关键规则：

- `workspaces/<project_id>/repo` 只放项目代码。
- `projects/<project_id>/` 放状态、产物和证据。
- 每个角色产物写固定目录。
- 所有日志必须脱敏。
- 所有路径必须按 `project_id` 隔离。

## 7. 恢复策略

重启后恢复流程：

```text
pm_scheduler starts
-> scan /home/ubuntu/cccagents/projects/*
-> for each project:
   read project-state.json
   read tasks.db
   read run-records.jsonl
   reconcile running/interrupted tasks
   append restart-recovery.jsonl
   if safe, requeue pending task
   if unsafe, notify PM/Feishu
   continue orchestrate_project(project_id)
```

恢复要求：

- 已完成任务不重跑。
- 已登记产物不覆盖。
- running 但失联的任务标记 interrupted。
- L0/L1、幂等、非破坏、非外部任务可以自动 retry。
- L2/L3、破坏性、外部副作用任务必须人工确认。
- pending approval 不自动执行。
- PM 能向用户解释恢复结果。

## 8. 评审、自动验收和审批

### 8.1 Review 类型

第一期定义：

| Review 类型 | 触发阶段 | 参与角色 | 目的 |
| --- | --- | --- | --- |
| requirement | PDM 完成 PRD 后 | PM/PDM | 需求是否明确 |
| tech_design | ARCH/DEV 完成方案后 | PM/ARCH/DEV | 方案是否可开发 |
| test_case | TEST 完成用例后 | PM/TEST | 覆盖是否足够 |
| self_test | DEV 完成开发后 | DEV | 自测是否通过 |
| quality | TEST 执行测试后 | TEST | 功能和回归是否通过 |
| security | SEC 审查后 | SEC | 安全风险是否可接受 |
| acceptance | 最终交付前 | PDM/PM/用户 | 是否满足用户目标 |

### 8.2 自动验收规则

S0 自动验收条件：

```text
DEV completed
AND DEV self-test passed or explicitly not required
AND no L2/L3
AND no security risk flag
AND no external side effect
```

S1 自动验收条件：

```text
DEV completed
AND self_test passed
AND TEST validation passed
AND no L2/L3
AND no SEC risk
```

S2 条件自动验收：

```text
requirement passed
AND tech_design passed
AND test_case passed
AND DEV self_test passed
AND TEST quality passed
AND PDM acceptance passed
AND no L2/L3
AND no SEC risk
```

S3 默认更严格。若没有 L2/L3、部署、外部副作用，可 PM 自动通知完成；只要存在任一高风险条件，必须 Feishu 人工审批。

### 8.3 失败回流

| 失败位置 | 回流对象 |
| --- | --- |
| requirement | PDM |
| tech_design | ARCH/DEV |
| test_case | TEST |
| self_test | DEV |
| quality | DEV |
| security | DEV/ARCH |
| acceptance | PDM/DEV |

每次回流创建新 task，保留旧产物版本。

默认自动回流次数：

| 复杂度 | 次数 | 超过后 |
| --- | ---: | --- |
| S0 | 1 | PM 通知失败，需要人工处理 |
| S1 | 2 | PM 汇总问题，请用户决策 |
| S2 | 2 | PM 请求用户确认是否继续 |
| S3 | 1 | 默认进入人工审批 |

### 8.4 飞书审批动作

第一期支持：

```text
approve
reject
comment
pause_project
resume_project
```

审批事件必须持久化，避免服务重启后 replay 防护失效。

## 9. 测试与验收策略

### 9.1 单元测试

新增：

```text
test_complexity_classifier.py
test_role_plan.py
test_project_state.py
test_orchestrator.py
test_review_engine.py
test_prompt_builder.py
```

覆盖：分类、组队、风险升级、并行分支、S3 SEC、自动验收、人工审批、失败回流、状态落盘和 prompt 内容。

### 9.2 安全回归测试

新增：

```text
test_clean_card_content_is_approved
test_env_files_are_gitignored
test_feishu_secret_names_are_redacted
test_seen_event_ids_survive_restart
```

### 9.3 Fake executor 集成测试

使用 FakeClaudeExecutor 模拟角色产物，不调用真实模型：

- PDM -> `prd.md`。
- ARCH -> `tech-design.md`。
- TEST -> `test-cases.md`、`test-cases.xlsx`、`test-result.md`。
- DEV -> `dev-summary.md`。
- SEC -> `security-review.md`。

覆盖 S0、S1、S2、S3 全流程。

### 9.4 恢复测试

覆盖：

- running task interrupted。
- L2/L3 interrupted 等待审批。
- completed artifact 不重跑。
- pending approval survive restart。

### 9.5 真实 smoke

全新服务器部署后跑：

- S0：README 增加一行。
- S1：新增简单 Python 函数和测试。
- S2：新增小功能，生成 PRD、技术方案、测试用例、实现和测试报告。
- S3：模拟涉及密钥配置的变更，只生成方案和安全审查，不写真实密钥。

## 10. 部署脚本

新增：

```text
scripts/phase5/preflight_check.sh
scripts/phase5/verify_deployment.sh
scripts/phase5/run_orchestrator_smoke.sh
```

`preflight_check.sh` 检查：

- Python、Node.js、npm。
- Claude Code CLI。
- Hermes。
- `cccai.store` 连通性。
- `/home/ubuntu/.hermes/.env` 权限。
- `config.yaml` 的 base_url、default model、terminal.cwd。
- Feishu allowlist。
- 磁盘空间。

`verify_deployment.sh` 检查：

- systemd 服务 enabled/active。
- pytest 全部通过。
- 密钥扫描通过。
- Hermes chat OK。
- Claude Code CLI OK。
- unit 文件关键字段。
- 项目目录可写。

`run_orchestrator_smoke.sh` 跑 S0/S1/S2/S3 smoke，并输出 PASS/FAIL summary。

## 11. 里程碑

### M0：安全 P0 修复和部署基础加固

范围：

- 修复 `validate_card_content`。
- `.gitignore` 加 `.env`、`*.env`。
- 扩展脱敏规则。
- 补测试。
- 增加 preflight 雏形。

### M1：复杂度分类和动态组队

新增：

- `complexity_classifier.py`。
- `role_plan.py`。
- 对应测试。

验收：S0/S1/S2/S3 和风险升级正确。

### M2：项目状态和任务推进 Orchestrator

新增/扩展：

- `project_state.py`。
- `orchestrator.py`。
- `prompt_builder.py`。
- TaskStore list/update/claim/complete/fail。
- pm_scheduler 主循环调用 orchestrator。

验收：Fake executor 下 S0/S1 可从 CREATED 到 DONE。

### M3：S2 并行设计/测试用例 + 评审引擎

新增：

- `review_engine.py`。
- S2 fake 集成测试。
- 并行隔离测试。

验收：S2 全流程 DONE，失败正确回流。

### M4：真实 Claude Code CLI 执行集成

扩展：

- `claude_executor.py`。
- `command_log.py`。
- `agent_config.py`。

验收：真实 CLI 下 S0/S1/S2 smoke 通过，run evidence 和 command log 完整。

### M5：飞书审批、真实端到端 smoke 和长周期恢复

新增/扩展：

- approval persistence。
- Feishu approval handling。
- phase5 verify/smoke 脚本。

验收：真实 Feishu S0/S1/S2 smoke，S3 审批 smoke，重启恢复通过。

## 12. 第一轮实施范围

第一轮建议实现 M0-M3：

```text
M0 安全修复
M1 复杂度分类 + 动态组队
M2 Orchestrator 跑通 S0/S1
M3 S2 并行方案/测试用例 + 评审
```

理由：

- M0-M3 可用 fake executor 稳定测试。
- 不依赖网络、飞书、真实模型。
- 先证明状态机和编排逻辑正确。
- 再进入 M4/M5 接真实 Claude Code CLI 和 Feishu。

第一轮完成标准：

```bash
PYTHONPATH=src .venv/bin/pytest -q tests
```

新增测试证明：

- S0 自动完成。
- S1 自动完成。
- S2 自动完成。
- S2 并行隔离。
- 失败正确回流。
- 自动验收/人工审批分流。
- 安全 P0 修复。

第二轮 M4-M5 完成后，服务器上必须证明：

```text
飞书 -> PM -> 动态组队 -> 角色执行 Claude Code -> 多轮评审 -> 自动验收/审批 -> PM 通知 -> 重启恢复
```

## 13. 范围外

第一轮不做：

- 分布式 worker queue。
- 多服务器调度。
- 真正并发执行多个 Claude Code 子进程的复杂资源调度。
- 自动创建 GitHub 仓库后的完整 PR 发布流。
- 生产部署自动执行。
- 外部系统写操作的自动批准。

这些留到 M4/M5 或后续版本，并必须经过 Feishu 人工审批。
