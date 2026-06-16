# cccagents Phase 5 Linux 部署命令清单

> 按顺序在 Linux 服务器上执行。假设服务器路径与 Phase 4 一致。

## 前置约定

```bash
RUN_USER=ubuntu
PROJECT_SOURCE=/home/ubuntu/cccagents-source
PROJECT_ROOT=/home/ubuntu/cccagents
HERMES_ENV=/home/ubuntu/.hermes/.env
HERMES_CONFIG=/home/ubuntu/.hermes/config.yaml
```

---

## 步骤 1: 连接服务器

```bash
ssh ubuntu@<server-ip>
```

---

## 步骤 2: 更新源码

```bash
cd /home/ubuntu/cccagents-source
git pull origin main
```

---

## 步骤 3: 安装依赖

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
```

---

## 步骤 4: 运行测试

```bash
PYTHONPATH=src .venv/bin/pytest -q tests
```

**期望**: `127 passed` 或更多

---

## 步骤 5: 部署前检查

```bash
bash scripts/phase5/preflight_check.sh
```

**期望输出**:
```
Python 3.x.x
v18.x.x
9.x.x
x.x.x
phase5 preflight PASS
```

---

## 步骤 6: 编排 Smoke 测试（Fake Executor）

```bash
PROJECT_ROOT=/home/ubuntu/cccagents SOURCE_DIR=/home/ubuntu/cccagents-source \
  bash scripts/phase5/run_orchestrator_smoke.sh
```

**期望输出**:
```
S0: PASS
S1: PASS
S2: PASS
All smoke tests completed successfully.
```

---

## 步骤 7: 验证 Smoke 产物

```bash
ls /home/ubuntu/cccagents/smoke-tests/smoke-s0/project-state.json
ls /home/ubuntu/cccagents/smoke-tests/smoke-s0/role-plan.json
ls /home/ubuntu/cccagents/smoke-tests/smoke-s1/04-test-cases/test-result.md
ls /home/ubuntu/cccagents/smoke-tests/smoke-s2/03-architecture/tech-design.md
```

**期望**: 所有文件存在

---

## 步骤 8: 真实 Claude CLI Smoke（可选）

> 仅在网关和密钥已配置后执行。

```bash
cd /home/ubuntu/cccagents-source
export PYTHONPATH=$PWD/src
source /home/ubuntu/.hermes/.env

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

**期望**: `{'status': 'done', ...}`

---

## 步骤 9: 验证真实执行产物

```bash
ls /home/ubuntu/cccagents/real-tests/real-s0-smoke/08-logs/hermes-runs/
cat /home/ubuntu/cccagents/real-tests/real-s0-smoke/08-logs/hermes-runs/run-001/result.json
```

**期望**: 看到 `run-001` 目录和 `result.json`

---

## 步骤 10: 更新 systemd 服务

```bash
cd /home/ubuntu/cccagents-source
PROJECT_SOURCE=/home/ubuntu/cccagents-source \
PROJECT_ROOT=/home/ubuntu/cccagents \
HERMES_ENV=/home/ubuntu/.hermes/.env \
RUN_USER=ubuntu \
UNIT_DIR=/tmp/cccagents-systemd-units \
./scripts/phase4/install_phase4_services.sh
```

---

## 步骤 11: 检查生成的 unit 文件

```bash
cat /tmp/cccagents-systemd-units/cccagents-pm-scheduler.service
```

**期望包含**:
```
WorkingDirectory=/home/ubuntu/cccagents-source
Environment=CCCAGENTS_PROJECT_ROOT=/home/ubuntu/cccagents
Environment=PYTHONPATH=/home/ubuntu/cccagents-source/src
ExecStart=/home/ubuntu/cccagents-source/.venv/bin/python -m cccagents.pm_scheduler
```

---

## 步骤 12: 安装并重启服务

```bash
sudo cp /tmp/cccagents-systemd-units/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart cccagents-pm-scheduler
sudo systemctl restart cccagents-hermes-gateway
```

---

## 步骤 13: 验证服务状态

```bash
systemctl is-active cccagents-pm-scheduler
systemctl is-active cccagents-hermes-gateway
```

**期望**: 两个都是 `active`

---

## 步骤 14: 审批流程验证 - 创建 S3 pending_approval 项目

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

**期望**:
```
{'status': 'pending_approval', 'complexity': 'S3', 'message': 'project requires Feishu user approval'}
```

---

## 步骤 15: 审批流程验证 - 模拟审批

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

**期望**:
```
Approved: True, Reason: approved
Project status: approved, Phase: APPROVED
```

---

## 步骤 16: 重启恢复验证 - 创建 interrupted 项目

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

---

## 步骤 17: 重启恢复验证 - 恢复并验证自动重试

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

**期望**:
```
Result: done
Project status: done
Recovery log: {"action": "reconcile_interrupted", ...}
```

---

## 步骤 18: 部署验证

```bash
PROJECT_ROOT=/home/ubuntu/cccagents SOURCE_DIR=/home/ubuntu/cccagents-source \
  bash scripts/phase5/verify_deployment.sh
```

**期望**: `phase5 deployment verification PASS`

---

## 步骤 19: 密钥扫描

```bash
cd /home/ubuntu/cccagents-source
grep -R "FEISHU_APP_SECRET=.*[A-Za-z0-9]\|FEISHU_VERIFICATION_TOKEN=.*[A-Za-z0-9]\|FEISHU_ENCRYPT_KEY=.*[A-Za-z0-9]\|sk-\|ANTHROPIC_API_KEY=.*[A-Za-z0-9]" docs src tests hermes scripts || true
```

**期望**: 只出现 `[REDACTED]`、`<redacted-api-key>`、测试字符串

---

## 步骤 20: 收集证据

```bash
PROJECT_ROOT=/home/ubuntu/cccagents \
  bash scripts/phase5/collect_phase5_evidence.sh
```

---

## 步骤 21: 查看生成的证据

```bash
ls -la docs/phase5/linux-ops/
```

**期望**:
```
preflight-check.log
orchestrator-smoke.log
approval-smoke.log
recovery-smoke.log
deployment-verification.log
```

---

## 步骤 22: 同步回开发机

```bash
# 在开发机执行
cd /Users/ccc/Documents/AI/cccagents
scp -r ubuntu@<server-ip>:/home/ubuntu/cccagents-source/docs/phase5/linux-ops docs/phase5/
```

---

## 步骤 23: 提交证据到仓库

```bash
cd /Users/ccc/Documents/AI/cccagents
git add docs/phase5/linux-ops/
git commit -m "docs: add Phase 5 Linux deployment evidence"
git push origin main
```

---

## 步骤 24: 最终验收

```bash
cd /home/ubuntu/cccagents-source
PYTHONPATH=src .venv/bin/pytest -q tests
git log --oneline -5
systemctl status cccagents-pm-scheduler --no-pager
systemctl status cccagents-hermes-gateway --no-pager
```

**期望**:
- 所有测试通过
- 最新 commit 包含 Phase 5 证据
- 两个服务都是 `active (running)`

---

## 故障排查

| 问题 | 解决 |
|------|------|
| `ModuleNotFoundError: cccagents` | 检查 PYTHONPATH 设置 |
| Gateway 报已有 PID | unit 文件加 `--replace` |
| Claude CLI 超时 | 检查 `cccai.store` 连通性 |
| 审批被拒 invalid_signature | 检查 Feishu webhook 签名 |
| 恢复不自动重试 | S3 或高风险，需人工决策 |
