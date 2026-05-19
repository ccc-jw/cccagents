# Phase 3.5 Real Feishu Smoke Report

Date: 2026-05-19

## Status

pass

## Verified Flow

```text
Feishu user -> Hermes Gateway -> PM Agent -> DEV task -> workspace artifact -> PM Agent -> Feishu user
```

## Gateway Mode

Hermes connected to Feishu/Lark through websocket mode:

```text
[Feishu] Connected in websocket mode (feishu)
✓ feishu connected
Gateway running with 1 platform(s)
```

The DNS name `feishu.cccai.store` resolves to the Linux host, but HTTPS webhook mode was not needed for this smoke.

## Feishu PM Send/Receive Evidence

```text
[Feishu] Inbound dm message received ... text='ping pm'
inbound message: platform=feishu ... msg='ping pm'
conversation turn ... platform=feishu ... msg='ping pm'
response ready: platform=feishu ... response=39 chars
[Feishu] Sending response ...
```

## Feishu PM to DEV Evidence

```text
conversation turn ... platform=feishu ...
tool write_file completed
file_exists=true
file_content=1213hello from Feishu PM to DEV
```

The `1213` prefix was part of the Feishu message content. The smoke goal was to prove a Feishu-triggered PM -> DEV workspace write loop, and that passed.

## Evidence Files

- `docs/phase3/linux-ops/feishu-real-env-check.log`
- `docs/phase3/linux-ops/feishu-real-gateway-discovery.log`
- `docs/phase3/linux-ops/feishu-real-gateway.log`
- `docs/phase3/linux-ops/feishu-real-pm-dev-loop.log`

## Security Notes

Real Feishu secrets are stored only on Linux `~/.hermes/.env`. Repository evidence contains only redacted secret placeholders. `GATEWAY_ALLOW_ALL_USERS=true` was used only for smoke validation and must be replaced by a Feishu user allowlist before production use.
