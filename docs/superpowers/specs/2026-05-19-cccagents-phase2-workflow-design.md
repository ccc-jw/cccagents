# cccagents Phase 2 多角色流程设计

> Superseded on 2026-05-19: 本文把角色设计成了本地 Python 工作流原型。根据用户确认，PM/PDM/RES/ARCH/DEV/TEST/SEC 必须运行在实际 Hermes 中。后续以 `docs/superpowers/specs/2026-05-19-cccagents-phase2-hermes-integration-design.md` 为准；本文仅作为流程规则和数据模型参考。

日期：2026-05-19

## 1. 目标

Phase 2 的目标是在不接入飞书、不做长期异步优化的前提下，先把 Hermes 内部多 Agent 软件工程团队流程定义清楚，并形成后续可实现的状态机、任务模型、评审门禁、产物规范和执行器调用边界。

Phase 1 已验证 Claude Code CLI 可在 Linux 服务器上通过环境变量连接用户网关：

```bash
export ANTHROPIC_BASE_URL="http://cccai.store"
export ANTHROPIC_API_KEY="<redacted-api-key>"
export ANTHROPIC_MODEL="qwen3.6-plus"
```

Phase 2 基于该执行能力继续设计，但仍不实现飞书接入和长期守护进程。

## 2. Phase 2 范围

包含：

- 定义 PM / PDM / RES / ARCH / DEV / TEST / SEC 七类 Agent 角色。
- 定义每类角色的职责、输入、输出、可调用执行器。
- 定义完整项目生命周期状态机。
- 定义需求评审、技术方案评审、测试用例评审、测试/安全验证、产品验收的门禁规则。
- 定义技术方案流与测试用例流的并行隔离规则。
- 定义 Task、Review、Artifact、Issue 的核心字段。
- 定义本地产物目录和版本规则。
- 定义 Claude Code CLI Executor 的调用边界和审计记录。

不包含：

- 飞书 Bot、回调、卡片、审批交互实现。
- 长期 tmux/systemd/queue worker。
- 多项目调度器的高可用设计。
- Web 管理后台。
- 真正的 Agent 推理编排代码实现。

## 3. 总体架构

```text
Hermes
├── Agent Runtime
│   ├── PM Agent
│   ├── PDM Agent
│   ├── RES Agent
│   ├── ARCH Agent
│   ├── DEV Agent
│   ├── TEST Agent
│   └── SEC Agent
├── Workflow Engine
├── Review Gate Engine
├── Task Store
├── Memory Store
├── Artifact Store
├── Issue Store
├── Executor Adapter
│   └── Claude Code CLI
└── Audit Log
```

Phase 2 内部交互入口先用 CLI/本地命令模拟，Phase 3 再把入口换成飞书。

## 4. Agent 角色定义

### 4.1 PM Agent：项目经理

职责：

- 接收用户目标和项目启动指令。
- 创建 Project 和主流程 Task。
- 监控当前阶段、阻塞项、超时风险。
- 发起评审会议任务。
- 汇总评审结论和风险。
- 在普通流程内推动角色流转。
- 只在重大歧义、超时、失败、审批、高风险命令时打扰用户。

输入：

- 用户目标。
- Workflow Engine 当前状态。
- 各角色 Task 状态。
- Review Gate 结果。
- Issue 列表。

输出：

- 项目阶段推进决定。
- 风险摘要。
- 下一处理角色。
- 用户交互请求。

Claude Code CLI 使用场景：

- 复杂进度报告。
- 阶段复盘。
- 风险总结文档。

### 4.2 PDM Agent：产品经理

职责：

- 与用户澄清需求。
- 输出 PRD 草稿。
- 维护需求澄清记录。
- 响应 ARCH/DEV/TEST 在隔离产出期间提出的需求问题。
- 根据需求评审意见修订 PRD。
- 执行最终产品验收。

输入：

- 用户需求。
- 需求澄清问题。
- 需求评审意见。
- 验收材料。

输出：

- `prd.draft.md`
- `prd.final.md`
- `clarification-log.md`
- `requirement-review.md`
- `acceptance-report.md`
- `acceptance-issues.md`

Claude Code CLI 使用场景：

- 生成和修订 PRD。
- 汇总验收报告。

### 4.3 RES Agent：调研员

职责：

- 做技术调研、竞品分析、可行性评估。
- 为 PDM、ARCH、DEV 提供背景材料。
- 不直接改变流程状态，只提交调研产物。

输入：

- 调研主题。
- PRD 草稿或需求问题。

输出：

- `research-report.<topic>.md`
- 可行性结论。
- 风险和替代方案。

Claude Code CLI 使用场景：

- 生成调研报告。
- 分析本地代码库或技术资料。

### 4.4 ARCH Agent：架构师

职责：

- 基于已通过 PRD 输出详细技术方案。
- 定义模块边界、接口、数据模型、部署模型。
- 识别技术风险和开发拆分。
- 与 DEV 协作产出技术方案流。
- 技术方案草稿期间不直接与 TEST 沟通。

输入：

- `prd.final.md`
- PDM 澄清记录。
- RES 调研报告。

输出：

- `tech-design.draft.md`
- `tech-design.final.md`
- `api-design.md`
- `database-design.md`
- `dev-breakdown.md`
- `tech-design-review.md`

Claude Code CLI 使用场景：

- 生成详细设计文档。
- 读取代码结构。
- 分析接口和数据库设计。

### 4.5 DEV Agent：开发工程师

职责：

- 参与技术方案产出。
- 根据通过的 PRD、技术方案和测试用例进行编码。
- 执行自测、联调、冒烟测试。
- 修复 TEST、SEC、PDM 提出的缺陷。
- 修复完成后通知对应角色回归。

输入：

- `prd.final.md`
- `tech-design.final.md`
- `test-cases.final.md`
- 缺陷列表。
- 安全问题列表。
- 验收问题列表。

输出：

- 源代码变更。
- `dev-notes.md`
- `self-test-report.md`
- `integration-test-report.md`
- `smoke-test-report.md`
- 修复说明。

Claude Code CLI 使用场景：

- 编码实现。
- 运行测试/构建/lint。
- 修复 Bug。
- 生成自测和冒烟测试报告。

### 4.6 TEST Agent：测试工程师

职责：

- 基于已通过 PRD 独立输出测试用例。
- 输出 Markdown 源测试清单和 Excel 交付测试清单。
- 在测试用例草稿期间不直接与 ARCH/DEV 沟通。
- 执行功能、边界、异常、回归测试。
- 记录缺陷并通知 DEV 修复。
- 对修复项进行回归验证。

输入：

- `prd.final.md`
- PDM 澄清记录。
- 可运行代码。
- DEV 自测/冒烟报告。

输出：

- `test-cases.draft.md`
- `test-cases.final.md`
- `test-checklist.draft.md`
- `test-checklist.final.md`
- `test-checklist.draft.xlsx`
- `test-checklist.final.xlsx`
- `test-execution-report.md`
- `defect-log.md`
- `regression-report.md`

Claude Code CLI 使用场景：

- 生成测试用例文档。
- 生成测试清单 Excel。
- 执行自动化测试。
- 汇总缺陷报告。

### 4.7 SEC Agent：安全工程师

职责：

- 对代码、配置、依赖、权限、日志、密钥处理做安全审查。
- 执行 SAST 或安全规则检查。
- 记录安全问题并通知 DEV 修复。
- 对安全修复进行回归验证。

输入：

- `prd.final.md`
- `tech-design.final.md`
- 可运行代码。
- 依赖清单。
- 配置文件。

输出：

- `security-review.md`
- `security-issues.md`
- `security-regression-report.md`

Claude Code CLI 使用场景：

- 读取代码做安全审查。
- 执行本地安全检查命令。
- 生成安全报告。

## 5. Agent 模型配置

每个 Agent 的模型配置统一使用 OpenAI 兼容形式的抽象字段，但执行到 Claude Code CLI 时映射为已验证通过的环境变量。

```text
AgentModelConfig
- role_code
- model_base_url
- model_api_key_ref
- model_name
- executor_type: claude_code_cli
- enabled
```

执行映射：

```text
model_base_url -> ANTHROPIC_BASE_URL
model_api_key_ref -> ANTHROPIC_API_KEY 的密钥引用
model_name -> ANTHROPIC_MODEL / claude --model
```

密钥规则：

- 数据库和产物中只保存 `model_api_key_ref`。
- 真实 API Key 只出现在进程环境变量或密钥管理器读取结果中。
- 日志、飞书消息、Agent prompt 摘要、产物文件不得保存真实 API Key。

## 6. 项目生命周期状态机

### 6.1 主状态

```text
CREATED
  -> REQUIREMENT_DRAFTING
  -> REQUIREMENT_REVIEW
  -> REQUIREMENT_APPROVED
  -> PARALLEL_DESIGN_AND_TESTCASE
  -> DEVELOPMENT
  -> DEV_SELF_TEST
  -> TESTING_AND_SECURITY
  -> PRODUCT_ACCEPTANCE
  -> DONE
```

失败和打回：

```text
REQUIREMENT_REVIEW fail -> REQUIREMENT_DRAFTING
TECH_DESIGN_REVIEW fail -> TECH_DESIGN_DRAFTING
TEST_CASE_REVIEW fail -> TEST_CASE_DRAFTING
DEV_SELF_TEST fail -> DEVELOPMENT
TESTING_AND_SECURITY fail -> FIXING -> TESTING_AND_SECURITY
PRODUCT_ACCEPTANCE fail -> FIXING -> DEV_SELF_TEST
```

### 6.2 并行子状态

需求评审通过后同时启动两条产物流。

```text
TECH_DESIGN_FLOW:
  TECH_DESIGN_DRAFTING
    -> TECH_DESIGN_REVIEW
    -> TECH_DESIGN_APPROVED

TEST_CASE_FLOW:
  TEST_CASE_DRAFTING
    -> TEST_CASE_REVIEW
    -> TEST_CASE_APPROVED
```

汇合门禁：

```text
TECH_DESIGN_APPROVED
AND
TEST_CASE_APPROVED
=> DEVELOPMENT
```

## 7. 技术方案流与测试用例流隔离规则

隔离期：

```text
从 REQUIREMENT_APPROVED 开始
到 TECH_DESIGN_APPROVED 且 TEST_CASE_APPROVED 结束
```

规则：

- ARCH/DEV 可以互相协作产出技术方案。
- TEST 独立产出测试用例和测试清单。
- ARCH/DEV 与 TEST 在草稿阶段不允许直接交流。
- 双方不能读取对方未评审通过的草稿。
- 任何需求疑问都只能提交给 PDM。
- PDM 的回答必须进入 `clarification-log.md`。
- 如果 PDM 澄清改变需求范围，PM 必须判断是否回到 `REQUIREMENT_REVIEW`。
- 两条产物流分别评审，分别打回。
- 只有两个流都通过后才进入开发。

## 8. 评审门禁

### 8.1 需求评审

发起人：PDM  
参与人：PM、PDM、RES、ARCH、DEV、TEST、SEC

输入：

- `prd.draft.md`
- `clarification-log.md`
- 必要调研报告

通过条件：

- 所有角色无阻塞疑问。
- 需求范围明确。
- 验收标准明确。
- 安全、测试、技术风险已记录。

失败输出：

- `requirement-review.md` 中记录问题。
- 状态回到 `REQUIREMENT_DRAFTING`。
- `next_handler_role=PDM`。

### 8.2 技术方案评审

发起人：ARCH  
参与人：PM、PDM、RES、ARCH、DEV、TEST、SEC

输入：

- `tech-design.draft.md`
- `api-design.md`
- `database-design.md`
- `dev-breakdown.md`

通过条件：

- 模块边界清楚。
- 接口和数据模型清楚。
- 开发拆分可执行。
- 关键风险有处理方案。
- 与 PRD 一致。

失败输出：

- `tech-design-review.md` 中记录问题。
- 状态回到 `TECH_DESIGN_DRAFTING`。
- `next_handler_role=ARCH` 或 `DEV`。

### 8.3 测试用例评审

发起人：TEST  
参与人：PM、PDM、RES、ARCH、DEV、TEST、SEC

输入：

- `test-cases.draft.md`
- `test-checklist.draft.md`
- `test-checklist.draft.xlsx`

通过条件：

- 覆盖 PRD 验收标准。
- 覆盖正常、边界、异常、回归、安全相关场景。
- 每条测试点有明确预期结果。
- Excel 测试清单字段符合固定 schema。

失败输出：

- `test-case-review.md` 中记录问题。
- 状态回到 `TEST_CASE_DRAFTING`。
- `next_handler_role=TEST`。

### 8.4 开发自测门禁

发起人：DEV

输入：

- 源码变更。
- 自动化测试结果。
- `self-test-report.md`
- `integration-test-report.md`
- `smoke-test-report.md`

通过条件：

- DEV 自测通过。
- 冒烟测试通过。
- 无阻塞构建或运行错误。

失败输出：

- 回到 `DEVELOPMENT`。
- `next_handler_role=DEV`。

### 8.5 测试与安全验证门禁

发起人：PM  
执行人：TEST、SEC 并行

通过条件：

- TEST 测试清单全部通过或非阻塞项有明确豁免。
- SEC 安全问题全部关闭或非阻塞项有明确豁免。
- 回归验证通过。

失败输出：

- TEST 问题写入 `defect-log.md`。
- SEC 问题写入 `security-issues.md`。
- 状态进入 `FIXING`。
- `next_handler_role=DEV`。

### 8.6 产品验收门禁

发起人：PDM

输入：

- PRD final。
- 测试执行报告。
- 安全回归报告。
- DEV 修复说明。
- 可运行交付物。

通过条件：

- PDM 验收通过。
- 验收问题清单为空或全部关闭。

失败输出：

- `acceptance-issues.md`。
- 状态进入 `FIXING`。
- `next_handler_role=DEV`。

## 9. 核心数据模型

### 9.1 Project

```text
Project
- id
- name
- status
- current_phase
- owner
- created_at
- updated_at
```

### 9.2 Task

```text
Task
- id
- project_id
- parent_task_id
- phase
- flow: main/tech_design/test_case/development/quality/security/acceptance
- assignee_role
- status: pending/running/blocked/reviewing/approved/rejected/completed/failed/interrupted
- title
- description
- input_artifact_ids
- output_artifact_ids
- issue_ids
- created_at
- started_at
- updated_at
- due_at
- completed_at
- next_handler_role
- next_handler_reason
```

### 9.3 Review

```text
Review
- id
- project_id
- phase
- review_type: requirement/tech_design/test_case/self_test/quality_security/acceptance
- status: pending/pass/fail
- participants
- required_roles
- issues
- decision_summary
- created_at
- completed_at
```

### 9.4 Artifact

```text
Artifact
- id
- project_id
- phase
- owner_role
- type
- path
- version
- status: draft/final/review/report/log
- source_artifact_id
- created_at
- updated_at
```

### 9.5 Issue

```text
Issue
- id
- project_id
- source: requirement_review/tech_design_review/test_case_review/test/security/acceptance
- severity: blocker/high/medium/low
- title
- description
- owner_role
- status: open/fixing/fixed/verified/closed/waived
- related_task_id
- related_artifact_id
- created_at
- updated_at
- closed_at
```

## 10. 本地产物目录

```text
projects/<project_id>/
  00-meta/
    project.yaml
    phase-log.md
    operation-log.md
    clarification-log.md

  01-requirements/
    prd.draft.md
    prd.final.md
    requirement-review.md

  02-tech-design/
    tech-design.draft.md
    tech-design.final.md
    api-design.md
    database-design.md
    dev-breakdown.md
    tech-design-review.md

  03-test-cases/
    test-cases.draft.md
    test-cases.final.md
    test-checklist.draft.md
    test-checklist.final.md
    test-checklist.draft.xlsx
    test-checklist.final.xlsx
    test-case-review.md

  04-development/
    dev-notes.md
    self-test-report.md
    integration-test-report.md
    smoke-test-report.md

  05-quality-validation/
    defect-log.md
    test-execution-report.md
    regression-report.md

  06-security/
    security-review.md
    security-issues.md
    security-regression-report.md

  07-acceptance/
    acceptance-report.md
    acceptance-issues.md

  08-logs/
    command-log.jsonl
    agent-runs/<run_id>/
      prompt.md
      stdout.log
      stderr.log
      result.json
```

## 11. Claude Code CLI Executor 边界

执行器输入：

```text
ExecutorRunRequest
- project_id
- task_id
- run_id
- agent_role
- phase
- cwd
- prompt
- allowed_tools
- permission_mode
- env_refs
```

执行器环境变量：

```text
ANTHROPIC_BASE_URL=<role.model_base_url>
ANTHROPIC_API_KEY=<resolved secret from model_api_key_ref>
ANTHROPIC_MODEL=<role.model_name>
```

执行规则：

- 每次 Task 执行创建一个新的 `run_id`。
- `cwd` 必须位于 `workspaces/<project_id>/repo/` 或 `projects/<project_id>/`。
- 不允许跨项目读取或写入。
- L0/L1 命令可在项目绑定后自动执行。
- L2/L3 命令必须进入审批流程。
- stdout/stderr 落盘前必须脱敏。
- 原始 API Key 不写入任何日志。

## 12. 权限策略

```text
L0: 只读
- ls
- git status
- git diff
- grep/rg

L1: 本地项目写入或测试
- mkdir
- 写项目产物
- pytest
- npm test
- 生成 Markdown / Excel

L2: 项目依赖或迁移级变更
- npm install
- pip install
- 数据库迁移
- 修改 CI/CD 配置

L3: 外部影响或高风险动作
- git push
- gh pr create
- kubectl apply
- terraform apply
- rm -rf
- force push
```

默认决策：

```text
L0 -> allow
L1 -> allow if bound_project=true
L2 -> require_approval
L3 -> require_approval
unbound write -> deny
cross-project access -> deny
secret visible in command/log -> deny or redact before persist
```

## 13. 审计与日志

每次命令执行必须写入项目级日志：

```text
projects/<project_id>/08-logs/command-log.jsonl
```

字段：

```text
project_id
task_id
run_id
phase
agent_role
cwd
command
permission_level
policy_decision
risk_reason
approval_id
started_at
completed_at
exit_code
stdout_path
stderr_path
redacted
redaction_reason
```

PM Agent 使用这些日志做进度监控、失败恢复和用户汇报。

## 14. Phase 2 验收标准

Phase 2 通过条件：

- 可以创建一个本地 Project。
- 可以按状态机创建并推进 Task。
- 可以生成 PRD、技术方案、测试用例、测试清单、安全报告、验收报告的路径记录。
- 可以表达技术方案流和测试用例流的并行隔离关系。
- 可以记录评审 pass/fail，并根据 fail 回流到正确角色。
- 可以为每个 Agent 绑定模型配置引用。
- 可以构造 Claude Code CLI ExecutorRunRequest。
- 可以记录命令日志和运行日志。

Phase 2 不要求：

- 飞书真实收发消息。
- 后台常驻运行。
- 多项目并发调度。
- 完整 Web UI。

## 15. 下一步实施建议

Phase 2 可以拆成以下实现任务：

1. 定义核心枚举和数据模型。
2. 实现项目目录初始化器。
3. 实现 Artifact Store 路径与注册逻辑。
4. 实现 Task Store 的本地 SQLite 原型。
5. 实现 Workflow Engine 状态流转规则。
6. 实现 Review Gate Engine。
7. 实现 Agent Role 配置与 Claude Code CLI 环境变量映射。
8. 实现 ExecutorRunRequest 构造器。
9. 实现一个本地端到端 dry run：需求草稿 -> 需求评审通过 -> 技术方案/测试用例并行 -> 汇合进入开发。
