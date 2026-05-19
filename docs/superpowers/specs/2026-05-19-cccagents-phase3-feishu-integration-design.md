# cccagents Phase 3 Feishu Integration Design

Date: 2026-05-19

## Goal

Phase 3 connects Feishu to Hermes so the user talks only to the PM Agent through Feishu, while Hermes remains the source of truth for project state, routing, approvals, and audit records.

## Scope

In scope:

- Verify Hermes Feishu Gateway capability on the Linux host.
- Document Feishu app configuration shape without storing real credentials.
- Define the Feishu -> Hermes PM message contract.
- Define approval card actions for review gates and high-risk permissions.
- Define callback security requirements: signature verification, timestamp window, replay protection, and approver authorization.
- Run a local Feishu webhook/callback simulation without sending real Feishu messages.
- Save Linux operation logs and Phase 3 acceptance evidence.

Out of scope for Phase 3:

- Long-running systemd hardening and cross-day recovery tuning; that belongs to Phase 4.
- Full production deployment automation.
- Replacing Hermes Gateway with a custom Feishu service.

## Architecture

```text
Feishu user
  -> Feishu App / Bot
  -> Hermes Feishu Gateway
  -> Hermes PM Agent
  -> Hermes state, memory, routing, approvals
  -> role agents and Claude Code CLI executor
```

Feishu is the user entry and notification channel only. Hermes state and local project artifacts remain authoritative.

## Message Contract

### User message to PM

```text
project_id
feishu_message_id
feishu_chat_id
feishu_user_id
message_type
text
received_at
```

Rules:

- Every Feishu user message maps to PM first.
- PM decides whether to ask the user, route internally, or create an approval request.
- Other roles do not directly chat with the user.
- PM responses must not include secrets, raw API keys, or full auth headers.

### PM notification to user

```text
project_id
event_type
summary
required_action
artifact_refs
approval_id
risk_level
created_at
```

Allowed `event_type` values for Phase 3:

```text
requirement_clarification
review_approval
risk_alert
permission_approval
progress_summary
phase_acceptance
```

## Approval Card Actions

Phase 3 supports these card actions:

```text
approve
reject
comment
pause_project
```

Each action must include:

```text
project_id
approval_id
action
feishu_user_id
feishu_message_id
timestamp
signature
```

Approval decisions update Hermes state only after security checks pass.

## Security Requirements

Phase 3 must enforce:

- Event callback signature verification.
- Timestamp validation window.
- Replay protection using Feishu message/event IDs.
- Feishu user ID to approver mapping.
- Approval action authorization.
- No secret values in card content, logs, prompts, or project artifacts.
- Feishu is not the source of truth; Hermes state remains authoritative.

## Local Simulation Strategy

Before using real Feishu credentials, Phase 3 creates a local callback simulation module and tests it with deterministic payloads.

Simulation verifies:

- PM-only routing.
- Valid approval action accepted.
- Unknown approver rejected.
- Replayed event rejected.
- Old timestamp rejected.
- Invalid signature rejected.
- Secret-like card content rejected or redacted before persistence.

## Linux Verification

On Linux, Phase 3 must collect:

```text
docs/phase3/linux-ops/feishu-gateway-capability.log
docs/phase3/linux-ops/feishu-local-simulation.log
docs/phase3/feishu-gateway-config.md
docs/phase3/feishu-local-simulation-report.md
docs/phase3/phase3-acceptance.md
```

Credential rule:

- Real Feishu app credentials may exist only on the Linux host secret store or Hermes config secret location.
- Repository files may contain only variable names, config shape, and redacted evidence.

## Acceptance Gates

| Gate | Required result |
| --- | --- |
| Hermes Feishu Gateway capability discovered | pass |
| Feishu config shape documented without secrets | pass |
| PM-only message routing contract documented and tested | pass |
| Approval action contract documented and tested | pass |
| Signature, timestamp, replay, and approver checks tested | pass |
| No real secret in repository evidence | pass |
| Phase 3 local simulation report created | pass |

## Phase 4 Handoff

After Phase 3 passes, Phase 4 should focus on long-running async operation: systemd/tmux worker model, retry policy, task recovery, timeout reminders, periodic PM progress summaries, and multi-project scheduling.
