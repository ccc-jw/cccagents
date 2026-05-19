# cccagents Phase 3 Feishu Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect Feishu to Hermes through a PM-only interaction boundary, with secure callback and approval handling verified by local simulation before real Feishu rollout.

**Architecture:** Feishu remains only the user entry and notification channel; Hermes PM Agent remains the only user-facing role and Hermes state remains authoritative. Phase 3 adds local contract modules for Feishu message routing and approval security, documents the Hermes Feishu Gateway configuration shape, and verifies the flow on Linux with redacted logs.

**Tech Stack:** NousResearch Hermes Gateway, Feishu app/bot callbacks, Python dataclasses, pytest, Linux shell logs, Markdown evidence, project-local redaction and audit rules.

---

## File Structure

- Create `src/cccagents/feishu_contracts.py`: dataclasses and pure functions for Feishu inbound messages, PM notifications, approval actions, PM-only routing, and safe card content checks.
- Create `tests/test_feishu_contracts.py`: unit tests for message routing, approval authorization, replay/timestamp/signature checks, and secret-like content rejection.
- Create `docs/phase3/feishu-gateway-config.md`: non-secret Feishu/Hermes Gateway configuration guide.
- Create `docs/phase3/linux-ops/feishu-gateway-capability.log`: Linux evidence from Hermes Feishu/Gateway capability discovery.
- Create `docs/phase3/linux-ops/feishu-local-simulation.log`: local simulation command output.
- Create `docs/phase3/feishu-local-simulation-report.md`: local simulation result and security conclusion.
- Create `docs/phase3/phase3-acceptance.md`: final Phase 3 acceptance record.

## Task 1: Add Feishu contract tests

**Files:**
- Create: `tests/test_feishu_contracts.py`
- Create later: `src/cccagents/feishu_contracts.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_feishu_contracts.py`:

```python
from cccagents.feishu_contracts import (
    FeishuApprovalAction,
    FeishuInboundMessage,
    FeishuSecurityContext,
    build_pm_route,
    validate_approval_action,
    validate_card_content,
)


def test_feishu_inbound_message_always_routes_to_pm():
    message = FeishuInboundMessage(
        project_id="demo",
        feishu_message_id="msg-1",
        feishu_chat_id="chat-1",
        feishu_user_id="user-1",
        message_type="text",
        text="创建一个项目",
        received_at=1_700_000_000,
    )

    route = build_pm_route(message)

    assert route.project_id == "demo"
    assert route.target_role == "PM"
    assert route.source == "feishu"
    assert route.payload["text"] == "创建一个项目"


def test_valid_approval_action_passes_security_checks():
    action = FeishuApprovalAction(
        project_id="demo",
        approval_id="approval-1",
        action="approve",
        feishu_user_id="user-1",
        feishu_message_id="event-1",
        timestamp=1_700_000_000,
        signature="sig-ok",
    )
    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids=set(),
        now=1_700_000_100,
        timestamp_window_seconds=300,
        expected_signature="sig-ok",
    )

    decision = validate_approval_action(action, context)

    assert decision.allowed is True
    assert decision.reason == "approved"


def test_unknown_approver_is_rejected():
    action = FeishuApprovalAction(
        project_id="demo",
        approval_id="approval-1",
        action="approve",
        feishu_user_id="user-2",
        feishu_message_id="event-1",
        timestamp=1_700_000_000,
        signature="sig-ok",
    )
    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids=set(),
        now=1_700_000_100,
        timestamp_window_seconds=300,
        expected_signature="sig-ok",
    )

    decision = validate_approval_action(action, context)

    assert decision.allowed is False
    assert decision.reason == "unauthorized_approver"


def test_replayed_event_is_rejected():
    action = FeishuApprovalAction(
        project_id="demo",
        approval_id="approval-1",
        action="approve",
        feishu_user_id="user-1",
        feishu_message_id="event-1",
        timestamp=1_700_000_000,
        signature="sig-ok",
    )
    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids={"event-1"},
        now=1_700_000_100,
        timestamp_window_seconds=300,
        expected_signature="sig-ok",
    )

    decision = validate_approval_action(action, context)

    assert decision.allowed is False
    assert decision.reason == "replay_detected"


def test_old_timestamp_is_rejected():
    action = FeishuApprovalAction(
        project_id="demo",
        approval_id="approval-1",
        action="approve",
        feishu_user_id="user-1",
        feishu_message_id="event-1",
        timestamp=1_699_999_000,
        signature="sig-ok",
    )
    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids=set(),
        now=1_700_000_100,
        timestamp_window_seconds=300,
        expected_signature="sig-ok",
    )

    decision = validate_approval_action(action, context)

    assert decision.allowed is False
    assert decision.reason == "timestamp_out_of_window"


def test_invalid_signature_is_rejected():
    action = FeishuApprovalAction(
        project_id="demo",
        approval_id="approval-1",
        action="approve",
        feishu_user_id="user-1",
        feishu_message_id="event-1",
        timestamp=1_700_000_000,
        signature="sig-bad",
    )
    context = FeishuSecurityContext(
        allowed_approvers={"user-1"},
        seen_event_ids=set(),
        now=1_700_000_100,
        timestamp_window_seconds=300,
        expected_signature="sig-ok",
    )

    decision = validate_approval_action(action, context)

    assert decision.allowed is False
    assert decision.reason == "invalid_signature"


def test_secret_like_card_content_is_rejected():
    decision = validate_card_content("部署完成，ANTHROPIC_API_KEY=sk-live-secret")

    assert decision.allowed is False
    assert decision.reason == "secret_like_content"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest tests/test_feishu_contracts.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cccagents.feishu_contracts'`.

## Task 2: Implement Feishu contracts

**Files:**
- Create: `src/cccagents/feishu_contracts.py`
- Test: `tests/test_feishu_contracts.py`

- [ ] **Step 1: Write the minimal implementation**

Create `src/cccagents/feishu_contracts.py`:

```python
from dataclasses import dataclass
from typing import Any

from cccagents.redaction import redact_text


ALLOWED_APPROVAL_ACTIONS = {"approve", "reject", "comment", "pause_project"}


@dataclass(frozen=True)
class FeishuInboundMessage:
    project_id: str
    feishu_message_id: str
    feishu_chat_id: str
    feishu_user_id: str
    message_type: str
    text: str
    received_at: int


@dataclass(frozen=True)
class PMRoute:
    project_id: str
    target_role: str
    source: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class FeishuApprovalAction:
    project_id: str
    approval_id: str
    action: str
    feishu_user_id: str
    feishu_message_id: str
    timestamp: int
    signature: str


@dataclass(frozen=True)
class FeishuSecurityContext:
    allowed_approvers: set[str]
    seen_event_ids: set[str]
    now: int
    timestamp_window_seconds: int
    expected_signature: str


@dataclass(frozen=True)
class FeishuDecision:
    allowed: bool
    reason: str


def build_pm_route(message: FeishuInboundMessage) -> PMRoute:
    return PMRoute(
        project_id=message.project_id,
        target_role="PM",
        source="feishu",
        payload={
            "feishu_message_id": message.feishu_message_id,
            "feishu_chat_id": message.feishu_chat_id,
            "feishu_user_id": message.feishu_user_id,
            "message_type": message.message_type,
            "text": message.text,
            "received_at": message.received_at,
        },
    )


def validate_approval_action(
    action: FeishuApprovalAction,
    context: FeishuSecurityContext,
) -> FeishuDecision:
    if action.signature != context.expected_signature:
        return FeishuDecision(False, "invalid_signature")
    if abs(context.now - action.timestamp) > context.timestamp_window_seconds:
        return FeishuDecision(False, "timestamp_out_of_window")
    if action.feishu_message_id in context.seen_event_ids:
        return FeishuDecision(False, "replay_detected")
    if action.feishu_user_id not in context.allowed_approvers:
        return FeishuDecision(False, "unauthorized_approver")
    if action.action not in ALLOWED_APPROVAL_ACTIONS:
        return FeishuDecision(False, "unsupported_action")
    return FeishuDecision(True, "approved")


def validate_card_content(content: str) -> FeishuDecision:
    redacted = redact_text(content)
    if redacted != content:
        return FeishuDecision(False, "secret_like_content")
    return FeishuDecision(True, "approved")
```

- [ ] **Step 2: Run the Feishu contract tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest tests/test_feishu_contracts.py -v
```

Expected: PASS.

- [ ] **Step 3: Run the full test suite**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q
```

Expected: PASS.

## Task 3: Document Feishu Gateway config shape

**Files:**
- Create: `docs/phase3/feishu-gateway-config.md`
- Create: `docs/phase3/linux-ops/feishu-gateway-capability.log`

- [ ] **Step 1: Create the Feishu Gateway config document**

Create `docs/phase3/feishu-gateway-config.md`:

```markdown
# Phase 3 Feishu Gateway Config

Date: 2026-05-19

## Goal

Configure Hermes Feishu Gateway so Feishu user messages enter Hermes through the PM Agent only.

## Non-secret Configuration Shape

```text
platform = feishu
project_id = <project_id>
pm_role = PM
callback_path = /webhook/feishu
allowed_chat_ids = <secret-ref-or-linux-local-config>
allowed_approver_user_ids = <secret-ref-or-linux-local-config>
```

## Secret Locations

Real Feishu credentials must stay on the Linux host only:

```text
~/.hermes/.env
~/.hermes/config.yaml
```

Repository files may contain only variable names and redacted evidence.

## Required Secret Variables

```text
FEISHU_APP_ID
FEISHU_APP_SECRET
FEISHU_VERIFICATION_TOKEN
FEISHU_ENCRYPT_KEY
```

## Routing Rule

```text
Feishu user -> Hermes Feishu Gateway -> PM Agent -> Hermes state/router
```

No Feishu user message may route directly to PDM, RES, ARCH, DEV, TEST, or SEC.

## Approval Security

Every approval callback must verify:

- callback signature
- timestamp validation window
- replay protection by message/event id
- Feishu user id to approver mapping
- action authorization
- no secret-like content in cards or logs

## Source of Truth

Feishu is not the source of truth. Hermes project state and local artifacts remain authoritative.
```

- [ ] **Step 2: Collect Linux Hermes Gateway capability evidence**

Run on Linux repository copy:

```bash
set -euo pipefail
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
cd "$HOME/cccagents-source"
mkdir -p docs/phase3/linux-ops
{
  date -u +%Y-%m-%dT%H:%M:%SZ
  hermes gateway --help
  hermes gateway list || true
  hermes tools list --summary || hermes tools --help || true
} 2>&1 | sed -E 's/(FEISHU_[A-Z_]+=).*/\1[REDACTED]/g; s/(app[_-]?secret|verification[_-]?token|encrypt[_-]?key)([=: ]+)[^ ]+/\1\2[REDACTED]/Ig' | tee docs/phase3/linux-ops/feishu-gateway-capability.log
```

Expected: log file exists and contains Hermes Gateway help or platform information.

- [ ] **Step 3: Sync Linux evidence back to the worktree**

Run from Mac worktree:

```bash
rsync -av -e "sshpass -p 'ccc123123!' ssh -p 22222 -o StrictHostKeyChecking=no" ubuntu@124.156.192.85:/home/ubuntu/cccagents-source/docs/phase3/linux-ops/feishu-gateway-capability.log docs/phase3/linux-ops/
```

Expected: local `docs/phase3/linux-ops/feishu-gateway-capability.log` exists.

## Task 4: Run local Feishu callback simulation

**Files:**
- Create: `docs/phase3/linux-ops/feishu-local-simulation.log`
- Create: `docs/phase3/feishu-local-simulation-report.md`

- [ ] **Step 1: Run local simulation tests on Linux**

Sync the worktree to Linux, then run:

```bash
set -euo pipefail
cd "$HOME/cccagents-source"
mkdir -p docs/phase3/linux-ops
{
  date -u +%Y-%m-%dT%H:%M:%SZ
  PYTHONPATH=src python3 -m pytest tests/test_feishu_contracts.py -v
} 2>&1 | sed -E 's/(FEISHU_[A-Z_]+=).*/\1[REDACTED]/g; s/(sk-)[A-Za-z0-9_-]+/\1[REDACTED]/g; s/(api[_-]?key|authorization|bearer|app[_-]?secret|verification[_-]?token|encrypt[_-]?key)([=: ]+)[^ ]+/\1\2[REDACTED]/Ig' | tee docs/phase3/linux-ops/feishu-local-simulation.log
```

Expected: `tests/test_feishu_contracts.py` passes on Linux. If pytest is unavailable on Linux, document that Linux Python test setup is missing and run the same command in the Mac worktree as the accepted interim evidence.

- [ ] **Step 2: Create the local simulation report**

Create `docs/phase3/feishu-local-simulation-report.md`:

```markdown
# Phase 3 Feishu Local Simulation Report

Date: 2026-05-19

## Status

pass

## Simulated Flow

```text
Feishu callback payload -> PM-only route -> approval security checks -> Hermes state decision
```

## Verified Checks

- Feishu inbound messages route to PM only.
- Valid approval action passes.
- Unknown approver is rejected.
- Replayed event is rejected.
- Old timestamp is rejected.
- Invalid signature is rejected.
- Secret-like card content is rejected.

## Evidence

- `tests/test_feishu_contracts.py`
- `docs/phase3/linux-ops/feishu-local-simulation.log`

## Secret Handling

No real Feishu app secret, verification token, encrypt key, API key, or authorization header is stored in repository evidence.
```

## Task 5: Add Phase 3 acceptance

**Files:**
- Create: `docs/phase3/phase3-acceptance.md`

- [ ] **Step 1: Create the acceptance document**

Create `docs/phase3/phase3-acceptance.md`:

```markdown
# Phase 3 Acceptance

Date: 2026-05-19

## Gate Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Hermes Feishu Gateway capability discovered | pass/fail | `docs/phase3/linux-ops/feishu-gateway-capability.log` |
| Feishu config shape documented without secrets | pass/fail | `docs/phase3/feishu-gateway-config.md` |
| PM-only message routing contract tested | pass/fail | `tests/test_feishu_contracts.py` |
| Approval action contract tested | pass/fail | `tests/test_feishu_contracts.py` |
| Signature, timestamp, replay, and approver checks tested | pass/fail | `tests/test_feishu_contracts.py` |
| No real secret in repository evidence | pass/fail | grep verification |
| Phase 3 local simulation report created | pass/fail | `docs/phase3/feishu-local-simulation-report.md` |

## Decision

Proceed to Phase 4 long-running async operation only if all blocking gates pass.

## Open Issues

- Real Feishu app credentials are not committed and must be configured only on the Linux host.
- Production Feishu callback delivery requires an externally reachable callback endpoint or gateway deployment mode.
```

Fill `pass/fail` based on actual evidence before closing Phase 3.

- [ ] **Step 2: Run tests**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -q
```

Expected: PASS.

- [ ] **Step 3: Scan for leaked secrets**

Run:

```bash
grep -R "FEISHU_APP_SECRET=.*[A-Za-z0-9]\|FEISHU_VERIFICATION_TOKEN=.*[A-Za-z0-9]\|FEISHU_ENCRYPT_KEY=.*[A-Za-z0-9]\|sk-\|ANTHROPIC_API_KEY=.*[A-Za-z0-9]" docs src tests hermes scripts || true
```

Expected: no real secret values. Redacted placeholders, command templates, and test fixtures are acceptable.

## Self-Review

Spec coverage:

- Feishu Gateway capability: Task 3.
- PM-only user entry: Task 1 and Task 2.
- Approval actions: Task 1 and Task 2.
- Signature, timestamp, replay, approver authorization: Task 1 and Task 2.
- Secret-free evidence: Task 3, Task 4, Task 5.
- Linux logs: Task 3 and Task 4.
- Acceptance: Task 5.

Placeholder scan:

- The plan uses `<project_id>` and `<secret-ref-or-linux-local-config>` only as documented configuration placeholders, not unfinished work.
- No TODO/TBD/fill-in-later implementation steps remain.

Type consistency:

- Test names match functions defined in `src/cccagents/feishu_contracts.py`.
- Approval action names match the design: `approve`, `reject`, `comment`, `pause_project`.
