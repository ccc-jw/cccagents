# Phase 3.5 Acceptance

Date: 2026-05-19

## Gate Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Real Feishu credentials configured on Linux only | pass | `docs/phase3/linux-ops/feishu-real-env-check.log` |
| Hermes Gateway recognizes Feishu/Lark configuration | pass | `docs/phase3/linux-ops/feishu-real-gateway-discovery.log` |
| Hermes Gateway connects to Feishu/Lark websocket mode | pass | `docs/phase3/linux-ops/feishu-real-gateway.log` |
| Feishu inbound message reaches Hermes PM session | pass | `docs/phase3/linux-ops/feishu-real-gateway.log` |
| Hermes responds to Feishu user | pass | `docs/phase3/linux-ops/feishu-real-gateway.log` |
| Feishu-triggered PM -> DEV task writes workspace artifact | pass | `docs/phase3/linux-ops/feishu-real-pm-dev-loop.log` |
| Repository evidence has no real Feishu secret values | pass | grep verification |
| Temporary open allowlist documented | pass | `docs/phase3/feishu-real-smoke-report.md` |

## Decision

Phase 3.5 passes. Real Feishu/Lark messaging is connected to Hermes and can trigger a minimal PM -> DEV task loop. Proceed to Phase 4 long-running async operation with Feishu as the user entry and notification channel.

## Test Evidence

```text
48 passed in 0.12s
```

## Real Feishu Evidence Summary

```text
[Feishu] Connected in websocket mode (feishu)
[Feishu] Inbound dm message received ... text='ping pm'
response ready: platform=feishu ... response=39 chars
tool write_file completed
file_exists=true
file_content=1213hello from Feishu PM to DEV
```

## Open Issues Before Production Use

- Replace `GATEWAY_ALLOW_ALL_USERS=true` with a Feishu user allowlist based on the observed user id.
- Install Gateway as a durable service in Phase 4 instead of foreground smoke mode.
- Add recovery, timeout reminders, progress summaries, and multi-project scheduling in Phase 4.
- Decide whether HTTPS webhook/reverse-proxy mode is needed later; current smoke used Feishu websocket mode successfully.
