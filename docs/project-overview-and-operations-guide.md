# cccagents 项目说明、操作指南与注意事项

## 1. 项目定位

cccagents 是一个面向长周期软件工程任务的多 Agent 协作系统验证项目。

目标是把用户从必须守在 Mac 前审批 Claude Code CLI 的工作方式，扩展为：

```text
用户 -> 飞书 -> Hermes PM Agent -> Hermes 多角色团队 -> Claude Code CLI 执行器 -> 项目产物/证据 -> PM -> 飞书用户
```

核心思想：

- 用户只通过飞书和 PM Agent 沟通。
- Hermes 负责角色协作、记忆、状态、协调、恢复和通知。
- Claude Code CLI 负责代码、文档、测试等具体工程执行。
- Linux 服务器负责长期运行和保存证据。
- 每个项目用 `project_id` 隔离 workspace、产物、任务状态和日志。

## 2. 当前完成状态

当前仓库已经完成 Phase 1 到 Phase 4 的验证。

| Phase | 内容 | 状态 |
| --- | --- | --- |
| Phase 1 | Linux 上跑通 Claude Code CLI，验证 OpenAI-compatible 网关 | 完成 |
| Phase 2 | Hermes 安装、模型配置、角色流程、本地 PM -> DEV 闭环 | 完成 |
| Phase 3 | 飞书合约、本地安全模拟、PM-only 边界 | 完成 |
| Phase 3.5 | 真实飞书接入，Feishu -> PM -> DEV -> PM -> Feishu 最小闭环 | 完成 |
| Phase 4 | systemd 服务化、allowlist、重启恢复、多项目调度、PM 通知 | 完成 |

最终验收记录：

```text
docs/phase4/phase4-acceptance.md
```

新服务器部署手册：

```text
docs/final-new-server-deployment-guide.md
```

## 3. 主要组件

### 3.1 Claude Code CLI

用途：执行具体工程任务，例如读写文件、改代码、跑测试、写文档。

关键规则：

- 必须直接支持 OpenAI-compatible 网关。
- 不接受协议适配层。
- 默认模型：`qwen3.6-plus`。
- 默认使用窄授权，不使用 `--dangerously-skip-permissions`。

示例：

```bash
claude -p "$PROMPT" --model qwen3.6-plus --output-format text --allowedTools Read,Write
```

### 3.2 Hermes Agent

用途：承载多 Agent 团队和用户入口。

当前规划角色：

| 角色 | 说明 |
| --- | --- |
| PM | 项目经理，唯一飞书入口和用户通知出口 |
| PDM | 产品经理，负责需求澄清 |
| RES | 调研员，负责资料和方案调研 |
| ARCH | 架构师，负责技术方案 |
| DEV | 开发工程师，负责实现 |
| TEST | 测试工程师，负责测试用例和验证 |
| SEC | 安全工程师，负责安全审查 |

重要边界：

- 用户消息只能进入 PM。
- DEV/TEST/ARCH 等角色不能直接接触飞书用户。
- PM 汇总和通知用户。

### 3.3 Feishu/Lark Bot

用途：用户与 PM Agent 的唯一交互通道。

已验证方式：Hermes Gateway Feishu websocket mode。

生产规则：

```text
GATEWAY_ALLOW_ALL_USERS=false
FEISHU_ALLOWED_USERS=<真实 ou_... 用户 id>
```

不允许长期使用：

```text
GATEWAY_ALLOW_ALL_USERS=true
```

这个配置只能用于首次 smoke 获取用户 id。

### 3.4 PM Scheduler

用途：长期异步运行的调度和恢复入口。

当前已验证能力：

- systemd 长期运行。
- 服务重启后仍可运行。
- stale running task 可被恢复逻辑标记为 interrupted。
- 安全 interrupted task 可回到 pending 等待重试。
- 多项目调度判断。
- 同项目写锁判断。
- PM 通知格式化和脱敏。

## 4. 服务器目录说明

默认路径：

```text
/home/ubuntu/cccagents-source
/home/ubuntu/cccagents
/home/ubuntu/.hermes/.env
/home/ubuntu/.hermes/config.yaml
```

含义：

| 路径 | 用途 |
| --- | --- |
| `/home/ubuntu/cccagents-source` | 仓库源码 |
| `/home/ubuntu/cccagents/workspaces/<project_id>/repo` | 每个项目的代码 workspace |
| `/home/ubuntu/cccagents/projects/<project_id>` | 每个项目的任务状态、产物、日志 |
| `/home/ubuntu/cccagents/projects/<project_id>/08-logs` | 项目日志 |
| `/home/ubuntu/.hermes/.env` | Linux 本地真实密钥，只能留在服务器 |
| `/home/ubuntu/.hermes/config.yaml` | Hermes 配置 |

## 5. 日常操作流程

### 5.1 启动或检查服务

```bash
systemctl is-enabled cccagents-hermes-gateway
systemctl is-active cccagents-hermes-gateway
systemctl is-enabled cccagents-pm-scheduler
systemctl is-active cccagents-pm-scheduler
```

期望：

```text
enabled
active
enabled
active
```

查看日志：

```bash
journalctl -u cccagents-hermes-gateway -n 100 --no-pager
journalctl -u cccagents-pm-scheduler -n 100 --no-pager
```

重启服务：

```bash
sudo systemctl restart cccagents-hermes-gateway
sudo systemctl restart cccagents-pm-scheduler
```

### 5.2 收集 Phase 4 证据

```bash
cd /home/ubuntu/cccagents-source
./scripts/phase4/collect_phase4_evidence.sh docs/phase4/linux-ops
```

输出：

```text
docs/phase4/linux-ops/service-install.log
docs/phase4/linux-ops/allowlist-check.log
docs/phase4/linux-ops/restart-recovery.log
docs/phase4/linux-ops/multi-project-scheduler.log
docs/phase4/linux-ops/pm-notification.log
```

### 5.3 本地测试

```bash
cd /home/ubuntu/cccagents-source
PYTHONPATH=src .venv/bin/pytest -q tests
```

当前最终验证结果是：

```text
71 passed
```

### 5.4 密钥扫描

```bash
grep -R "FEISHU_APP_SECRET=.*[A-Za-z0-9]\|FEISHU_VERIFICATION_TOKEN=.*[A-Za-z0-9]\|FEISHU_ENCRYPT_KEY=.*[A-Za-z0-9]\|sk-\|ANTHROPIC_API_KEY=.*[A-Za-z0-9]" docs src tests hermes scripts || true
```

允许命中：

- `[REDACTED]`
- `<redacted-api-key>`
- 测试样例
- 计划文档示例

不允许命中：

- 真实 API Key
- 真实 Feishu App Secret
- 真实 Verification Token
- 真实 Encrypt Key
- 真实 Authorization/Bearer Token

## 6. 新项目操作指南

### 6.1 创建项目隔离目录

为每个新项目分配一个 `project_id`。

```bash
PROJECT_ID=<project_id>
mkdir -p /home/ubuntu/cccagents/workspaces/$PROJECT_ID/repo
mkdir -p /home/ubuntu/cccagents/projects/$PROJECT_ID/08-logs/hermes-runs
```

### 6.2 保存项目命令日志

每个项目的命令日志建议保存在：

```text
/home/ubuntu/cccagents/projects/<project_id>/08-logs/command-log.jsonl
```

### 6.3 技术方案和测试用例分离

用户明确要求：

- 技术方案由 ARCH/DEV 负责。
- 测试用例由 TEST 负责。
- 两者并行进行。
- 写方案和写测试用例期间双方不互相交流。
- 有需求问题时，各自找 PDM 沟通。
- 本地产物必须分开保存。
- Markdown 和 Excel 都需要。

建议目录：

```text
projects/<project_id>/02-requirements/
projects/<project_id>/03-architecture/
projects/<project_id>/04-test-cases/
projects/<project_id>/08-logs/
```

## 7. 权限和审批注意事项

建议权限等级：

| 等级 | 含义 | 是否可自动 |
| --- | --- | --- |
| L0 | 只读、分析、列目录、读文件 | 可以 |
| L1 | 项目内写文件、跑本地测试 | 可按策略自动 |
| L2 | 项目级变更、提交、服务重启等 | 需要 PM/用户审批 |
| L3 | 外部系统、共享状态、删除、部署、force 操作 | 必须审批 |

危险操作必须显式确认：

- 删除文件或目录
- `rm -rf`
- `git reset --hard`
- `git push --force`
- 修改生产 systemd/服务配置
- 服务器 reboot
- 外部系统发布、PR、Issue、消息发送

## 8. 飞书使用注意事项

1. Feishu Bot 是用户入口，不是所有 Agent 的入口。
2. 用户只和 PM Agent 对话。
3. PM 负责把任务拆给其他角色。
4. DEV/TEST/ARCH 不直接给用户发飞书消息。
5. PM 通知用户前必须脱敏。
6. Feishu allowlist 必须开启。
7. 如果换用户或换 Bot，需要重新设置 `FEISHU_ALLOWED_USERS`。

首次接入新 Bot 时：

1. 设置真实 Feishu secrets 到 `/home/ubuntu/.hermes/.env`。
2. 如不知道用户 id，可短暂设置 `GATEWAY_ALLOW_ALL_USERS=true`。
3. 发消息给 Bot，观察 `ou_...`。
4. 立刻改回 `GATEWAY_ALLOW_ALL_USERS=false`。
5. 设置 `FEISHU_ALLOWED_USERS=<observed-ou-id>`。
6. 重启 Gateway。
7. 保存脱敏证据。

## 9. Hermes/OpenAI-compatible 注意事项

Hermes 的 base URL 必须使用 OpenAI-compatible API base：

```text
http://cccai.store/v1
```

不要只写：

```text
http://cccai.store
```

否则可能出现 `hermes chat` 空响应。

验证命令：

```bash
hermes chat --query "只回复 OK" --provider custom --model qwen3.6-plus --toolsets safe --quiet --max-turns 3
```

期望：

```text
OK
```

## 10. systemd 注意事项

Gateway unit 必须包含：

```text
ExecStart=/home/ubuntu/.local/bin/hermes gateway run --accept-hooks --replace
```

`--replace` 是必要的，因为旧 foreground gateway 或残留 PID 可能导致服务启动失败。

Scheduler unit 必须包含：

```text
Environment=PYTHONPATH=/home/ubuntu/cccagents-source/src
ExecStart=/home/ubuntu/cccagents-source/.venv/bin/python -m cccagents.pm_scheduler
```

否则可能报：

```text
ModuleNotFoundError: No module named 'cccagents'
```

## 11. 故障排查

### 11.1 Gateway 启动失败，提示已有 gateway 运行

检查 unit 是否包含：

```text
--replace
```

然后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl restart cccagents-hermes-gateway
journalctl -u cccagents-hermes-gateway -n 100 --no-pager
```

### 11.2 Scheduler 启动失败，找不到 cccagents

检查 unit 是否包含：

```text
Environment=PYTHONPATH=/home/ubuntu/cccagents-source/src
ExecStart=/home/ubuntu/cccagents-source/.venv/bin/python -m cccagents.pm_scheduler
```

然后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl restart cccagents-pm-scheduler
journalctl -u cccagents-pm-scheduler -n 100 --no-pager
```

### 11.3 测试缺 openpyxl

执行：

```bash
cd /home/ubuntu/cccagents-source
.venv/bin/python -m pip install -r requirements-dev.txt
PYTHONPATH=src .venv/bin/pytest -q tests
```

### 11.4 Linux 没有 ensurepip / venv

执行：

```bash
sudo apt update
sudo apt install -y python3-venv
python3 -m venv .venv
```

### 11.5 GitHub push 超时

本地提交不受影响。网络稳定后重试：

```bash
git push origin main
```

## 12. 文档索引

最重要的文档：

```text
docs/final-new-server-deployment-guide.md
```

项目说明和操作注意事项：

```text
docs/project-overview-and-operations-guide.md
```

阶段验收：

```text
docs/phase1/phase1b-capability-report.md
docs/phase2/phase2-acceptance.md
docs/phase3/phase3-acceptance.md
docs/phase3/phase35-acceptance.md
docs/phase4/phase4-acceptance.md
```

关键设计与计划：

```text
docs/superpowers/specs/2026-05-19-cccagents-design.md
docs/superpowers/specs/2026-05-20-cccagents-phase4-long-running-async-design.md
docs/superpowers/plans/2026-05-20-cccagents-phase4-long-running-async-plan.md
```

## 13. 最终注意事项

- 不要把真实密钥提交到 Git。
- 不要长期保留 `GATEWAY_ALLOW_ALL_USERS=true`。
- 不要让用户绕过 PM 直接访问 DEV/TEST/ARCH。
- 不要在默认执行器里使用 `--dangerously-skip-permissions`。
- 不要把多个项目写入同一个 workspace。
- 不要在未确认前执行 reboot、删除、force push、生产部署等高风险操作。
- 每个阶段、每次 Linux 操作、每次 smoke 都要保存本地证据。
- 如果要部署到新服务器，优先按 `docs/final-new-server-deployment-guide.md` 执行。
