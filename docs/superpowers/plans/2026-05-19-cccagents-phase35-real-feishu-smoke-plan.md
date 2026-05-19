# cccagents Phase 3.5 Real Feishu Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect a real Feishu/Lark bot to Hermes and verify a minimal Feishu user -> PM -> DEV -> PM -> Feishu user loop before Phase 4 long-running async work.

**Architecture:** Hermes Gateway connects to Feishu/Lark through websocket mode. Feishu remains the user entry and notification channel, PM remains the only user-facing agent, and DEV executes a tiny workspace-local file creation task through Hermes delegation.

**Tech Stack:** NousResearch Hermes Gateway, Feishu/Lark bot credentials, websocket gateway mode, Claude Code/Hermes local tools, Linux shell evidence, Markdown acceptance records, redacted logs.

---

## File Structure

- Create `docs/superpowers/specs/2026-05-19-cccagents-phase35-real-feishu-smoke-design.md`: final Phase 3.5 design.
- Create `docs/phase3/linux-ops/feishu-real-env-check.log`: redacted Linux secret presence check.
- Create `docs/phase3/linux-ops/feishu-real-gateway-discovery.log`: Hermes Gateway setup/status discovery.
- Create `docs/phase3/linux-ops/feishu-real-gateway.log`: redacted live Gateway run log.
- Create `docs/phase3/linux-ops/feishu-real-pm-dev-loop.log`: PM -> DEV artifact verification log.
- Create `docs/phase3/feishu-real-smoke-report.md`: Phase 3.5 smoke report.
- Create `docs/phase3/phase35-acceptance.md`: final Phase 3.5 acceptance record.

## Task 1: Configure Feishu secrets on Linux

**Files:**
- Create: `docs/phase3/linux-ops/feishu-real-env-check.log`

- [x] **Step 1: Write Feishu App/Bot secrets to Linux only**

Configured in:

```text
~/.hermes/.env
```

Values written:

```text
FEISHU_APP_ID=[REDACTED]
FEISHU_APP_SECRET=[REDACTED]
FEISHU_VERIFICATION_TOKEN=[REDACTED]
FEISHU_ENCRYPT_KEY=[REDACTED]
```

- [x] **Step 2: Verify redacted presence**

Evidence:

```text
hermes_env=present
FEISHU_APP_ID=[REDACTED]
FEISHU_APP_SECRET=[REDACTED]
FEISHU_VERIFICATION_TOKEN=[REDACTED]
FEISHU_ENCRYPT_KEY=[REDACTED]
```

## Task 2: Verify Hermes Feishu Gateway mode

**Files:**
- Create: `docs/phase3/linux-ops/feishu-real-gateway-discovery.log`
- Create: `docs/phase3/linux-ops/feishu-real-gateway.log`

- [x] **Step 1: Discover Gateway setup state**

Observed:

```text
Feishu / Lark (configured)
Gateway is not running
```

- [x] **Step 2: Start Gateway in foreground for smoke**

Run:

```bash
hermes gateway run --accept-hooks -vv
```

Observed:

```text
[Feishu] Connected in websocket mode (feishu)
✓ feishu connected
Gateway running with 1 platform(s)
```

- [x] **Step 3: Document HTTPS callback status**

`feishu.cccai.store` resolves to the Linux host, but Hermes connected through websocket mode, so HTTPS callback was not required for this smoke.

## Task 3: Verify Feishu PM send/receive

**Files:**
- Create: `docs/phase3/linux-ops/feishu-real-gateway.log`

- [x] **Step 1: Send test message from Feishu**

Input:

```text
ping pm
```

- [x] **Step 2: Confirm Hermes received it**

Evidence:

```text
[Feishu] Inbound dm message received ... text='ping pm'
inbound message: platform=feishu ... msg='ping pm'
conversation turn ... platform=feishu ... msg='ping pm'
```

- [x] **Step 3: Confirm Hermes replied**

Evidence:

```text
response ready: platform=feishu ... response=39 chars
[Feishu] Sending response ...
```

## Task 4: Verify Feishu PM -> DEV tiny task loop

**Files:**
- Create: `docs/phase3/linux-ops/feishu-real-pm-dev-loop.log`

- [x] **Step 1: Send tiny DEV task from Feishu**

Requested artifact:

```text
/home/ubuntu/cccagents/workspaces/phase35-feishu-smoke/repo/hello-from-feishu-dev.txt
```

- [x] **Step 2: Confirm PM delegated to DEV/tool execution**

Evidence:

```text
conversation turn ... platform=feishu ...
tool write_file completed
```

- [x] **Step 3: Verify workspace artifact**

Observed:

```text
file_exists=true
file_content=1213hello from Feishu PM to DEV
```

The `1213` prefix was part of the Feishu message content and does not affect the smoke conclusion.

## Task 5: Finalize Phase 3.5 evidence

**Files:**
- Create: `docs/phase3/feishu-real-smoke-report.md`
- Create: `docs/phase3/phase35-acceptance.md`

- [ ] **Step 1: Sync Linux logs back to Mac worktree**

Run:

```bash
rsync -av -e "sshpass -p 'ccc123123!' ssh -p 22222 -o StrictHostKeyChecking=no" ubuntu@124.156.192.85:/home/ubuntu/cccagents-source/docs/phase3/linux-ops/ docs/phase3/linux-ops/
```

Expected: local Phase 3.5 log files exist.

- [ ] **Step 2: Create final smoke report**

Create `docs/phase3/feishu-real-smoke-report.md` with:

```markdown
# Phase 3.5 Real Feishu Smoke Report

Date: 2026-05-19

## Status

pass

## Verified Flow

```text
Feishu user -> Hermes Gateway -> PM Agent -> DEV task -> workspace artifact -> PM Agent -> Feishu user
```

## Evidence

- `docs/phase3/linux-ops/feishu-real-env-check.log`
- `docs/phase3/linux-ops/feishu-real-gateway-discovery.log`
- `docs/phase3/linux-ops/feishu-real-gateway.log`
- `docs/phase3/linux-ops/feishu-real-pm-dev-loop.log`

## Result

Real Feishu/Lark websocket mode is connected. Feishu inbound messages reach Hermes, Hermes responds to Feishu, and a Feishu-triggered PM -> DEV tiny task created a workspace artifact.

## Security Notes

Real Feishu secrets are stored only on Linux `~/.hermes/.env`. Repository evidence contains only redacted secret placeholders. `GATEWAY_ALLOW_ALL_USERS=true` was used only for smoke validation and must be replaced by a Feishu user allowlist before production use.
```

- [ ] **Step 3: Create acceptance record**

Create `docs/phase3/phase35-acceptance.md` with gate results.

- [ ] **Step 4: Run tests and secret scan**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q
grep -R "FEISHU_APP_SECRET=.*[A-Za-z0-9]\|FEISHU_VERIFICATION_TOKEN=.*[A-Za-z0-9]\|FEISHU_ENCRYPT_KEY=.*[A-Za-z0-9]\|sk-\|ANTHROPIC_API_KEY=.*[A-Za-z0-9]" docs src tests hermes scripts || true
```

Expected: tests pass; no real secret values in repository evidence.
