# cccagents 新服务器部署最终操作文档

> 本文档用于把本项目按 Phase 1-4 的最终验证路径部署到一台新的 Linux 服务器。真实密钥只允许保存在 Linux 主机本地，仓库和操作证据只保存脱敏内容。

## 1. 目标架构

部署完成后，新服务器上应具备：

- Claude Code CLI：作为每个工程任务的一次性执行器。
- Hermes Agent：承载 PM/PDM/RES/ARCH/DEV/TEST/SEC 等角色协作。
- Feishu/Lark Bot：用户唯一入口，只与 PM Agent 交互。
- systemd 服务：长期运行 Hermes Gateway 和 PM Scheduler。
- 项目隔离目录：支持多个 `project_id` 并行运行。
- 本地证据目录：每个 Phase 和 Linux 操作都保存到本地文档与日志。

## 2. 服务器约定

默认用户与路径：

```text
RUN_USER=ubuntu
PROJECT_SOURCE=/home/ubuntu/cccagents-source
PROJECT_ROOT=/home/ubuntu/cccagents
HERMES_ENV=/home/ubuntu/.hermes/.env
HERMES_CONFIG=/home/ubuntu/.hermes/config.yaml
```

项目目录结构：

```text
/home/ubuntu/cccagents-source/              # 本仓库源码
/home/ubuntu/cccagents/workspaces/<id>/repo # 每个项目的 workspace
/home/ubuntu/cccagents/projects/<id>/       # 每个项目的任务、产物、日志
/home/ubuntu/cccagents/projects/<id>/08-logs/command-log.jsonl
/home/ubuntu/cccagents/projects/<id>/08-logs/hermes-runs/<run_id>/
```

## 3. 安全规则

1. 不要把真实密钥写入仓库、Markdown、日志、stdout/stderr 证据或 Feishu 消息。
2. 真实值只放在 Linux：`/home/ubuntu/.hermes/.env`。
3. 仓库中只允许出现：`[REDACTED]`、`<redacted-api-key>`、变量名或测试样例。
4. Phase 4/生产环境必须使用 Feishu allowlist：
   ```text
   GATEWAY_ALLOW_ALL_USERS=false
   FEISHU_ALLOWED_USERS=<真实 ou_... 用户 id，不能提交到仓库>
   ```
5. Claude Code CLI 默认不要使用 `--dangerously-skip-permissions`。
6. DEV 最小写入任务使用窄授权，例如：
   ```bash
   claude -p "$PROMPT" --model qwen3.6-plus --output-format text --allowedTools Read,Write
   ```
7. Feishu 用户消息只能进入 PM；不能直接路由到 PDM/RES/ARCH/DEV/TEST/SEC。

## 4. 准备系统依赖

```bash
lsb_release -a
sudo apt update
sudo apt install -y curl git build-essential python3 python3-venv python3-pip sshpass
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
node -v
npm -v
python3 --version
```

## 5. 部署源码

```bash
cd /home/ubuntu
git clone https://github.com/ccc-jw/cccagents.git cccagents-source
cd /home/ubuntu/cccagents-source
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
PYTHONPATH=src .venv/bin/pytest -q tests
```

通过标准：测试全部通过。

## 6. 安装 Claude Code CLI

```bash
sudo npm install -g @anthropic-ai/claude-code
claude --version
claude --help
```

配置 OpenAI-compatible 网关环境变量。把真实 key 只写入 Linux shell 或 `/home/ubuntu/.hermes/.env`，不要写入仓库：

```bash
export ANTHROPIC_BASE_URL="http://cccai.store"
export ANTHROPIC_API_KEY="<redacted-api-key>"
export ANTHROPIC_MODEL="qwen3.6-plus"
```

Phase 1 门禁：必须是 Claude Code CLI 本体直接支持 OpenAI-compatible 网关；不接受协议适配层。如果本门禁失败，项目停止。

最小验证：

```bash
claude -p "只回复 OK" --model qwen3.6-plus --output-format text --allowedTools Read
```

期望输出包含：

```text
OK
```

## 7. 安装 Hermes Agent

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
/home/ubuntu/.local/bin/hermes --help
/home/ubuntu/.local/bin/hermes doctor
```

Hermes OpenAI-compatible 配置重点：base URL 必须带 `/v1`。

```text
model.provider = custom
model.base_url = http://cccai.store/v1
model.default = qwen3.6-plus
```

验证 Hermes 模型：

```bash
hermes chat --query "只回复 OK" --provider custom --model qwen3.6-plus --toolsets safe --quiet --max-turns 3
```

期望输出：

```text
OK
```

如果 `http://cccai.store` 空响应，改为 `http://cccai.store/v1` 后重试。

## 8. 配置 Linux secret 文件

创建 Hermes secret/config 目录：

```bash
mkdir -p /home/ubuntu/.hermes
chmod 700 /home/ubuntu/.hermes
```

创建 `/home/ubuntu/.hermes/.env`：

```bash
cat > /home/ubuntu/.hermes/.env <<'EOF'
ANTHROPIC_BASE_URL=http://cccai.store
ANTHROPIC_API_KEY=<redacted-api-key>
ANTHROPIC_MODEL=qwen3.6-plus

FEISHU_APP_ID=<real-app-id>
FEISHU_APP_SECRET=<redacted-app-secret>
FEISHU_VERIFICATION_TOKEN=<redacted-verification-token>
FEISHU_ENCRYPT_KEY=<redacted-encrypt-key>

GATEWAY_ALLOW_ALL_USERS=false
FEISHU_ALLOWED_USERS=<real-ou-user-id>
EOF
chmod 600 /home/ubuntu/.hermes/.env
```

注意：第一次真实 Feishu smoke 如果还不知道 `ou_...` 用户 id，可以临时用 `GATEWAY_ALLOW_ALL_USERS=true` 观察一次用户 id；拿到 id 后必须改回：

```text
GATEWAY_ALLOW_ALL_USERS=false
FEISHU_ALLOWED_USERS=<observed-ou-user-id>
```

## 9. 配置 Feishu Bot

需要准备：

- App ID
- App Secret
- Verification Token
- Encrypt Key

本次已验证 Hermes Gateway 使用 Feishu websocket mode 可用，不强制需要 HTTPS webhook。

预留 HTTPS webhook 地址形状：

```text
https://feishu.cccai.store/webhook/feishu
```

若使用 DNS/反代模式，DNS 应指向 Linux 服务器 IP。

Feishu smoke 顺序：

1. 启动 Hermes Gateway。
2. 给 Bot 发送 `ping pm`。
3. 验证消息只进入 PM。
4. PM 回复 Feishu 用户。
5. 再发送一个最小 DEV 任务：创建 harmless 文件。
6. PM 调 DEV，DEV 完成后回 PM，PM 通知 Feishu 用户。

## 10. 启动 systemd 服务

生成 unit：

```bash
cd /home/ubuntu/cccagents-source
PROJECT_SOURCE=/home/ubuntu/cccagents-source \
PROJECT_ROOT=/home/ubuntu/cccagents \
HERMES_ENV=/home/ubuntu/.hermes/.env \
RUN_USER=ubuntu \
UNIT_DIR=/tmp/cccagents-systemd-units \
./scripts/phase4/install_phase4_services.sh
```

检查 `/tmp/cccagents-systemd-units/` 中两个文件：

```text
cccagents-hermes-gateway.service
cccagents-pm-scheduler.service
```

关键内容应包括：

```text
ExecStart=/home/ubuntu/.local/bin/hermes gateway run --accept-hooks --replace
Environment=PYTHONPATH=/home/ubuntu/cccagents-source/src
ExecStart=/home/ubuntu/cccagents-source/.venv/bin/python -m cccagents.pm_scheduler
Restart=always
```

安装并启动：

```bash
sudo cp /tmp/cccagents-systemd-units/cccagents-hermes-gateway.service /etc/systemd/system/
sudo cp /tmp/cccagents-systemd-units/cccagents-pm-scheduler.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cccagents-hermes-gateway
sudo systemctl enable --now cccagents-pm-scheduler
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

常见故障：

- Gateway 报已有 PID：unit 必须带 `--replace`。
- Scheduler 报 `No module named cccagents`：unit 必须设置 `PYTHONPATH=/home/ubuntu/cccagents-source/src`，并使用仓库 `.venv/bin/python`。

## 11. Phase 4 smoke 验证

### 11.1 重启恢复 smoke

创建 stale running task，并执行恢复：

```bash
cd /home/ubuntu/cccagents-source
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from pathlib import Path
from cccagents.pm_scheduler import reconcile_project_after_restart
project_dir = Path("/home/ubuntu/cccagents/projects/phase4-recovery-smoke")
project_dir.mkdir(parents=True, exist_ok=True)
(project_dir / "tasks.json").write_text(json.dumps([{
  "id":"task_restart_1",
  "project_id":"phase4-recovery-smoke",
  "phase":"DEVELOPMENT",
  "flow":"main",
  "assignee_role":"DEV",
  "title":"Restart smoke",
  "description":"Recover stale running task after service restart",
  "created_at":"2026-05-20T00:00:00Z",
  "status":"running"
}], indent=2) + "\n")
(project_dir / "run-records.json").write_text(json.dumps([{
  "project_id":"phase4-recovery-smoke",
  "task_id":"task_restart_1",
  "run_id":"run_restart_1",
  "status":"running",
  "permission_level":"L1",
  "idempotent":False,
  "process_alive":False,
  "heartbeat_stale":True,
  "destructive":False,
  "external":False,
  "same_project_write_lock":False
}], indent=2) + "\n")
print(reconcile_project_after_restart(project_dir)[0])
PY
sudo systemctl restart cccagents-pm-scheduler
systemctl is-active cccagents-pm-scheduler
```

期望恢复证据：

```text
{"action": "mark_interrupted", "next_status": "interrupted", "notify_pm": true, "previous_status": "running", "task_id": "task_restart_1"}
```

### 11.2 多项目调度 smoke

```bash
cd /home/ubuntu/cccagents-source
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from pathlib import Path
from cccagents.scheduler import DispatchRequest, ProjectLockState, decide_dispatch
root = Path("/home/ubuntu/cccagents")
log_path = root / "projects" / "phase4-scheduler-smoke" / "08-logs" / "multi-project-scheduler.jsonl"
log_path.parent.mkdir(parents=True, exist_ok=True)
for project_id in ["project_a", "project_b"]:
    (root / "workspaces" / project_id / "repo").mkdir(parents=True, exist_ok=True)
scenarios = [
    ("project_a_first_write", DispatchRequest("project_a", root / "workspaces" / "project_a" / "repo", root, "L1", True), ProjectLockState(set(), 0, 2)),
    ("project_a_second_write_blocked", DispatchRequest("project_a", root / "workspaces" / "project_a" / "repo", root, "L1", True), ProjectLockState({"project_a"}, 1, 2)),
    ("project_b_write_allowed", DispatchRequest("project_b", root / "workspaces" / "project_b" / "repo", root, "L1", True), ProjectLockState({"project_a"}, 1, 2)),
    ("project_a_outside_cwd_blocked", DispatchRequest("project_a", Path("/tmp/outside"), root, "L1", True), ProjectLockState(set(), 0, 2)),
]
with log_path.open("w") as handle:
    for name, request, locks in scenarios:
        decision = decide_dispatch(request, locks)
        handle.write(json.dumps({"scenario": name, "allowed": decision.allowed, "reason": decision.reason}, sort_keys=True) + "\n")
print(log_path.read_text())
PY
```

期望包含：

```text
project_a_first_write dispatch_allowed
project_a_second_write_blocked same_project_write_lock
project_b_write_allowed dispatch_allowed
project_a_outside_cwd_blocked cwd_outside_project
```

### 11.3 PM 通知 smoke

```bash
cd /home/ubuntu/cccagents-source
PYTHONPATH=src .venv/bin/python - <<'PY'
from pathlib import Path
from cccagents.pm_notifications import PMNotification, format_pm_notification
log_path = Path("/home/ubuntu/cccagents/projects/phase4-notification-smoke/08-logs/pm-notification.log")
log_path.parent.mkdir(parents=True, exist_ok=True)
notifications = [
    PMNotification("phase4-notification-smoke", "progress_summary", "Phase 4 progress", "Scheduler smoke running with ANTHROPIC_API_KEY=secret-value", "none", "task_progress_1"),
    PMNotification("phase4-notification-smoke", "restart_recovery", "Task interrupted after restart", "task_restart_1 requires retry decision", "approve_retry_or_stop", "task_restart_1"),
    PMNotification("phase4-notification-smoke", "approval_request", "Approval required", "L2 project change requires PM approval", "approve_or_reject", "task_approval_1"),
    PMNotification("phase4-notification-smoke", "completion_notice", "Phase 4 smoke complete", "PM notification smoke completed", "none", None),
]
log_path.write_text("\n---\n".join(format_pm_notification(item) for item in notifications) + "\n")
print(log_path.read_text())
PY
```

期望：

- 覆盖 `progress_summary`、`restart_recovery`、`approval_request`、`completion_notice`。
- `ANTHROPIC_API_KEY=secret-value` 被脱敏为 `ANTHROPIC_API_KEY=[REDACTED]`。

## 12. 收集证据

```bash
cd /home/ubuntu/cccagents-source
./scripts/phase4/collect_phase4_evidence.sh docs/phase4/linux-ops
```

会生成或更新：

```text
docs/phase4/linux-ops/service-install.log
docs/phase4/linux-ops/allowlist-check.log
docs/phase4/linux-ops/restart-recovery.log
docs/phase4/linux-ops/multi-project-scheduler.log
docs/phase4/linux-ops/pm-notification.log
```

同步回开发机后提交到仓库。证据中必须只出现 `[REDACTED]`，不能出现真实密钥或真实 Feishu user id。

## 13. 最终验收命令

在服务器或开发机仓库根目录运行：

```bash
PYTHONPATH=src .venv/bin/pytest -q tests
```

运行密钥扫描：

```bash
grep -R "FEISHU_APP_SECRET=.*[A-Za-z0-9]\|FEISHU_VERIFICATION_TOKEN=.*[A-Za-z0-9]\|FEISHU_ENCRYPT_KEY=.*[A-Za-z0-9]\|sk-\|ANTHROPIC_API_KEY=.*[A-Za-z0-9]" docs src tests hermes scripts || true
```

允许命中：

- `[REDACTED]`
- `<redacted-api-key>`
- 测试字符串，例如 `sk-test...` 或 `ANTHROPIC_API_KEY=secret-value`
- 计划文档里的示例命令

不允许命中：

- 真实 Feishu App Secret
- 真实 Verification Token
- 真实 Encrypt Key
- 真实 API Key
- 真实 Authorization/Bearer token

## 14. 最终验收标准

`docs/phase4/phase4-acceptance.md` 应全部为 `pass`：

- Hermes Gateway/worker durable service
- Feishu allowlist replaces open access
- PM-only Feishu boundary preserved
- Hermes/server restart recovery
- Interrupted task handling
- Multi-project isolation
- Same-project write lock
- PM notifications
- Approval safety
- Secret safety
- Local/Linux tests
- Linux evidence

## 15. 推送仓库

```bash
git status --short
git log --oneline -5
git push origin main
```

如果 GitHub HTTPS 超时，稍后在网络稳定时重试即可；本地提交不受影响。

## 16. 运维常用命令

```bash
systemctl status cccagents-hermes-gateway --no-pager
systemctl status cccagents-pm-scheduler --no-pager
journalctl -u cccagents-hermes-gateway -n 100 --no-pager
journalctl -u cccagents-pm-scheduler -n 100 --no-pager
sudo systemctl restart cccagents-hermes-gateway
sudo systemctl restart cccagents-pm-scheduler
```

服务应保持：

```text
cccagents-hermes-gateway: enabled / active
cccagents-pm-scheduler: enabled / active
```

## 17. 新项目启动建议

为每个新项目分配独立 `project_id`：

```text
/home/ubuntu/cccagents/workspaces/<project_id>/repo
/home/ubuntu/cccagents/projects/<project_id>/08-logs
```

所有命令、产物、任务状态、run evidence 都按 `project_id` 隔离保存。技术方案和测试用例保持独立产物，且方案编写与测试用例编写并行进行；双方有问题各自找产品沟通需求，不互相同步中间内容。
