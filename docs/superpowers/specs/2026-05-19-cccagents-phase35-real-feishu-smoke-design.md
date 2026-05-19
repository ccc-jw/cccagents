# cccagents Phase 3.5 Real Feishu Smoke Design

Date: 2026-05-19

## Goal

Phase 3.5 connects a real Feishu/Lark bot to Hermes before Phase 4 long-running async work. The goal is to verify that a real Feishu user can reach Hermes through the PM boundary, receive a response, and trigger a minimal PM -> DEV -> PM -> Feishu completion loop.

## Scope

In scope:

- Configure real Feishu App/Bot credentials only on the Linux host.
- Start Hermes Gateway with the Feishu/Lark platform enabled.
- Verify real Feishu inbound messages reach Hermes through Feishu websocket mode.
- Verify Hermes sends a response back to the Feishu user.
- Verify a Feishu user can request a tiny DEV task through PM.
- Verify DEV creates a harmless file in the project workspace.
- Verify PM/Feishu returns completion evidence to the user.
- Save redacted Linux logs and acceptance evidence.

Out of scope:

- Long-running systemd/tmux worker hardening.
- Cross-day task recovery.
- Multi-project scheduling.
- Periodic PM progress reports.
- Production callback/reverse-proxy automation.
- Complex approval matrices.

## Architecture

```text
Feishu user
  -> Feishu/Lark websocket connection
  -> Hermes Gateway
  -> PM Agent session
  -> DEV delegated task / local executor
  -> workspace artifact
  -> PM Agent
  -> Feishu user notification
```

Hermes Feishu Gateway connected through Feishu websocket mode, so the initial smoke did not require the HTTPS event callback URL. The DNS name `feishu.cccai.store` resolves to the Linux host and remains available for future webhook or reverse-proxy modes.

## Real Feishu Configuration

Real secrets are stored only on Linux:

```text
~/.hermes/.env
```

Required values configured for the smoke:

```text
FEISHU_APP_ID=[REDACTED]
FEISHU_APP_SECRET=[REDACTED]
FEISHU_VERIFICATION_TOKEN=[REDACTED]
FEISHU_ENCRYPT_KEY=[REDACTED]
```

Temporary smoke setting:

```text
GATEWAY_ALLOW_ALL_USERS=true
```

This is acceptable only for the short smoke test. After collecting the Feishu user id from logs, Phase 4 or production setup should replace it with a platform allowlist.

## Verification Point 1: Feishu to PM and PM to Feishu

Input sent from Feishu:

```text
ping pm
```

Observed behavior:

```text
[Feishu] Inbound dm message received ... text='ping pm'
inbound message: platform=feishu ... msg='ping pm'
conversation turn ... platform=feishu ... msg='ping pm'
response ready: platform=feishu ... response=39 chars
[Feishu] Sending response ...
```

Conclusion: real Feishu inbound and outbound messaging works through Hermes Gateway.

## Verification Point 2: Feishu to PM to DEV to PM to Feishu

Input sent from Feishu requested DEV to create:

```text
/home/ubuntu/cccagents/workspaces/phase35-feishu-smoke/repo/hello-from-feishu-dev.txt
```

Observed Linux artifact:

```text
file_exists=true
file_content=1213hello from Feishu PM to DEV
```

The `1213` prefix came from the user's Feishu message content. The important smoke result is that Feishu triggered PM, PM delegated to DEV, DEV wrote inside the project workspace, and Hermes produced a completion response.

## Security Notes

- Secrets were written to Linux `~/.hermes/.env`, not repository files.
- Gateway logs are saved with redaction filters.
- Hermes Gateway secret redaction was enabled during the smoke.
- DEV wrote only inside `/home/ubuntu/cccagents/workspaces/phase35-feishu-smoke/repo`.
- The open `GATEWAY_ALLOW_ALL_USERS=true` setting must be replaced by a Feishu user allowlist after smoke validation.

## Acceptance Gates

| Gate | Required Result |
| --- | --- |
| Feishu credentials configured on Linux only | pass |
| Hermes Gateway connects to Feishu/Lark | pass |
| Feishu inbound message reaches Hermes | pass |
| Hermes responds to Feishu user | pass |
| Feishu-triggered PM -> DEV task writes workspace artifact | pass |
| Logs and repository evidence contain no real secrets | pass |
| Temporary open allowlist is documented | pass |

## Phase 4 Handoff

Phase 4 should build on this real Feishu channel and focus on durable async operation: gateway service management, user allowlists, task recovery, PM progress summaries, multi-project scheduling, timeout reminders, and safe approval gates.
