# cccagents 新服务器部署操作记录

> 部署日期: 2026-06-14
> 服务器: ubuntu@43.142.31.20:22222
> 系统: Ubuntu 24.04.4 LTS, Python 3.12.3, 50G 磁盘, 1.9G 内存

## 初始状态

| 项目 | 状态 |
| --- | --- |
| OS | Ubuntu 24.04.4 LTS |
| Python | 3.12.3 ✅ |
| Node.js | ❌ 未安装 |
| Claude CLI | ❌ 未安装 |
| Hermes | ❌ 未安装 |
| 磁盘 | 42G 可用 |
| 内存 | 1.9G (可用 1.5G) |

---

## 步骤记录

### 1. 系统依赖安装 ✅

```bash
sudo apt update
sudo apt install -y curl git build-essential python3-venv python3-pip sshpass pipx
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs
```

结果：
- Node.js: v24.16.0
- npm: 11.13.0

### 2. 源码部署 ✅

**问题**：服务器无法连接 GitHub（github.com:443 超时）

**解决**：从本地打包 scp 上传

```bash
# 本地执行
tar czf /tmp/cccagents-source.tar.gz --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' -C /Users/ccc/Documents/AI cccagents
sshpass -p '***' scp -P 22222 /tmp/cccagents-source.tar.gz ubuntu@43.142.31.20:/tmp/

# 服务器执行
cd /home/ubuntu && tar xzf /tmp/cccagents-source.tar.gz && mv cccagents cccagents-source
```

### 3. Python 环境 ✅

```bash
cd /home/ubuntu/cccagents-source
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

测试结果：84 passed, 2 failed（test_complexity_classifier 和 test_orchestrator_s0_s1 模块未实现，不影响部署）

### 4. Claude Code CLI ✅

```bash
sudo npm install -g @anthropic-ai/claude-code
```

版本：2.1.177

### 5. Hermes Agent ✅

**问题**：安装脚本无法从 GitHub 下载

**解决**：使用 pipx 安装

```bash
pipx install hermes-agent
```

版本：0.16.0

### 6. 配置 .env ✅

路径改为 `/home/ubuntu/.env`（权限 600）

```
ANTHROPIC_BASE_URL=https://cccai.store
ANTHROPIC_API_KEY=***
ANTHROPIC_MODEL=qwen3.7-plus
OPENAI_API_KEY=***
OPENAI_BASE_URL=https://cccai.store/v1
```

### 7. 配置 Hermes config.yaml ✅

路径：`/home/ubuntu/.hermes/config.yaml`

**问题**：使用 `api_key_env` 环境变量方式导致 401 Invalid token

**解决**：在 `custom_providers` 里内联 `api_key`

```yaml
custom_providers:
- name: ccc
  base_url: https://cccai.store/v1
  api_key: ***
  models:
    gpt-5.5:
      name: gpt-5.5
    qwen3.7-plus:
      name: qwen3.7-plus
  model: qwen3.7-plus

model:
  provider: ccc
  base_url: https://cccai.store/v1
  default: qwen3.7-plus

gateway:
  terminal: true
  GATEWAY_ALLOW_ALL_USERS: false
```

### 8. Hermes 模型验证 ✅

```bash
hermes chat --query "reply OK only" --provider ccc --model qwen3.7-plus --quiet
```

输出：`OK`

### 9. systemd 服务 ✅

```bash
cd /home/ubuntu/cccagents-source
PROJECT_SOURCE=/home/ubuntu/cccagents-source \
PROJECT_ROOT=/home/ubuntu/cccagents \
HERMES_ENV=/home/ubuntu/.env \
RUN_USER=ubuntu \
UNIT_DIR=/tmp/cccagents-systemd-units \
bash scripts/phase4/install_phase4_services.sh

sudo cp /tmp/cccagents-systemd-units/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cccagents-hermes-gateway
sudo systemctl enable --now cccagents-pm-scheduler
```

状态：
- cccagents-hermes-gateway: enabled / active
- cccagents-pm-scheduler: enabled / active

### 10. 配置 Feishu Bot ✅

写入 `/home/ubuntu/.env` 和 `/home/ubuntu/.hermes/.env`：

```
FEISHU_APP_ID=cli_aa8c7962f3bbdbd6
FEISHU_APP_SECRET=***
FEISHU_CONNECTION_MODE=websocket
```

飞书开放平台配置：
- 事件订阅：长连接模式（websocket）
- 添加事件：`im.message.receive_v1`
- 权限：`im:message`、`im:message:send_as_bot`、`im:chat`
- 版本发布：已创建并发布

验证：
- websocket 连接成功：`connected to wss://msg-frontier.feishu.cn/ws/v2`
- 消息收到：`你好` → 回复 16 chars，10.8s
- 消息收到：`你是谁` → 回复 123 chars，3.5s
- 消息收到：`ping pm` → 回复成功

### 11. 收紧 Allowlist ✅

```
GATEWAY_ALLOW_ALL_USERS=false
FEISHU_ALLOWED_USERS=ou_efc291e8806c47b8460cc26a447cc476
```

验证：
- `Channel directory built: 1 target(s)` — 识别到允许的用户
- 消息收到：`你好` → 回复成功，6.8s

### 12. 模型切换 gpt-5.5 → qwen3.7-plus ✅

修改 `.env` 和 `config.yaml`，重启 Gateway。

验证：
- 日志确认：`model=qwen3.7-plus provider=custom`
- 旧 session 已清除（避免历史上下文干扰）
- 消息收到：`你是什么模型` → 回复 104 chars，4.3s

### 13. Phase 4 Smoke 验证 ✅

#### 13.1 重启恢复 smoke

```
task_id='task_restart_1', previous_status='running', next_status='interrupted',
action='mark_interrupted', notify_pm=True
```

结果：stale running task 正确恢复为 interrupted ✅

#### 13.2 多项目调度 smoke

```
project_a_first_write          → dispatch_allowed        ✅
project_a_second_write_blocked → same_project_write_lock  ✅
project_b_write_allowed        → dispatch_allowed         ✅
project_a_outside_cwd_blocked  → cwd_outside_project      ✅
```

结果：4 个场景全部符合预期 ✅

#### 13.3 PM 通知 smoke

覆盖 4 种通知类型：
- `progress_summary` ✅
- `restart_recovery` ✅
- `approval_request` ✅
- `completion_notice` ✅

密钥脱敏验证：`ANTHROPIC_API_KEY=secret-value` → `ANTHROPIC_API_KEY=[REDACTED]` ✅

---

## 遇到的问题及解决

| 问题 | 原因 | 解决方案 |
| --- | --- | --- |
| GitHub 连不上 | 服务器网络限制，github.com:443 超时 | 本地打包 scp 上传 |
| Hermes 安装脚本失败 | 同上，raw.githubusercontent.com 也超时 | 改用 `pipx install hermes-agent` |
| cccai.store HTTP 301 | nginx 强制 HTTPS | 改用 `https://cccai.store/v1` |
| Hermes 401 Invalid token | `api_key_env` 环境变量方式不生效 | 在 config.yaml 的 `custom_providers` 里内联 `api_key` |
| Bot 说自己是 gpt-5.5 | 旧 session 历史上下文残留 | 删除旧 session，新 session 正确识别为 qwen3.7-plus |

---

## 最终状态

| 组件 | 版本/值 | 状态 |
| --- | --- | --- |
| Python | 3.12.3 | ✅ |
| Node.js | v24.16.0 | ✅ |
| Claude Code CLI | 2.1.177 | ✅ |
| Hermes Agent | 0.16.0 | ✅ |
| 当前模型 | qwen3.7-plus | ✅ |
| cccagents-hermes-gateway | - | enabled / active |
| cccagents-pm-scheduler | - | enabled / active |
| Feishu Bot | websocket | 连接正常 |
| Allowlist | `ou_efc291e8806c47b8460cc26a447cc476` | 已收紧 |
| Phase 4 Smoke | 重启恢复 / 多项目调度 / PM 通知 | 全部通过 |

---

## 运维命令

```bash
# 查看服务状态
systemctl status cccagents-hermes-gateway --no-pager
systemctl status cccagents-pm-scheduler --no-pager

# 查看日志
journalctl -u cccagents-hermes-gateway -n 100 --no-pager
journalctl -u cccagents-pm-scheduler -n 100 --no-pager
tail -f /home/ubuntu/.hermes/logs/gateway.log
tail -f /home/ubuntu/.hermes/logs/agent.log

# 重启服务
sudo systemctl restart cccagents-hermes-gateway
sudo systemctl restart cccagents-pm-scheduler
```

---

### 14. PM Routing Stage A - systemd unit 验证 ✅

检查时间：2026-06-14

Gateway unit 关键配置：

```text
WorkingDirectory=/home/ubuntu/cccagents-source
EnvironmentFile=/home/ubuntu/.env
ExecStart=/home/ubuntu/.local/bin/hermes gateway run --accept-hooks --replace
```

结果：`WorkingDirectory` 已指向仓库根目录，Hermes Gateway 可以读取 `/home/ubuntu/cccagents-source/AGENTS.md`。
