# cccagents Phase 5 Linux 部署指南

> 本文档用于把 M4-M5（自动编排 + Feishu 审批 + 重启恢复）部署到 Linux 服务器。
> 前置条件：Phase 1-4 已完成部署，systemd 服务已运行。

## 1. 变更概览

Phase 5 新增/修改的模块：

| 模块 | 说明 |
|------|------|
| `src/cccagents/claude_executor.py` | 扩展 `run_claude_task()`，支持真实 Claude Code CLI 执行 |
| `src/cccagents/real_orchestrator.py` | `RealExecutor` + `orchestrate_with_real_executor()` |
| `src/cccagents/project_orchestrator.py` | 编排入口：审批分流 + 重启恢复 |
| `src/cccagents/approval_handler.py` | Feishu 审批动作处理（approve/reject/pause/resume） |
| `src/cccagents/feishu_webhook.py` | Feishu webhook 解析和处理 |
| `src/cccagents/pm_scheduler.py` | 扩展：编排循环 + 恢复扫描 |
| `scripts/phase5/preflight_check.sh` | 部署前检查 |
| `scripts/phase5/run_orchestrator_smoke.sh` | S0/S1/S2 smoke 测试 |
| `scripts/phase5/verify_deployment.sh` | 部署验证 |
| `scripts/phase5/collect_phase5_evidence.sh` | 证据收集 |

## 2. 服务器约定（与 Phase 4 一致）

```text
RUN_USER=ubuntu
PROJECT_SOURCE=/home/ubuntu/cccagents-source
PROJECT_ROOT=/home/ubuntu/cccagents
HERMES_ENV=/home/ubuntu/.hermes/.env
HERMES_CONFIG=/home/ubuntu/.hermes/config.yaml
```

## 3. 更新源码

```bash
cd /home/ubuntu/cccagents-source
git pull origin main
.venv/bin/python -m pip install -r requirements-dev.txt
```

运行测试验证：

```bash
PYTHONPATH=src .venv/bin/pytest -q tests
```

期望：`129 passed`（或更多）。

## 4. 部署前检查

```bash
cd /home/ubuntu/cccagents-source
bash scripts/phase5/preflight_check.sh
```

检查项：

- Python3、Node.js、npm、Claude Code CLI、Hermes 可用
- `cccai.store` 网关可达
- `/home/ubuntu/.hermes/.env` 存在且权限 600
- `config.yaml` 包含 `gpt-5.5`、`cccai.store/v1`
- `GATEWAY_ALLOW_ALL_USERS=false`

期望输出：

```text
phase5 preflight PASS
```

## 5. 编排 Smoke 测试（Fake Executor）

先用 FakeExecutor 验证编排流程，不调用真实 Claude CLI：

```bash
cd /home/ubuntu/cccagents-source
PROJECT_ROOT=/home/ubuntu/cccagents SOURCE_DIR=/home/ubuntu/cccagents-source \
  bash scripts/phase5/run_orchestrator_smoke.sh
```

期望输出：

```text
S0: PASS (roles: DEV, DEV, PM)
S1: PASS (roles: DEV, DEV, TEST, PM)
S2: PASS (roles: PDM, PM, ARCH, TEST, PM, DEV, DEV, TEST, PDM)
All smoke tests completed successfully.
```

验证产物：

```bash
ls /home/ubuntu/cccagents/smoke-tests/smoke-s0/project-state.json
ls /home/ubuntu/cccagents/smoke-tests/smoke-s0/role-plan.json
ls /home/ubuntu/cccagents/smoke-tests/smoke-s1/04-test-cases/test-result.md
ls /home/ubuntu/cccagents/smoke-tests/smoke-s2/03-architecture/tech-design.md
```

## 6. 真实 Claude Code CLI Smoke（可选）

> 仅在网关和密钥已配置后执行。

```bash
cd /home/ubuntu/cccagents-source
export PYTHONPATH=$PWD/src
export ANTHROPIC_BASE_URL="http://cccai.store"
export ANTHROPIC_API_KEY="<从 /home/ubuntu/.hermes/.env 读取>"
export ANTHROPIC_MODEL="gpt-5.5"

.venv/bin/python -c "
from pathlib import Path
from cccagents.real_orchestrator import RealExecutor, orchestrate_with_real_executor
from cccagents.orchestrator import OrchestrationRequest
import os, time

request = OrchestrationRequest(
    project_id='real-s0-smoke',
    text='在 workspace 里创建一个 hello.txt，内容为 Hello from cccagents',
    project_root=Path('/home/ubuntu/cccagents/real-tests'),
    now=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
)

executor = RealExecutor(
    model=os.getenv('ANTHROPIC_MODEL', 'gpt-5.5'),
    base_url=os.getenv('ANTHROPIC_BASE_URL', 'http://cccai.store'),
    api_key=os.getenv('ANTHROPIC_API_KEY'),
)

result = orchestrate_with_real_executor(request, executor, now=request.now)
print(result)
"
```

验证：

```bash
ls /home/ubuntu/cccagents/real-tests/real-s0-smoke/08-logs/hermes-runs/
cat /home/ubuntu/cccagents/real-tests/real-s0-smoke/08-logs/hermes-runs/run-001/result.json
```

## 7. 更新 systemd 服务

Phase 5 的 scheduler 需要编排循环。更新 unit 文件：

```bash
cd /home/ubuntu/cccagents-source
PROJECT_SOURCE=/home/ubuntu/cccagents-source \
PROJECT_ROOT=/home/ubuntu/cccagents \
HERMES_ENV=/home/ubuntu/.hermes/.env \
RUN_USER=ubuntu \
UNIT_DIR=/tmp/cccagents-systemd-units \
./scripts/phase4/install_phase4_services.sh
```

检查生成的 unit 文件：

```bash
cat /tmp/cccagents-systemd-units/cccagents-pm-scheduler.service
```

关键字段：

```text
WorkingDirectory=/home/ubuntu/cccagents-source
Environment=CCCAGENTS_PROJECT_ROOT=/home/ubuntu/cccagents
Environment=PYTHONPATH=/home/ubuntu/cccagents-source/src
ExecStart=/home/ubuntu/cccagents-source/.venv/bin/python -m cccagents.pm_scheduler
Restart=always
```

重新加载并重启：

```bash
sudo cp /tmp/cccagents-systemd-units/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart cccagents-pm-scheduler
sudo systemctl restart cccagents-hermes-gateway
systemctl is-active cccagents-pm-scheduler
systemctl is-active cccagents-hermes-gateway
```

期望：两个都是 `active`。

## 8. 审批流程验证

### 8.1 创建 S3 pending_approval 项目

```bash
cd /home/ubuntu/cccagents-source
PYTHONPATH=src .venv/bin/python - <<'PY'
from pathlib import Path
from cccagents.orchestrator import FakeExecutor, OrchestrationRequest
from cccagents.project_orchestrator import orchestrate_project

project_dir = Path("/home/ubuntu/cccagents/projects/phase5-approval-smoke")
request = OrchestrationRequest(
    project_id="phase5-approval-smoke",
    text="修改认证权限并部署到生产，涉及 FEISHU_APP_SECRET 配置",
    project_root=Path("/home/ubuntu/cccagents/projects"),
    now="2026-06-15T10:00:00Z",
)

result = orchestrate_project(project_dir, request, FakeExecutor(), now="2026-06-15T10:00:00Z")
print(result)
PY
```

期望：

```text
{'status': 'pending_approval', 'complexity': 'S3', 'message': 'project requires Feishu user approval'}
```

### 8.2 模拟审批

```bash
cd /home/ubuntu/cccagents-source
PYTHONPATH=src .venv/bin/python - <<'PY'
from pathlib import Path
from cccagents.approval_handler import ApprovalRequest, process_approval_action
from cccagents.feishu_contracts import FeishuSecurityContext
from cccagents.project_state import load_project_state

project_dir = Path("/home/ubuntu/cccagents/projects/phase5-approval-smoke")

request = ApprovalRequest(
    project_id="phase5-approval-smoke",
    approval_id="approval-smoke-001",
    action="approve",
    feishu_user_id="user-1",
    feishu_message_id="msg-smoke-001",
    timestamp=1700000000,
    signature="test-sig",
)

context = FeishuSecurityContext(
    allowed_approvers={"user-1"},
    seen_event_ids=set(),
    now=1700000000,
    timestamp_window_seconds=300,
    expected_signature="test-sig",
)

result = process_approval_action(request, context, project_dir, now="2026-06-15T10:05:00Z")
print(f"Approved: {result.approved}, Reason: {result.reason}")

state = load_project_state(project_dir)
print(f"Project status: {state.status}, Phase: {state.current_phase}")
PY
```

期望：

```text
Approved: True, Reason: approved
Project status: approved, Phase: APPROVED
```

### 8.3 验证审批日志

```bash
cat /home/ubuntu/cccagents/projects/phase5-approval-smoke/08-logs/approval-events.jsonl 2>/dev/null || echo "No approval-events.jsonl (expected: webhook handler writes this)"
cat /home/ubuntu/cccagents/projects/phase5-approval-smoke/project-state.json
```

## 9. 重启恢复验证

### 9.1 创建 interrupted 项目

```bash
cd /home/ubuntu/cccagents-source
PYTHONPATH=src .venv/bin/python - <<'PY'
import json
from pathlib import Path
from cccagents.project_state import ProjectState, save_project_state

project_dir = Path("/home/ubuntu/cccagents/projects/phase5-recovery-smoke")
project_dir.mkdir(parents=True, exist_ok=True)

state = ProjectState(
    project_id="phase5-recovery-smoke",
    source="feishu",
    status="interrupted",
    complexity="S1",
    current_phase="DEV_IMPLEMENTATION",
    required_roles=["PM", "DEV", "TEST"],
    risk_flags=["code_change"],
    approval_policy="auto_if_l0_l1_and_all_reviews_pass",
    retry_count_by_phase={},
    created_at="2026-06-15T09:00:00Z",
    updated_at="2026-06-15T09:30:00Z",
    last_pm_notification_at="2026-06-15T09:30:00Z",
)
save_project_state(project_dir, state)
print("Created interrupted project")
PY
```

### 9.2 恢复并验证自动重试

```bash
cd /home/ubuntu/cccagents-source
PYTHONPATH=src .venv/bin/python - <<'PY'
from pathlib import Path
from cccagents.orchestrator import FakeExecutor, OrchestrationRequest
from cccagents.project_orchestrator import reconcile_and_orchestrate
from cccagents.project_state import load_project_state

project_dir = Path("/home/ubuntu/cccagents/projects/phase5-recovery-smoke")
request = OrchestrationRequest(
    project_id="phase5-recovery-smoke",
    text="修复登录按钮 loading 的局部 bug，并跑本地测试",
    project_root=Path("/home/ubuntu/cccagents/projects"),
    now="2026-06-15T10:00:00Z",
)

result = reconcile_and_orchestrate(project_dir, request, FakeExecutor(), now="2026-06-15T10:00:00Z")
print(f"Result: {result['status']}")

state = load_project_state(project_dir)
print(f"Project status: {state.status}")

recovery_log = project_dir / "08-logs" / "restart-recovery.jsonl"
if recovery_log.exists():
    print(f"Recovery log:\n{recovery_log.read_text()}")
PY
```

期望：

```text
Result: done
Project status: done
Recovery log: {"action": "reconcile_interrupted", ...}
```

## 10. 部署验证

```bash
cd /home/ubuntu/cccagents-source
PROJECT_ROOT=/home/ubuntu/cccagents SOURCE_DIR=/home/ubuntu/cccagents-source \
  bash scripts/phase5/verify_deployment.sh
```

检查项：

- systemd 服务 enabled/active
- pytest 全部通过
- 密钥扫描通过
- 编排 smoke 通过
- 审批流程正常
- 重启恢复正常

期望输出：

```text
phase5 deployment verification PASS
```

## 11. 收集证据

```bash
cd /home/ubuntu/cccagents-source
PROJECT_ROOT=/home/ubuntu/cccagents \
  bash scripts/phase5/collect_phase5_evidence.sh
```

生成：

```text
docs/phase5/linux-ops/preflight-check.log
docs/phase5/linux-ops/orchestrator-smoke.log
docs/phase5/linux-ops/approval-smoke.log
docs/phase5/linux-ops/recovery-smoke.log
docs/phase5/linux-ops/deployment-verification.log
```

同步回开发机后提交到仓库。证据中必须只出现 `[REDACTED]`。

## 12. 密钥扫描

```bash
grep -R "FEISHU_APP_SECRET=.*[A-Za-z0-9]\|FEISHU_VERIFICATION_TOKEN=.*[A-Za-z0-9]\|FEISHU_ENCRYPT_KEY=.*[A-Za-z0-9]\|sk-\|ANTHROPIC_API_KEY=.*[A-Za-z0-9]" docs src tests hermes scripts || true
```

只允许 `[REDACTED]`、`<redacted-api-key>`、测试字符串。

## 13. 推送仓库

```bash
cd /home/ubuntu/cccagents-source
git status --short
git log --oneline -5
git push origin main
```

## 14. 运维命令

```bash
# 查看服务状态
systemctl status cccagents-hermes-gateway --no-pager
systemctl status cccagents-pm-scheduler --no-pager

# 查看日志
journalctl -u cccagents-pm-scheduler -n 100 --no-pager
journalctl -u cccagents-hermes-gateway -n 100 --no-pager

# 重启服务
sudo systemctl restart cccagents-pm-scheduler
sudo systemctl restart cccagents-hermes-gateway

# 查看项目状态
cat /home/ubuntu/cccagents/projects/<project_id>/project-state.json

# 查看审批日志
cat /home/ubuntu/cccagents/projects/<project_id>/08-logs/approval-events.jsonl

# 查看恢复日志
cat /home/ubuntu/cccagents/projects/<project_id>/08-logs/restart-recovery.jsonl

# 查看 Claude CLI 执行日志
ls /home/ubuntu/cccagents/projects/<project_id>/08-logs/hermes-runs/
cat /home/ubuntu/cccagents/projects/<project_id>/08-logs/hermes-runs/<run_id>/result.json
```

## 15. 验收标准

`docs/phase5/phase5-acceptance.md` 应全部为 `pass`：

- Preflight check
- Orchestrator smoke (S0/S1/S2)
- Real Claude CLI execution
- Feishu approval webhook handling
- S3 pending_approval flow
- Restart recovery (auto-retry L0/L1)
- Restart recovery (S3 manual decision)
- Paused project handling
- Secret safety
- Deployment verification
- Evidence collection

## 16. 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError: cccagents` | PYTHONPATH 未设置 | unit 文件加 `Environment=PYTHONPATH=.../src` |
| Gateway 报已有 PID | 缺少 `--replace` | unit ExecStart 加 `--replace` |
| Claude CLI 超时 | 网关不可达 | 检查 `cccai.store` 连通性和 `.env` 配置 |
| 审批被拒 invalid_signature | 签名不匹配 | 检查 Feishu webhook 签名配置 |
| 恢复不自动重试 | S3 或高风险 | 正常行为，需人工决策 |
| Smoke 测试失败 | 模块缺失 | `git pull` 并重新安装依赖 |
