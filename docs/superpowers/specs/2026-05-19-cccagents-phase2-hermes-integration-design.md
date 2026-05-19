# cccagents Phase 2 Hermes 集成重设计

日期：2026-05-19

## 1. 重设计结论

原 `2026-05-19-cccagents-phase2-workflow-design.md` 把 PM / PDM / RES / ARCH / DEV / TEST / SEC 设计成了本项目自研的本地 Python 工作流原型。这个方向不符合当前约束：这些角色应运行在实际 Hermes 中，而不是先自研一个替代 Hermes 的 Agent Runtime。

因此 Phase 2 改为：在 Linux 上安装并验证 `NousResearch/hermes-agent`，确认 Hermes 的真实配置、Gateway、Toolset、Skill、Subagent、Memory、Terminal 能力，然后把七类软件工程角色定义成 Hermes 可加载、可调度、可审计的运行单元；Claude Code CLI 只作为 Hermes 调用的代码/文档执行器。

## 2. Phase 2 新目标

Phase 2 的目标不是完整飞书接入，也不是长期异步运行，而是在 Linux 上证明以下闭环可行：

1. Hermes Agent 已安装并可启动。
2. Hermes 可使用 OpenAI 兼容模型配置。
3. Hermes 内部存在 PM 入口角色，并能按项目状态创建和分发任务。
4. PDM / RES / ARCH / DEV / TEST / SEC 以 Hermes 原生扩展点承载角色职责。
5. Hermes 可通过受控 tool 或 terminal backend 调用 Claude Code CLI。
6. 一个最小项目能完成：用户目标 -> PM 分派 -> DEV 通过 Claude Code CLI 写入一个项目内文件 -> PM 记录状态和产物。

Phase 2 通过后，再进入 Phase 3 飞书接入；Phase 3 只把用户入口换成飞书，不重新定义团队工作流。

## 3. Hermes 仓库依据

仓库：`https://github.com/NousResearch/hermes-agent`

已确认的 Hermes 能力：

- Python 项目，包名 `hermes-agent`。
- CLI 入口：`hermes`、`hermes-agent`、`hermes-acp`。
- README 提供安装命令：`curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash`。
- CLI 支持：`hermes setup`、`hermes model`、`hermes tools`、`hermes gateway`、`hermes doctor`。
- `pyproject.toml` 包含 `openai==2.24.0`。
- `pyproject.toml` optional extra 包含 `feishu = ["lark-oapi==1.5.3", "qrcode==7.4.2"]`。
- `gateway/platforms/feishu.py` 存在，读取 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`、`FEISHU_CONNECTION_MODE`、`FEISHU_ALLOWED_USERS`、`FEISHU_REQUIRE_MENTION` 等环境变量。
- `toolsets.py` 存在 `terminal`、`skills`、`subagent`、`hermes-feishu`、`hermes-gateway` 等 toolset。
- `tools/terminal_tool.py` 支持本地、Docker、SSH 等 terminal backend，并有危险命令审批逻辑。
- `hermes_cli/config.py` 说明配置文件在 `~/.hermes/config.yaml`，密钥在 `~/.hermes/.env`。
- Hermes config 支持 `model.provider`、`model.base_url`、辅助模型 `base_url/api_key/model` 等 OpenAI 兼容配置。

## 4. 新总体架构

```text
Linux Server
├── Hermes Runtime
│   ├── PM Agent Session
│   │   ├── project state monitor
│   │   ├── task router
│   │   ├── review gate controller
│   │   └── user-facing summaries
│   ├── Role Definitions
│   │   ├── PDM role skill/persona
│   │   ├── RES role skill/persona
│   │   ├── ARCH role skill/persona
│   │   ├── DEV role skill/persona
│   │   ├── TEST role skill/persona
│   │   └── SEC role skill/persona
│   ├── Hermes Memory / Skills / Subagents
│   ├── Hermes Gateway
│   │   └── Feishu platform adapter（Phase 3 启用）
│   └── Hermes Terminal / Custom Tool
│       └── Claude Code CLI Executor
├── cccagents Project Store
│   ├── workspaces/<project_id>/repo/
│   └── projects/<project_id>/...
└── Audit and Secret Boundary
    ├── command-log.jsonl
    ├── agent-runs/<run_id>/
    └── ~/.hermes/.env / secret refs
```

关键边界：

- Hermes 是 Agent 运行时、记忆、协调、Gateway、长期会话入口。
- cccagents 只保留项目目录、状态、审计、产物规范、Claude Code CLI 执行器封装。
- Claude Code CLI 不直接面对飞书用户，只由 Hermes 内部角色通过受控工具调用。
- 飞书用户只与 PM Agent 交互。

## 5. Hermes 内角色承载方式

Phase 2 不再自研 Agent Runtime。角色按以下优先级落地：

### 5.1 首选：Hermes Skill / Persona + Subagent Tool

每个角色定义为一个 Hermes skill/persona 文档，内容包括：职责、输入、输出、禁止事项、可调用工具、产物路径、评审格式。

PM 使用 Hermes 的 subagent 能力把任务派发给角色上下文。每次派发都带上：

```text
project_id
task_id
role
phase
input_artifacts
output_artifact_contract
allowed_toolsets
forbidden_actions
review_gate_expected_output
```

适用原因：Hermes 已有 `skills` 和 `subagent` toolset，最符合“角色运行在 Hermes 中”的约束。

### 5.2 备选：Hermes Profile / Session 级 system prompt

如果 Hermes 的 subagent 配置粒度不足，则用多个 profile/session 承载角色。PM 仍是唯一用户入口，通过 Hermes CLI 或内部命令触发不同 profile 的任务。

### 5.3 不采用：独立 Python Agent Runtime

旧 Phase 2 的本地 SQLite TaskStore / WorkflowEngine 可以保留为 cccagents 的状态与审计组件，但不能作为角色运行时。角色必须由 Hermes 会话、skill、profile 或 subagent 执行。

## 6. Claude Code CLI Executor 接入方式

Phase 2 采用最小安全接入：Hermes 通过 terminal/custom tool 调用本机 `claude` 命令。

执行环境：

```bash
ANTHROPIC_BASE_URL=<role.model_base_url>
ANTHROPIC_API_KEY=<resolved secret>
ANTHROPIC_MODEL=<role.model_name>
```

执行命令模式：

```bash
claude -p "<role task prompt>" --model "$ANTHROPIC_MODEL" --output-format text
```

执行前必须检查：

- `cwd` 位于 `workspaces/<project_id>/repo/` 或 `projects/<project_id>/`。
- 命令按 L0/L1/L2/L3 分类。
- L2/L3 进入 Hermes/PM 审批，不自动执行。
- prompt、stdout、stderr、命令日志写入前脱敏。
- 真实 API Key 不进入 `projects/<project_id>/`、飞书消息、Agent 摘要或 git。

## 7. Agent 模型配置

用户要求每个 Agent 使用 OpenAI 兼容配置：

```text
AgentModelConfig
- role_code: PM/PDM/RES/ARCH/DEV/TEST/SEC
- model_base_url
- model_api_key_ref
- model_name
- hermes_provider: custom 或 Hermes 实际支持的 provider id
- executor_type: hermes_role / claude_code_cli
- enabled
```

Phase 2 要验证两条模型路径：

1. Hermes 自身主模型是否可通过 `~/.hermes/config.yaml` + `~/.hermes/.env` 使用用户网关。
2. Claude Code CLI executor 是否继续使用 Phase 1 已验证的 `ANTHROPIC_BASE_URL`、`ANTHROPIC_API_KEY`、`ANTHROPIC_MODEL`。

Hermes 配置用户网关时，`model.base_url` 必须填写 OpenAI-compatible API base URL，而不是站点根地址。已验证正确值为：

```text
model.provider = custom
model.base_url = http://cccai.store/v1
model.default = qwen3.6-plus
```

`http://cccai.store` 会导致 Hermes custom provider 建连成功但 `hermes chat` 返回空响应；补上 `/v1` 后 `hermes chat --query "只回复 OK" --provider custom --model qwen3.6-plus --toolsets safe --quiet --max-turns 3` 返回 `OK`。

如果 Hermes 主模型不支持用户网关，但 Claude Code CLI 支持，Phase 2 不算完全通过；需要停在 Hermes 模型配置问题上解决，不进入飞书接入。

## 8. 项目生命周期保留规则

业务流程仍沿用已评审过的生命周期：

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

需求通过后并行：

```text
TECH_DESIGN_FLOW:
  TECH_DESIGN_DRAFTING -> TECH_DESIGN_REVIEW -> TECH_DESIGN_APPROVED

TEST_CASE_FLOW:
  TEST_CASE_DRAFTING -> TEST_CASE_REVIEW -> TEST_CASE_APPROVED
```

隔离规则保留：

- ARCH/DEV 负责技术方案流。
- TEST 负责测试用例流。
- 两条流草稿阶段不能互相交流，也不能读取对方未评审草稿。
- 需求问题都找 PDM。
- PDM 澄清必须进入 `00-meta/clarification-log.md`。
- 两条流都评审通过后才进入开发。

## 9. 本地产物目录保留规则

产物仍按 `project_id` 隔离：

```text
workspaces/<project_id>/repo/
projects/<project_id>/
  00-meta/
  01-requirements/
  02-tech-design/
  03-test-cases/
  04-development/
  05-quality-validation/
  06-security/
  07-acceptance/
  08-logs/
```

新增 Hermes 运行证据目录：

```text
projects/<project_id>/08-logs/hermes-runs/<run_id>/
  role.md
  prompt.md
  hermes-session.md
  claude-command.redacted.sh
  stdout.log
  stderr.log
  result.json
```

## 10. Phase 2 实施任务重排

旧 Phase 2 Task 8-10 暂停。新的 Phase 2 任务为：

1. 在 Linux 安装 Hermes Agent。
2. 运行 `hermes --help`、`hermes doctor`、`hermes model`、`hermes tools`，保存输出到 Linux 本地操作记录。
3. 定位 `~/.hermes/config.yaml` 和 `~/.hermes/.env`，记录配置结构，不记录真实密钥。
4. 配置 Hermes 使用用户 OpenAI 兼容网关，并跑通最小对话。
5. 验证 Hermes toolset 中 terminal、skills、subagent 是否可用。
6. 定义七类角色的 Hermes skill/persona 草案。
7. 定义 PM 分派任务给 DEV 的最小 Hermes prompt 协议。
8. 定义 Claude Code CLI executor wrapper，并复用 Phase 1 路径、权限、脱敏、日志组件。
9. 跑通最小闭环：PM 接收本地模拟用户目标，派发 DEV，DEV 调 Claude Code CLI 在项目目录写入文件，PM 汇总结果。
10. 保存 Phase 2 验收报告，明确是否进入 Phase 3 飞书。

## 11. Phase 2 验收标准

Phase 2 pass 条件：

- Linux 上 Hermes 安装完成。
- `hermes doctor` 无阻塞错误，或阻塞项有明确修复结论。
- Hermes 主模型能通过用户 OpenAI 兼容网关完成一次最小对话。
- Hermes 可使用 terminal 或 custom tool 调用 `claude`。
- PM / PDM / RES / ARCH / DEV / TEST / SEC 的角色定义以 Hermes 可加载形式保存。
- PM 能在 Hermes 内部触发一个 DEV 角色任务。
- DEV 能通过 Claude Code CLI 在 `workspaces/<project_id>/repo/` 或 `projects/<project_id>/` 内生成文件。
- 命令、输出、产物路径、状态变更都按 `project_id` 记录。
- 日志和产物中没有真实 API Key。

Phase 2 fail 条件：

- Hermes 无法安装或无法启动，且没有可接受修复方案。
- Hermes 不能使用用户 OpenAI 兼容模型配置。
- Hermes 无法承载角色定义或无法调度角色任务。
- Hermes 无法安全调用 Claude Code CLI。
- 需要引入用户已拒绝的协议适配层。

## 12. 对旧 Phase 2 代码的处理

已写的本地 Python 组件不删除，但降级为候选适配层：

- `phase2_models.py`：可保留为 cccagents 状态/产物 schema。
- `project_init.py`：可保留为项目目录初始化器。
- `artifact_store.py`：可保留为产物注册工具。
- `task_store.py`：是否继续使用取决于 Hermes 是否已有足够状态存储；不能绕过 Hermes 自建调度。
- `workflow.py` / `review_gate.py`：可作为 PM Agent 的流程规则库或测试 oracle。
- `agent_config.py`：可复用为 Claude Code CLI executor 环境变量映射。

原则：这些组件只能辅助 Hermes，不替代 Hermes。
