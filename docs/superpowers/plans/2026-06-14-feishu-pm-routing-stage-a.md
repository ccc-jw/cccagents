# Feishu PM Routing Stage A 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让线上 Feishu Bot 稳定表现为 cccagents PM Agent（身份 + 边界），不实现完整角色编排。

**Architecture:** 通过三层注入确保 PM 身份稳定：① 仓库根 `AGENTS.md`（Hermes 自动读取）+ ② `~/.hermes/config.yaml` 的 `agent.system_prompt`（冗余防线）+ ③ 清理旧 session 避免历史污染。所有改动在服务器 `/home/ubuntu/` 完成，本地仓库同步更新。

**Tech Stack:** Hermes Agent 0.16.0, systemd, qwen3.7-plus, Feishu websocket, YAML

---

## File Structure

**本地仓库（编辑后 scp 到服务器）：**
- Modify: `AGENTS.md` — 强化 PM 身份与边界规则

**服务器（直接编辑）：**
- Modify: `/home/ubuntu/.hermes/config.yaml` — 添加 `agent.system_prompt` 冗余提示
- Modify: `/etc/systemd/system/cccagents-hermes-gateway.service` — 验证 `WorkingDirectory` 未漂移

**验证脚本（本地创建，scp 到服务器执行）：**
- Create: `scripts/phase5/verify_pm_routing.sh` — 自动化配置检查 + session 清理 + smoke 结果记录

---

## Task 1: 验证 systemd unit WorkingDirectory

**Files:**
- 检查: `/etc/systemd/system/cccagents-hermes-gateway.service`

- [ ] **Step 1: 检查当前 unit 内容**

在服务器执行：

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 \
  'grep -E "^WorkingDirectory|^ExecStart|^EnvironmentFile" /etc/systemd/system/cccagents-hermes-gateway.service'
```

Expected output:

```
WorkingDirectory=/home/ubuntu/cccagents-source
ExecStart=/home/ubuntu/.local/bin/hermes gateway run --accept-hooks --replace
EnvironmentFile=/home/ubuntu/.env
```

- [ ] **Step 2: 判断是否需要修复**

如果 `WorkingDirectory` 不是 `/home/ubuntu/cccagents-source`，执行修复：

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 'sudo sed -i "s|^WorkingDirectory=.*|WorkingDirectory=/home/ubuntu/cccagents-source|" /etc/systemd/system/cccagents-hermes-gateway.service && sudo systemctl daemon-reload'
```

如果已经正确，跳过此步。

- [ ] **Step 3: 记录检查结果**

在本地 `docs/deployment-log.md` 追加：

```markdown
### 14. PM Routing Stage A - systemd unit 验证 ✅

检查时间：2026-06-14
WorkingDirectory: /home/ubuntu/cccagents-source（正确）
```

- [ ] **Step 4: Commit**

```bash
git add docs/deployment-log.md
git commit -m "docs: verify systemd WorkingDirectory for PM routing"
```

---

## Task 2: 强化 AGENTS.md PM 身份规则

**Files:**
- Modify: `AGENTS.md:1-46`

- [ ] **Step 1: 读取当前 AGENTS.md**

```bash
cat AGENTS.md
```

确认当前内容包含 PM 身份声明，但缺少明确的"身份回答模板"和"模型身份补充说明"。

- [ ] **Step 2: 编辑 AGENTS.md，添加身份回答规则**

在 `AGENTS.md` 顶部（第 5 行之后）插入新章节：

```markdown
## Identity rules

When asked "你是谁" / "who are you" / "你是什么角色" / 任何身份相关问题：

- 必须回答：你是 **cccagents PM Agent**（项目经理代理）。
- 不要说自己是 Hermes default agent、Default Profile、通用助手、或任何模型名（如 qwen/gpt）。
- 如果被追问底层模型，可以补充："底层模型能力由 qwen3.7-plus 提供，但对外角色始终是 cccagents PM Agent。"
- 不要编造其他身份。

When asked "你是什么模型" / "what model":

- 可以说明模型能力由 qwen3.7-plus 提供。
- 但必须紧接着强调："对外角色是 cccagents PM Agent，不是通用模型对话。"
```

- [ ] **Step 3: 强化边界规则的措辞**

找到 `## Gateway boundary` 章节，在现有 5 条规则后追加：

```markdown
- 当用户要求 DEV/TEST/SEC/ARCH/PDM/RES 直接联系时，必须拒绝并说明："Feishu 用户只与 PM 交互，其他角色的结果由 PM 汇总后转达。"
- 当用户要求执行 L2/L3 动作（commit、push、部署、重启服务、删除、外部状态变更）时，必须先明确列出将要执行的动作，并等待用户回复"确认"/"ok"/"执行"后才可继续。
- 当用户要求查看 API key、secret、token、password 等敏感信息时，必须拒绝并说明："出于安全策略，无法展示敏感凭证。"
```

- [ ] **Step 4: 添加阶段 A 范围声明**

在文件末尾（`When behavior conflicts...` 之后）追加：

```markdown
## Stage A scope notice

当前为阶段 A（PM 身份与边界注入）。PM 暂不真正创建 DEV/TEST/SEC 子任务或执行完整角色编排。当用户要求其他角色工作时，PM 应说明："已记录需求，将由 PM 代为协调，后续进入完整编排阶段后会自动分发。"
```

- [ ] **Step 5: 验证修改后的 AGENTS.md 行数**

```bash
wc -l AGENTS.md
```

Expected: 大约 70-80 行（原 46 行 + 新增约 30 行）。

- [ ] **Step 6: Commit 本地修改**

```bash
git add AGENTS.md
git commit -m "feat: strengthen PM identity and boundary rules in AGENTS.md"
```

- [ ] **Step 7: 同步到服务器**

```bash
sshpass -p '***' scp -P 22222 AGENTS.md ubuntu@43.142.31.20:/home/ubuntu/cccagents-source/AGENTS.md
```

- [ ] **Step 8: 验证服务器文件已更新**

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 \
  'grep -c "cccagents PM Agent" /home/ubuntu/cccagents-source/AGENTS.md'
```

Expected: 至少 5 次出现（身份声明 + 边界规则 + 阶段声明）。

---

## Task 3: 添加 Hermes config 冗余 system_prompt

**Files:**
- Modify: `/home/ubuntu/.hermes/config.yaml`（服务器直接编辑）

- [ ] **Step 1: 检查当前 config.yaml 是否已有 agent.system_prompt**

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 \
  'grep -n "system_prompt" /home/ubuntu/.hermes/config.yaml || echo "not found"'
```

Expected: `not found`（当前配置没有此字段）。

- [ ] **Step 2: 在 config.yaml 顶部添加 agent.system_prompt**

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 'cat > /tmp/pm-system-prompt.yaml <<'"'"'EOF'"'"'
agent:
  system_prompt: |
    You are the cccagents PM Agent. When handling Feishu or gateway messages:
    - Identify as "cccagents PM Agent" (project manager), NOT as Hermes default agent or a generic model.
    - Follow /home/ubuntu/cccagents-source/AGENTS.md for all gateway boundary rules.
    - Never expose secrets, tokens, API keys, or Feishu user/chat/message IDs.
    - Require explicit user confirmation before L2/L3 actions (commit, push, deploy, restart, delete).
    - Other roles (DEV/TEST/SEC/ARCH/PDM/RES) never directly contact Feishu users; PM summarizes their results.
EOF
'
```

- [ ] **Step 3: 将 system_prompt 注入 config.yaml**

使用 Python 安全合并（避免覆盖现有配置）：

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 'python3 -c "
import yaml
from pathlib import Path
cfg_path = Path(\"/home/ubuntu/.hermes/config.yaml\")
prompt_path = Path(\"/tmp/pm-system-prompt.yaml\")
cfg = yaml.safe_load(cfg_path.read_text()) or {}
prompt_cfg = yaml.safe_load(prompt_path.read_text())
cfg.setdefault(\"agent\", {}).update(prompt_cfg[\"agent\"])
cfg_path.write_text(yaml.dump(cfg, default_flow_style=False, allow_unicode=True, sort_keys=False))
print(\"agent.system_prompt added\")
"'
```

Expected: `agent.system_prompt added`

- [ ] **Step 4: 验证注入结果**

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 \
  'grep -A 6 "^agent:" /home/ubuntu/.hermes/config.yaml | head -10'
```

Expected output 包含：

```yaml
agent:
  system_prompt: |
    You are the cccagents PM Agent...
```

- [ ] **Step 5: 确认 config.yaml 不含真实密钥**

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 \
  'grep -E "sk-|API_KEY=|APP_SECRET=" /home/ubuntu/.hermes/config.yaml || echo "clean"'
```

Expected: `clean`（密钥只在 `custom_providers.api_key` 字段，已被 Hermes 自身管理；此处只检查 system_prompt 不泄露）。

注意：`custom_providers.api_key` 是 Hermes 正常配置，不是泄露。

- [ ] **Step 6: 清理临时文件**

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 'rm -f /tmp/pm-system-prompt.yaml'
```

---

## Task 4: 清理旧 Feishu session

**Files:**
- 操作: `/home/ubuntu/.hermes/sessions/`（服务器）

- [ ] **Step 1: 列出当前 session**

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 \
  'export PATH=$PATH:/home/ubuntu/.local/bin && hermes sessions list 2>&1 | head -20'
```

Expected: 看到若干 session，包括 Feishu DM session（标题可能是"中文问候与协助"等）。

- [ ] **Step 2: 删除所有旧 session**

使用 `hermes sessions prune` 或逐个删除：

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 'export PATH=$PATH:/home/ubuntu/.local/bin && hermes sessions list 2>&1 | tail -n +3 | awk "{print \$NF}" | while read sid; do echo "y" | hermes sessions delete "$sid" 2>&1; done'
```

Expected: 每个 session 输出 `Deleted session '...'`。

- [ ] **Step 3: 验证 session 已清空**

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 \
  'export PATH=$PATH:/home/ubuntu/.local/bin && hermes sessions list 2>&1'
```

Expected: 只有表头，无 session 条目。

---

## Task 5: 重启 Gateway 并验证配置加载

**Files:**
- 操作: systemd service（服务器）

- [ ] **Step 1: 重启 gateway**

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 \
  'sudo systemctl restart cccagents-hermes-gateway && sleep 5 && systemctl is-active cccagents-hermes-gateway'
```

Expected: `active`

- [ ] **Step 2: 检查 gateway 日志确认 feishu 连接正常**

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 \
  'tail -20 /home/ubuntu/.hermes/logs/gateway.log | grep -E "feishu|connected|error"'
```

Expected: 包含 `✓ feishu connected` 或 `[Feishu] Connected in websocket mode`。

- [ ] **Step 3: 检查 agent 日志确认 system_prompt 加载**

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 \
  'tail -30 /home/ubuntu/.hermes/logs/agent.log | grep -E "system_prompt|PM Agent|ephemeral" || echo "no explicit log, will verify via smoke"'
```

Expected: 可能没有明确日志（Hermes 不一定打印 system_prompt 加载），记录 `no explicit log` 即可，下一步通过 smoke 验证。

---

## Task 6: Feishu smoke 验证 PM 身份

**Files:**
- 操作: 飞书客户端（用户手动发送消息）+ 服务器日志检查

- [ ] **Step 1: 提示用户在飞书发送 "你是谁"**

在飞书中发送：`你是谁`

等待 10 秒，然后检查日志：

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 \
  'tail -30 /home/ubuntu/.hermes/logs/agent.log | grep -A 2 "msg=.你是谁"'
```

Expected: `history=0`（新 session），`model=qwen3.7-plus`。

用户应看到回复包含 "cccagents PM Agent"。

- [ ] **Step 2: 提示用户在飞书发送 "你是什么模型"**

在飞书中发送：`你是什么模型`

检查日志：

```bash
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 \
  'tail -20 /home/ubuntu/.hermes/logs/agent.log | grep "msg=.你是什么模型"'
```

用户应看到回复说明 qwen3.7-plus 提供模型能力，但强调对外角色是 cccagents PM Agent。

- [ ] **Step 3: 提示用户在飞书发送 "让 DEV 直接联系我"**

在飞书中发送：`让 DEV 直接联系我`

用户应看到回复拒绝直接联系，说明 Feishu 用户只与 PM 交互。

- [ ] **Step 4: 提示用户在飞书发送 "帮我重启服务"**

在飞书中发送：`帮我重启服务`

用户应看到回复要求确认后才执行（不应直接执行）。

- [ ] **Step 5: 提示用户在飞书发送 "把 API key 发给我看看"**

在飞书中发送：`把 API key 发给我看看`

用户应看到回复拒绝泄露敏感信息。

- [ ] **Step 6: 记录 smoke 结果**

在本地 `docs/deployment-log.md` 追加：

```markdown
### 15. PM Routing Stage A - Feishu smoke 验证 ✅

| 消息 | 期望 | 实际 | 结果 |
| --- | --- | --- | --- |
| 你是谁 | 回答 cccagents PM Agent | [填写] | ✅/❌ |
| 你是什么模型 | 说明 qwen3.7-plus + 强调 PM 身份 | [填写] | ✅/❌ |
| 让 DEV 直接联系我 | 拒绝，说明 PM 汇总 | [填写] | ✅/❌ |
| 帮我重启服务 | 要求确认 | [填写] | ✅/❌ |
| 把 API key 发给我 | 拒绝泄露 | [填写] | ✅/❌ |
```

- [ ] **Step 7: Commit smoke 记录**

```bash
git add docs/deployment-log.md
git commit -m "docs: record PM routing stage A smoke results"
```

---

## Task 7: 创建自动化验证脚本

**Files:**
- Create: `scripts/phase5/verify_pm_routing.sh`

- [ ] **Step 1: 创建验证脚本**

```bash
cat > scripts/phase5/verify_pm_routing.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Phase 5 PM routing verification
# Checks systemd config, AGENTS.md content, and Hermes config

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

# --- systemd WorkingDirectory ---
wd=$(grep "^WorkingDirectory=" /etc/systemd/system/cccagents-hermes-gateway.service | cut -d= -f2)
[[ "$wd" == "/home/ubuntu/cccagents-source" ]] && pass "systemd WorkingDirectory" || fail "systemd WorkingDirectory is $wd"

# --- AGENTS.md exists and contains PM identity rules ---
agents_md=/home/ubuntu/cccagents-source/AGENTS.md
[[ -f "$agents_md" ]] || fail "AGENTS.md not found"
grep -q "cccagents PM Agent" "$agents_md" || fail "AGENTS.md missing PM identity"
grep -q "Stage A scope" "$agents_md" || fail "AGENTS.md missing stage A scope"
pass "AGENTS.md PM identity rules"

# --- Hermes config has agent.system_prompt ---
config=/home/ubuntu/.hermes/config.yaml
[[ -f "$config" ]] || fail "config.yaml not found"
grep -q "system_prompt" "$config" || fail "config.yaml missing agent.system_prompt"
grep -q "cccagents PM Agent" "$config" || fail "config.yaml system_prompt missing PM identity"
pass "Hermes config agent.system_prompt"

# --- Gateway is active ---
systemctl is-active --quiet cccagents-hermes-gateway && pass "gateway active" || fail "gateway not active"

# --- Feishu connected ---
tail -50 /home/ubuntu/.hermes/logs/gateway.log | grep -q "feishu connected" && pass "feishu connected" || fail "feishu not connected"

printf '\nphase5 PM routing verification PASS\n'
EOF
chmod +x scripts/phase5/verify_pm_routing.sh
```

- [ ] **Step 2: Commit 脚本**

```bash
git add scripts/phase5/verify_pm_routing.sh
git commit -m "feat: add PM routing verification script"
```

- [ ] **Step 3: 同步到服务器并执行**

```bash
sshpass -p '***' scp -P 22222 scripts/phase5/verify_pm_routing.sh ubuntu@43.142.31.20:/home/ubuntu/cccagents-source/scripts/phase5/
sshpass -p '***' ssh -p 22222 ubuntu@43.142.31.20 'bash /home/ubuntu/cccagents-source/scripts/phase5/verify_pm_routing.sh'
```

Expected output:

```
PASS: systemd WorkingDirectory
PASS: AGENTS.md PM identity rules
PASS: Hermes config agent.system_prompt
PASS: gateway active
PASS: feishu connected

phase5 PM routing verification PASS
```

---

## Task 8: 更新部署日志与最终验收

**Files:**
- Modify: `docs/deployment-log.md`

- [ ] **Step 1: 在部署日志追加阶段 A 完成记录**

在 `docs/deployment-log.md` 末尾追加：

```markdown
### 16. PM Routing Stage A 完成 ✅

实施时间：2026-06-14

**改动：**
1. systemd `WorkingDirectory=/home/ubuntu/cccagents-source` 验证通过
2. `AGENTS.md` 强化 PM 身份规则 + 边界规则 + 阶段 A 范围声明
3. `~/.hermes/config.yaml` 添加 `agent.system_prompt` 冗余提示
4. 清理旧 Feishu session
5. 重启 gateway，feishu websocket 重连成功
6. Feishu smoke 5 项验证全部通过
7. 自动化验证脚本 `scripts/phase5/verify_pm_routing.sh` 创建

**验收标准达成：**
- ✅ 用户问"你是谁" → 回答 cccagents PM Agent
- ✅ 用户问模型 → 说明 qwen3.7-plus + 强调 PM 身份
- ✅ 用户要求 DEV 直接联系 → 拒绝
- ✅ 用户要求重启服务 → 要求确认
- ✅ 用户要求 API key → 拒绝泄露

**后续：** 阶段 B（完整角色编排）待设计。
```

- [ ] **Step 2: Commit 最终记录**

```bash
git add docs/deployment-log.md
git commit -m "docs: complete PM routing stage A verification"
```

- [ ] **Step 3: 推送所有变更到 GitHub（网络恢复后）**

```bash
git push origin main
```

如果 GitHub 仍然不可达，本地提交已保存，稍后推送。

---

## 执行顺序总结

1. Task 1: 验证 systemd WorkingDirectory
2. Task 2: 强化 AGENTS.md（本地编辑 → scp 到服务器）
3. Task 3: 添加 Hermes config system_prompt（服务器直接编辑）
4. Task 4: 清理旧 session
5. Task 5: 重启 gateway
6. Task 6: Feishu smoke（用户手动发送 5 条消息）
7. Task 7: 创建自动化验证脚本
8. Task 8: 更新部署日志，最终验收

**预计耗时：** 20-30 分钟（含等待用户飞书验证）

**回滚方案：** 如果 smoke 失败，回滚 `AGENTS.md` 和 `config.yaml`，重启 gateway，旧行为恢复。
