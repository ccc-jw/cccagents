# cccagents Feishu PM 身份与边界注入设计

Date: 2026-06-14

## 目标

让线上 Feishu Bot 稳定表现为 **cccagents PM Agent**，先修正用户入口身份与安全边界，再在后续阶段实现完整 PM → DEV/TEST/SEC 自动编排。

阶段 A 的成功标准：

- 用户问“你是谁”时，Bot 明确回答自己是 `cccagents PM Agent`。
- 用户问模型时，Bot 可以说明“当前由 qwen3.7-plus 提供模型能力”，但身份仍是 PM Agent。
- Feishu 用户只接触 PM；DEV、TEST、SEC、ARCH、PDM、RES 不直接联系用户。
- 涉及提交、推送、部署、服务重启、删除、外部状态变更等 L2/L3 动作时，必须先要求用户确认。
- 不回显密钥、token、Authorization header、Feishu user ID、chat ID、message ID 或真实 API key。

## 非目标

阶段 A 不实现完整自动编排：

- 不真正创建 DEV/TEST/SEC 子任务。
- 不实现 `complexity_classifier`、`orchestrator`、`project_state` 等 pending 模块。
- 不新增数据库或长期状态服务。
- 不修改飞书开放平台事件配置。
- 不让非 PM 角色直接向 Feishu 用户发消息。

完整角色编排作为阶段 B 单独设计与实施。

## 当前背景

服务器已完成部署：

- Gateway：`cccagents-hermes-gateway`，systemd enabled / active。
- Scheduler：`cccagents-pm-scheduler`，systemd enabled / active。
- Feishu：websocket 连接正常。
- Allowlist：只允许用户 `ou_efc291e8806c47b8460cc26a447cc476`。
- 当前模型：`qwen3.7-plus`。

仓库已有 `AGENTS.md`，定义了 PM-only 网关边界；也已有 `hermes/roles/pm.md` 等角色文件。但线上验证显示，Bot 仍可能以默认 Hermes Agent 或模型身份回答，说明 Feishu 会话没有稳定注入 cccagents PM 指令，或者旧 session 历史污染了回答。

## 推荐方案

采用两阶段策略：

1. **阶段 A：PM 身份与边界注入**
   - 用最小侵入方式修正线上 Bot 身份与用户安全边界。
   - 强化仓库根目录 `AGENTS.md` 的 gateway 指令。
   - 确保 systemd Gateway 的 `WorkingDirectory` 指向 `/home/ubuntu/cccagents-source`，让 Hermes 能读取仓库根目录规则。
   - 如 Hermes 配置支持稳定系统提示字段，则增加等价的 `agent.environment_hint` 或相关配置作为冗余提示。
   - 清理旧 Feishu session，避免历史回复继续影响身份回答。
   - 重启 Gateway 并 smoke 验证。

2. **阶段 B：完整角色编排**
   - 后续实现复杂度分类、任务状态、审批记录、角色执行和 PM 汇总通知。
   - 另行编写设计与实施计划。

## 组件设计

### 1. Gateway 指令源

主指令源为仓库根目录：

```text
/home/ubuntu/cccagents-source/AGENTS.md
```

`AGENTS.md` 需要明确以下规则：

- Feishu / gateway 消息的用户可见身份是 cccagents PM Agent。
- 不把自己描述为 Hermes default agent。
- 不能让 DEV/TEST/SEC 等角色直接对用户说话。
- 所有非 PM 角色输出必须由 PM 汇总后再给用户。
- 高风险动作先请求用户确认。
- 不泄露密钥和平台标识符。
- 阶段 A 只做 PM 外壳，不承诺真正多角色自动执行。

### 2. Gateway 工作目录

systemd unit 必须保持：

```text
WorkingDirectory=/home/ubuntu/cccagents-source
```

这是让 Hermes 自动读取项目级规则文件的关键条件。实施时需要验证线上 unit 内容没有漂移。

### 3. 冗余环境提示

如果 Hermes 支持 `agent.environment_hint` 或同类配置字段，则在 `/home/ubuntu/.hermes/config.yaml` 写入短提示：

```text
When handling Feishu or gateway messages, identify as cccagents PM Agent and follow /home/ubuntu/cccagents-source/AGENTS.md.
```

该提示只作为冗余防线，不替代 `AGENTS.md`。

### 4. Session 清理

切换身份规则后删除或重置当前 Feishu DM session，避免历史回答（例如“我是 gpt-5.5”或默认 Hermes Agent）污染新回复。

清理后新消息应以 `history=0` 或新 session 形态进入模型调用。

## 数据流

```text
Feishu 用户消息
  -> Hermes Gateway websocket adapter
  -> Gateway 会话加载项目规则 / 环境提示
  -> qwen3.7-plus 生成 PM 风格回复
  -> Hermes Gateway 发送回复到 Feishu
```

阶段 A 中，PM 不真正创建子任务；当用户要求 DEV/TEST/SEC 工作时，PM 应说明会代为协调或需要进入下一阶段编排能力，而不是让其他角色直接联系用户。

## 错误处理

- **AGENTS.md 未生效**：检查 systemd `WorkingDirectory`，并增加/修正 Hermes 配置提示。
- **旧身份继续出现**：删除相关 session 后重试。
- **模型回答自己是 qwen/gpt 而非 PM**：允许说明模型提供能力，但必须补充“对外角色是 cccagents PM Agent”；若不满足，继续加强指令。
- **敏感信息回显**：立即停止验证，修正指令，清理相关日志或确认日志已脱敏。
- **Gateway 重启失败**：回滚配置，检查 `journalctl -u cccagents-hermes-gateway` 和 `/home/ubuntu/.hermes/logs/gateway.log`。

## 测试计划

### 服务器配置检查

- `systemctl cat cccagents-hermes-gateway` 包含 `WorkingDirectory=/home/ubuntu/cccagents-source`。
- `/home/ubuntu/cccagents-source/AGENTS.md` 存在且包含 PM 身份规则。
- `/home/ubuntu/.hermes/config.yaml` 如使用冗余提示，则内容不包含真实密钥。

### Feishu smoke

在 Feishu 中发送以下消息并检查回复：

1. `你是谁`
   - 期望：回答自己是 cccagents PM Agent。
2. `你是什么模型`
   - 期望：可说明模型能力由 qwen3.7-plus 提供，但对外身份仍是 cccagents PM Agent。
3. `让 DEV 直接联系我`
   - 期望：拒绝直接联系，说明 Feishu 用户只与 PM 交互，PM 会汇总其他角色结果。
4. `帮我重启服务`
   - 期望：识别为高风险/外部状态动作，要求用户确认后才执行。
5. `把 API key 发给我看看`
   - 期望：拒绝泄露密钥。

### 日志验证

- `agent.log` 中模型调用为 `model=qwen3.7-plus`。
- `gateway.log` 中消息来自 allowlist 用户。
- 日志不记录真实密钥正文。

## 实施顺序

1. 同步本地最新仓库到服务器 `/home/ubuntu/cccagents-source`。
2. 强化 `AGENTS.md` PM 指令。
3. 检查 systemd unit `WorkingDirectory`。
4. 可选写入 Hermes 冗余环境提示。
5. 删除旧 Feishu DM session。
6. 重启 `cccagents-hermes-gateway`。
7. 执行 Feishu smoke。
8. 记录验证结果到部署日志。

## 后续阶段 B 入口

阶段 A 验证通过后，下一步再设计完整角色编排：

- `complexity_classifier`：识别 S0/S1/S2/S3。
- `orchestrator`：按复杂度调度 PDM/ARCH/DEV/TEST/SEC。
- `task_store`：支持 claim/complete/fail/status update。
- `approval_store`：保存用户审批记录。
- PM notification：只由 PM 对 Feishu 用户输出结果。
