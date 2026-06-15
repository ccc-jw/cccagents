# cccagents 新项目启动指南

本文档用于在已经部署好的 cccagents Linux 服务器上启动一个新的工程项目。

## 1. 先定义 project_id

每个项目必须有唯一 `project_id`，后续 workspace、任务状态、产物、日志都按它隔离。

示例：

```text
my-new-project
```

命名建议：

- 使用小写字母、数字、短横线。
- 不要使用空格。
- 不要和已有项目重复。

## 2. 在 Linux 上创建项目目录

```bash
PROJECT_ID=my-new-project

mkdir -p /home/ubuntu/cccagents/workspaces/$PROJECT_ID/repo
mkdir -p /home/ubuntu/cccagents/projects/$PROJECT_ID/02-requirements
mkdir -p /home/ubuntu/cccagents/projects/$PROJECT_ID/03-architecture
mkdir -p /home/ubuntu/cccagents/projects/$PROJECT_ID/04-test-cases
mkdir -p /home/ubuntu/cccagents/projects/$PROJECT_ID/08-logs/hermes-runs
touch /home/ubuntu/cccagents/projects/$PROJECT_ID/08-logs/command-log.jsonl
```

如果项目已经有 Git 仓库，把代码 clone 到：

```text
/home/ubuntu/cccagents/workspaces/my-new-project/repo
```

## 3. 确认 cccagents 服务运行

```bash
systemctl is-active cccagents-hermes-gateway
systemctl is-active cccagents-pm-scheduler
```

期望输出都是：

```text
active
```

如果不是 active，先排查：

```bash
journalctl -u cccagents-hermes-gateway -n 100 --no-pager
journalctl -u cccagents-pm-scheduler -n 100 --no-pager
```

## 4. 通过飞书通知 PM 新建项目

在飞书里给 Bot 发送类似消息：

```text
新建项目 my-new-project。
目标：做一个 xxx 系统。
请先让 PDM 澄清需求，让 ARCH/DEV 准备技术方案，让 TEST 并行准备测试用例。
技术方案和测试用例要分开保存，Markdown 和 Excel 都要。
```

PM 后续应负责：

```text
用户 -> 飞书 -> PM
PM -> PDM 澄清需求
PM -> ARCH/DEV 写技术方案
PM -> TEST 写测试用例
PM -> 用户审批
PM -> DEV 执行
PM -> TEST 验证
PM -> 用户通知结果
```

## 5. 产物保存规则

代码 workspace：

```text
/home/ubuntu/cccagents/workspaces/<project_id>/repo
```

项目管理和产物目录：

```text
/home/ubuntu/cccagents/projects/<project_id>/02-requirements
/home/ubuntu/cccagents/projects/<project_id>/03-architecture
/home/ubuntu/cccagents/projects/<project_id>/04-test-cases
/home/ubuntu/cccagents/projects/<project_id>/08-logs
```

命令日志：

```text
/home/ubuntu/cccagents/projects/<project_id>/08-logs/command-log.jsonl
```

Hermes/Claude Code run evidence：

```text
/home/ubuntu/cccagents/projects/<project_id>/08-logs/hermes-runs/<run_id>/
```

## 6. 技术方案和测试用例规则

用户要求：

- 技术方案由 ARCH/DEV 负责。
- 测试用例由 TEST 负责。
- 技术方案和测试用例并行产出。
- 写方案期间，ARCH/DEV 和 TEST 不互相沟通中间内容。
- 有需求问题时，各自找 PDM 沟通需求。
- 本地产物必须分开保存。
- Markdown 和 Excel 都需要。

建议保存：

```text
03-architecture/technical-design.md
03-architecture/technical-design.xlsx
04-test-cases/test-cases.md
04-test-cases/test-cases.xlsx
```

## 7. 权限和审批注意事项

可以自动处理：

- 读文件、列目录、分析代码。
- 在项目 workspace 内写 harmless 文件。
- 运行本地测试。

需要 PM/用户审批：

- Git commit / push / PR。
- 删除文件或目录。
- 修改 systemd、服务器配置、外部服务。
- 生产部署。
- 服务重启或服务器 reboot。
- 跨项目写入。
- L2/L3 权限任务。

禁止默认使用：

```text
--dangerously-skip-permissions
```

DEV 执行任务建议使用窄授权：

```bash
claude -p "$PROMPT" --model gpt-5.5 --output-format text --allowedTools Read,Write
```

## 8. 飞书交互边界

- 用户只和 PM 对话。
- PM 是唯一用户入口。
- PM 是唯一用户通知出口。
- DEV/TEST/ARCH/PDM/RES/SEC 不直接接触飞书用户。
- PM 需要把其他 Agent 的结果汇总、脱敏后再通知用户。

## 9. 多项目隔离注意事项

- 每个项目必须有独立 `project_id`。
- 不要多个项目共用同一个 `workspaces/<project_id>/repo`。
- 同一项目写任务需要串行，避免并发写冲突。
- 不同项目可以并行调度，但仍受全局并发限制。
- cwd 必须在项目 workspace 或项目产物目录内。

## 10. 项目启动后建议做的第一轮检查

```bash
PROJECT_ID=my-new-project

test -d /home/ubuntu/cccagents/workspaces/$PROJECT_ID/repo
test -d /home/ubuntu/cccagents/projects/$PROJECT_ID/08-logs
test -f /home/ubuntu/cccagents/projects/$PROJECT_ID/08-logs/command-log.jsonl
systemctl is-active cccagents-hermes-gateway
systemctl is-active cccagents-pm-scheduler
```

期望：

- 项目目录存在。
- command log 文件存在。
- Gateway active。
- Scheduler active。

## 11. 相关总文档

新服务器部署：

```text
docs/final-new-server-deployment-guide.md
```

项目说明、操作指南和注意事项：

```text
docs/project-overview-and-operations-guide.md
```
