# cccagents 严格门禁型设计方案

日期：2026-05-19

## 1. 背景与目标

用户希望在 Linux 云服务器上部署 Hermes，并搭建多 Agent 协作的软件工程团队。用户通过飞书只与项目经理 Agent 交互；Hermes 负责记忆、协调、状态和任务流转；Claude Code CLI 负责代码和文档的具体执行。

当前最大痛点是：在 Mac 上使用 Claude Code CLI 做长周期项目时，需要一直守在终端前处理审批，难以支撑长期异步项目。

本设计采用严格门禁型路线：先验证 Linux 上 Claude Code CLI 执行器是否成立，再定义多角色流程，再接入飞书，最后优化长期异步执行。

## 2. 总体路线

```text
Phase 1：Linux Claude Code CLI 执行器验证
  1A. Ubuntu 云服务器安装 Claude Code CLI
  1B. 验证 Claude Code CLI 是否原生支持 OpenAI 兼容 base_url/api_key/model
  1C. 验证单执行器代码任务

Phase 2：多角色软件工程流程定义
  定义 PM / PDM / RES / ARCH / DEV / TEST / SEC 的职责、输入输出、评审门禁、状态流转。

Phase 3：飞书接入
  用户只通过飞书与 Hermes 中的 PM Agent 交互，PM Agent 负责通知、审批、驳回、状态查询。

Phase 4：长期异步执行优化
  支持跨天任务、失败恢复、日志回放、进度监控、超时提醒、无人值守运行。
```

## 3. 生死门禁

Phase 1B 是项目生死门禁：

```text
如果 Claude Code CLI 不能原生直连 OpenAI 兼容 base_url/api_key/model：
- 项目停止；
- 不引入协议适配层；
- 不替换执行器；
- 不拆分模型来源；
- 不继续做多角色、飞书或长期异步执行。
```

## 4. Phase 1：Linux 安装与执行器验证

### 4.1 执行环境

```text
OS: Ubuntu 22.04 / 24.04
运行方式: 宿主机直接安装
运行用户: 普通 Linux 用户，避免长期使用 root
项目目录: ~/workspaces/cccagents
日志目录: ~/.claude/cccagents-logs 与 projects/<project_id>/08-logs/
```

### 4.2 Phase 1A：安装 Claude Code CLI

Linux 操作清单：

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

验收标准：

```text
- claude 命令存在；
- claude --version 正常输出；
- claude --help 正常输出；
- 普通用户可执行 claude；
- 安装过程和命令结果保存到 Linux 本地。
```

### 4.3 Phase 1B：OpenAI 兼容网关验证

目标是确认 Claude Code CLI 本体是否能直接配置：

```text
- base_url
- api_key
- model
```

验证内容：

```text
- 查找 Claude Code CLI 是否有官方配置入口；
- 尝试通过环境变量或配置文件指定模型网关；
- 启动 Claude Code CLI；
- 执行一次最小对话或代码分析任务；
- 确认请求是否打到用户已有的 OpenAI 兼容网关。
```

失败判定流程：

```text
1. 记录 Claude Code CLI 版本与安装来源；
2. 检查 claude --help、配置目录、官方配置说明中是否存在 OpenAI-compatible base_url/api_key/model 配置入口；
3. 在不引入协议适配层的前提下，尝试配置用户已有网关；
4. 执行最小请求，并通过网关访问日志或 CLI 输出确认请求目标；
5. 保存验证命令、配置片段脱敏版、输出日志、失败原因到 Phase 1B 验证报告；
6. 若只能通过 Anthropic/Claude 官方协议、协议适配层、替代执行器或拆分模型来源实现，则判定 fail。
```

验收标准：

```text
pass:
- Claude Code CLI 使用 OpenAI 兼容网关完成一次真实任务；
- 验证报告包含版本、配置方式、脱敏配置、执行命令、网关命中证据和产物路径。

fail:
- CLI 不支持配置 OpenAI-compatible base_url/api_key/model；
- 或必须依赖协议适配层；
- 或只能走 Anthropic/Claude 官方协议。
```

失败处理：项目停止。

### 4.4 Phase 1C：单执行器代码任务验证

只有 Phase 1B 通过才进入 Phase 1C。

验证任务：

```text
- clone cccagents 仓库；
- 让 Claude Code CLI 读取 README 或源码；
- 让 Claude Code CLI 生成 docs/phase1-verification.md；
- 让 Claude Code CLI 执行 git status、项目可用的测试/构建命令；
- 保存执行日志和产物。
```

Linux 操作清单示例：

```bash
mkdir -p ~/workspaces
cd ~/workspaces
git clone https://github.com/ccc-jw/cccagents.git
cd cccagents
git status
claude
```

Phase 1C 通过标准：

```text
- Claude Code CLI 在项目目录内完成一次读文件、写文档、执行命令的闭环；
- docs/phase1-verification.md 存在；
- 项目级 command-log.jsonl 记录了 git status 和验证命令；
- Agent 运行日志记录了本次任务的 task_id、agent_role、输入摘要、输出摘要和产物路径。
```

## 5. Phase 2：多角色流程设计

### 5.1 角色职责

```text
PM 项目经理
- 接收用户目标；
- 拆分项目阶段；
- 维护状态；
- 推动评审；
- 汇总风险；
- 决定是否进入下一阶段。

PDM 产品经理
- 与用户澄清需求；
- 输出 PRD；
- 根据评审意见修订 PRD；
- 执行产品验收。

RES 调研员
- 做技术调研、竞品分析、可行性评估；
- 给 PDM / ARCH / DEV 提供背景资料。

ARCH 架构师
- 输出详细技术方案；
- 定义模块边界、接口、数据模型、部署方案；
- 识别技术风险。

DEV 开发工程师
- 参与技术方案；
- 编码实现；
- 自测、联调、冒烟测试；
- 修复 TEST / SEC / PDM 提出的问题。

TEST 测试工程师
- 输出测试用例；
- 输出 Markdown 与 Excel 测试清单；
- 执行测试；
- 记录缺陷并回归验证。

SEC 安全工程师
- 做安全审查；
- 执行安全测试 / SAST；
- 输出安全问题；
- 回归安全修复。
```

### 5.2 状态机

需求评审通过后，技术方案流和测试用例流并行启动，且双方在编写过程中不允许直接交流。

```text
CREATED
  -> REQUIREMENT_DRAFTING
  -> REQUIREMENT_REVIEW
  -> REQUIREMENT_APPROVED

REQUIREMENT_APPROVED 并行拆分：
  TECH_DESIGN_FLOW:
    TECH_DESIGN_DRAFTING
      -> TECH_DESIGN_REVIEW
      -> TECH_DESIGN_APPROVED

  TEST_CASE_FLOW:
    TEST_CASE_DRAFTING
      -> TEST_CASE_REVIEW
      -> TEST_CASE_APPROVED

并行汇合门禁：
  TECH_DESIGN_APPROVED
  AND TEST_CASE_APPROVED
  => DEVELOPMENT

DEVELOPMENT
  -> DEV_SELF_TEST
  -> TESTING_AND_SECURITY
  -> FIXING
  -> PRODUCT_ACCEPTANCE
  -> DONE
```

进入开发的门禁：

```text
TECH_DESIGN_APPROVED
AND
TEST_CASE_APPROVED
=> DEVELOPMENT
```

失败回流：

```text
REQUIREMENT_REVIEW fail -> REQUIREMENT_DRAFTING
TECH_DESIGN_REVIEW fail -> TECH_DESIGN_DRAFTING
TEST_CASE_REVIEW fail -> TEST_CASE_DRAFTING
DEV_SELF_TEST fail -> DEVELOPMENT
TESTING_AND_SECURITY fail -> FIXING -> TESTING_AND_SECURITY
PRODUCT_ACCEPTANCE fail -> FIXING -> DEV_SELF_TEST
```

### 5.3 技术方案与测试用例隔离规则

```text
需求评审通过后，并行启动两条互相隔离的产物流：

1. 技术方案流
   负责人：ARCH + DEV
   产物：详细技术方案、接口设计、数据库设计、开发拆分、自测思路
   有疑问：只能找 PDM 澄清需求

2. 测试用例流
   负责人：TEST
   产物：测试用例、测试清单 Markdown、测试清单 Excel、边界场景、验收验证点
   有疑问：只能找 PDM 澄清需求
```

隔离规则：

```text
- TECH_DESIGN_DRAFTING 和 TEST_CASE_DRAFTING 期间，ARCH/DEV 与 TEST 不允许直接交流；
- 双方不能互相参考未评审通过的草稿；
- 所有需求疑问统一提交给 PDM；
- PDM 的澄清要记录到 PRD 或需求澄清记录里；
- 如果 PDM 的澄清导致需求变化，需要判断是否回到 REQUIREMENT_REVIEW；
- 两条产物流分别评审；
- TECH_DESIGN_APPROVED 且 TEST_CASE_APPROVED 后，才允许进入 DEVELOPMENT。
```

## 6. 本地产物目录

Linux 云服务器上按项目隔离工作区和产物目录：

```text
workspaces/<project_id>/repo/      # 项目代码仓库，只允许对应 project_id 的任务进入该目录执行
projects/<project_id>/             # 项目管理产物、日志、评审记录
```

所有命令执行前必须绑定 `project_id` 与 `workspace_root`；命令工作目录必须位于对应项目的 `workspaces/<project_id>/repo/` 或 `projects/<project_id>/` 下，避免多项目互相污染。

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
    agent-runs/
    command-log.jsonl
```

测试 Markdown 是源文件，Excel 是交付文件。评审通过后同时生成 final.md 和 final.xlsx。

## 7. Hermes 边界与组件

PM Agent 是 Hermes 内部 Agent Runtime 中的一个角色 Agent，不是 Hermes 外部系统。

```text
用户
  -> 飞书
  -> Hermes Feishu Adapter
  -> Hermes Agent Runtime / PM Agent
  -> Hermes Workflow + Memory + State
  -> 其他角色 Agent / Claude Code CLI Executor
```

Hermes 组件：

```text
Hermes
├── Feishu Adapter
├── Agent Runtime
│   ├── PM Agent
│   ├── PDM Agent
│   ├── RES Agent
│   ├── ARCH Agent
│   ├── DEV Agent
│   ├── TEST Agent
│   └── SEC Agent
├── Workflow Engine
├── Memory Store
├── Artifact Store
├── Executor Adapter
│   └── Claude Code CLI
└── Audit Log
```

Hermes 负责：

```text
- 项目状态；
- Agent 角色；
- 任务队列；
- 上下文记忆；
- 评审门禁；
- 飞书消息；
- 运行日志；
- 权限策略。
```

Claude Code CLI 负责：

```text
- 读取项目代码；
- 修改代码；
- 生成文档；
- 执行测试/构建/lint；
- 输出具体产物。
```

## 8. 执行器运行模型

Phase 1 先采用“一次任务启动一次 Claude Code CLI 会话”的执行模型，不使用长驻 Claude Code CLI 进程。

```text
Task -> Executor Adapter -> 新建执行会话 -> Claude Code CLI -> 产物/日志 -> Task 状态更新
```

执行规则：

```text
- 每个 Task 绑定 project_id、task_id、agent_role、phase、workspace_root；
- Executor Adapter 为每次运行创建独立 run_id；
- Claude Code CLI 的工作目录必须在该项目 workspace_root 内；
- stdout、stderr、命令日志、产物路径都挂到 run_id；
- CLI 退出后，Hermes 根据 exit_code 和产物检查更新 Task.status；
- 进程中断时，running Task 标记为 interrupted，并保留 run_id 日志。
```

后续长期异步阶段可以再引入 tmux、systemd 或队列 worker 托管，但不得改变 Task、Artifact、Audit 的数据边界。

## 9. Memory Store 与 Artifact Store 边界

```text
Memory Store 存：
- 用户目标摘要；
- 需求澄清摘要；
- 评审结论；
- 决策原因；
- 跨任务上下文。

Artifact Store 存：
- 文件路径；
- 文件类型；
- 版本；
- draft/final 状态；
- 关联 phase/task/review。
```

大文档全文保存在本地文件系统，不直接塞进 Memory Store。Agent 需要上下文时，Hermes 先提供摘要和路径，再按需让 Claude Code CLI 读取具体文件。

## 10. 核心数据模型

### 10.1 Project

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

### 10.2 AgentRole

```text
AgentRole
- id
- role_code: PM/PDM/RES/ARCH/DEV/TEST/SEC
- model_base_url
- model_api_key_ref
- model_name
- permissions
- enabled
```

### 10.3 Task

```text
Task
- id
- project_id
- phase
- assignee_role
- status

- created_at
- started_at
- updated_at
- due_at
- completed_at

- next_handler_role
- next_handler_reason

- input_artifacts
- output_artifacts
- blocked_by
```

字段规则：

```text
created_at: 任务创建时间。
started_at: 当前这次任务实际开始处理时间。
updated_at: 最近一次状态、责任人、产物或问题更新的时间。
due_at: 当前任务截止时间。
completed_at: 当前任务完成时间。
next_handler_role: 下一步需要谁处理，可选 PM/PDM/RES/ARCH/DEV/TEST/SEC/USER/SYSTEM。
next_handler_reason: 为什么需要该角色处理。
```

示例：

```text
技术方案评审失败：
status = blocked
assignee_role = ARCH
next_handler_role = ARCH
next_handler_reason = waiting_tech_design_fix

测试发现缺陷：
status = failed
assignee_role = TEST
next_handler_role = DEV
next_handler_reason = waiting_dev_fix

需求不清：
status = waiting_user
assignee_role = PDM
next_handler_role = USER
next_handler_reason = waiting_requirement_clarification
```

### 10.4 Artifact

```text
Artifact
- id
- project_id
- phase
- type
- path
- version
- status: draft/final/archived
```

### 10.5 Review

```text
Review
- id
- project_id
- phase
- artifact_id
- participants
- status: pass/fail
- issues
```

### 10.6 Issue

```text
Issue
- id
- project_id
- source_role
- target_role
- phase
- severity
- status
- title
- description
- reproduce_steps
- expected_result
- actual_result
- linked_test_case
- linked_artifact
- created_at
- updated_at
- closed_at
```

### 10.7 Clarification

```text
Clarification
- id
- project_id
- from_role
- to_role=PDM
- question
- answer
- affects_requirement
- linked_artifact
```

### 10.8 Approval

```text
Approval
- id
- project_id
- phase
- artifact_id
- approver
- decision: approved/rejected/commented/paused
- comment
- created_at
```

## 11. 飞书交互设计

飞书只作为用户入口和通知审批层，不作为真实状态数据库。

用户只和 PM Agent 对话：

```text
用户 -> 飞书 -> Hermes Feishu Adapter -> Hermes Agent Runtime 中的 PM Agent
```

飞书消息类型：

```text
1. 项目创建消息
2. 需求澄清消息
3. 评审审批消息
4. 风险提醒消息
5. 进度日报/摘要
```

飞书卡片动作：

```text
通过
驳回
查看产物
补充说明
暂停项目
```

必须通知用户：

```text
- 需要需求澄清；
- 需求/技术方案/测试用例/验收评审；
- 项目将停止；
- 权限或高风险操作；
- 阶段明显超时；
- 多轮修复仍失败。
```

不打扰用户：

```text
- 普通 Agent 内部执行；
- 普通文件生成；
- 可自动修复的问题；
- 非阻塞日志。
```

## 12. 长期异步执行

Task.status：

```text
pending
running
waiting_review
waiting_user
blocked
failed
completed
cancelled
```

运行规则：

```text
- Task 创建时写 created_at；
- Agent 真正开始处理时写 started_at；
- 每次状态变化写 updated_at；
- 完成时写 completed_at；
- PM Agent 定期扫描 running / blocked / waiting_user；
- 超时任务通过飞书通知用户或提醒责任 Agent；
- 进程中断后根据 Task 状态和产物记录恢复。
```

恢复策略：

```text
pending：重新派发；
running 但进程不存在：标记 interrupted，PM 决定重试；
waiting_user：继续等待飞书审批；
failed：保留失败记录，创建修复任务；
completed：不重复执行，只进入下一状态。
```

## 13. 权限设计

Claude Code CLI 执行器需要分级权限，目的是在减少人工审批的同时避免高风险动作失控。

```text
L0 只读
- 读文件
- 搜索代码
- 查看 git diff/status
- 生成分析报告

L1 本地写入
- 写文档
- 修改代码
- 创建本地产物
- 运行非破坏性测试

L2 项目变更
- 安装依赖
- 数据库 migration
- 修改 CI 配置
- 修改权限配置

L3 外部影响
- push 代码
- 创建 PR
- 发飞书审批
- 部署
- 删除资源
```

自动化边界：

```text
可自动：
- L0
- 部分 L1

需要审批：
- L2
- 所有 L3
- 任何删除、覆盖、force、生产环境操作
```

### 13.1 Command Policy Engine

权限分级必须由 Command Policy Engine 强制执行，不能只依赖 Agent 自觉遵守。

```text
Command Policy Engine
- classify(command, cwd, project_id, agent_role) -> L0/L1/L2/L3
- decide(permission_level, task_context) -> allow / require_approval / deny
- redact(command, stdout, stderr) -> 脱敏后的日志内容
- record(policy_decision, risk_reason, approval_id)
```

执行流程：

```text
1. Executor Adapter 收到命令请求；
2. 校验 cwd 是否位于当前 project_id 的 workspace 或 projects 目录；
3. Command Policy Engine 分类命令权限等级；
4. L0 和允许范围内的 L1 直接执行；
5. L2、L3、删除、覆盖、force、生产环境操作进入审批；
6. 审批通过后记录 approval_id 再执行；
7. 审批拒绝则 Task 标记 blocked 或 failed，并记录原因。
```

拒绝规则：

```text
- 跨项目 workspace 执行命令：deny；
- 未绑定 project_id/task_id 的写操作：deny；
- 命令中包含明文 API Key、token、password：deny；
- 未经审批的 L2/L3：deny；
- 删除资源、force push、生产部署默认 require_approval，必要时 deny。
```

### 13.2 密钥与脱敏规则

```text
- model_api_key_ref 只保存密钥引用，不保存明文；
- API Key 不进入命令日志、产物目录、Agent prompt 摘要；
- stdout/stderr 入库或落盘前必须做敏感信息脱敏；
- 飞书消息不展示密钥、完整环境变量或完整认证头；
- 验证报告只能保存脱敏配置片段；
- 如果命令或输出疑似包含密钥，日志记录 redacted=true，并保留脱敏原因。
```

## 14. 日志与审计

Linux 云服务器需要同时支持全局日志和项目级日志，避免多项目混杂。

### 14.1 全局命令日志

```text
~/.claude/cccagents-logs/linux-commands.jsonl
```

用途：

```text
- 服务器级审计；
- 排查全局问题；
- 查看所有项目命令流水；
- 检查高风险命令。
```

### 14.2 项目级命令日志

```text
projects/<project_id>/08-logs/command-log.jsonl
```

用途：

```text
- 单项目复盘；
- 单项目恢复；
- 单项目交付归档；
- PM Agent 查询当前项目执行历史。
```

### 14.3 命令日志字段

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

说明：`linux-commands.jsonl` 是 Linux 命令流水账，用于留痕、审计、回放和排查问题；它不是执行命令的脚本。

### 14.4 其他审计日志

```text
Agent 运行日志
- agent_role
- task_id
- prompt摘要
- output摘要
- model
- token/耗时
- status

审批日志
- approver
- phase
- artifact
- decision
- comment
- time

状态流转日志
- project_id
- from_status
- to_status
- reason
- operator
- time
```

## 15. 测试、安全验证和产品验收

### 15.1 开发提测门禁

DEV 完成编码后，必须先完成：

```text
1. 自测
2. 联调测试
3. 冒烟测试
4. 代码变更说明
```

产物：

```text
04-development/dev-notes.md
04-development/self-test-report.md
04-development/integration-test-report.md
04-development/smoke-test-report.md
```

### 15.2 TEST 与 SEC 并行验证

开发提测后，TEST 和 SEC 并行执行。

TEST：

```text
- 根据 test-checklist.final.md / .xlsx 执行功能测试；
- 记录通过/失败；
- 输出 defect-log.md；
- 输出 test-execution-report.md；
- 回归验证 DEV 修复结果。
```

SEC：

```text
- 读取代码变更；
- 执行安全审查；
- 运行依赖漏洞扫描；
- 运行 secret 扫描；
- 检查命令注入、路径穿越、权限越权、日志泄密风险；
- 检查飞书 webhook 签名验证和回调权限；
- 输出 security-review.md；
- 输出 security-issues.md；
- 回归验证安全修复结果。
```

两条线都必须通过：

```text
TEST pass
AND
SEC pass
=> PRODUCT_ACCEPTANCE
```

### 15.3 测试清单字段结构

测试清单 Markdown 与 Excel 使用同一套字段，Markdown 作为源文件，Excel 作为交付文件。

```text
case_id
requirement_id
module
scenario
preconditions
steps
expected_result
priority
case_type: functional/boundary/exception/regression/security
execution_status: not_run/pass/fail/blocked
actual_result
defect_id
remark
```

生成规则：

```text
- test-checklist.*.md 必须能完整表达以上字段；
- test-checklist.*.xlsx 的列名与字段保持一致；
- 执行结果先回写 Markdown 源文件，再同步导出 Excel；
- final.md 与 final.xlsx 必须同源，不允许手工维护两套不一致内容。
```

### 15.4 产品验收

PDM 根据 PRD final 逐项验收：

```text
- 检查需求是否完整实现；
- 检查测试报告和安全报告；
- 输出 acceptance-report.md；
- 如果不通过，输出 acceptance-issues.md。
```

验收结果：

```text
pass -> DONE
fail -> FIXING -> DEV_SELF_TEST -> TESTING_AND_SECURITY -> PRODUCT_ACCEPTANCE
```

## 16. 项目关闭条件

项目只有同时满足以下条件才能完成：

```text
- PRD final 存在；
- tech-design final 存在；
- test-cases final.md 存在；
- test-checklist final.md 和 final.xlsx 存在；
- DEV 自测/联调/冒烟通过；
- TEST 验证通过；
- SEC 验证通过；
- PDM 验收通过；
- 所有高/中风险 Issue 关闭；
- phase-log 和 operation-log 完整。
```

## 17. 设计结论

推荐继续采用严格门禁型路线。第一优先级不是实现完整多 Agent 团队，而是在 Ubuntu 云服务器上证明：

```text
Claude Code CLI + OpenAI 兼容网关 + 本地日志审计
```

能形成一个可用、可控、可审计的最小执行器。

只有 Phase 1B 通过后，才值得继续投入 Phase 2 到 Phase 4。