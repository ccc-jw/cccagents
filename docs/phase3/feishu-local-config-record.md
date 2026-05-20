# Phase 3.5 Feishu Local Configuration Record

Date: 2026-05-19

## Purpose

Record the real Feishu/Lark connection configuration in local project evidence without storing real secrets. This record is for future Phase 4 service hardening and recovery work.

## Linux Secret Location

Real Feishu values are stored only on the Linux host:

```text
/home/ubuntu/.hermes/.env
```

File permission configured during smoke:

```text
600
```

Directory permission:

```text
/home/ubuntu/.hermes -> 700
```

## Configured Secret Variables

Repository evidence may only contain names and redacted values:

```text
FEISHU_APP_ID=[REDACTED]
FEISHU_APP_SECRET=[REDACTED]
FEISHU_VERIFICATION_TOKEN=[REDACTED]
FEISHU_ENCRYPT_KEY=[REDACTED]
```

## Temporary Smoke Setting

The real smoke used:

```text
GATEWAY_ALLOW_ALL_USERS=true
```

This is not production safe. It was used only because the first Feishu user id had not yet been allowlisted before the smoke. The observed user id in redacted logs starts with `ou_...`; Phase 4 should replace open access with a Feishu user allowlist.

## Gateway Mode

Hermes Gateway connected Feishu/Lark through websocket mode:

```text
[Feishu] Connected in websocket mode (feishu)
✓ feishu connected
Gateway running with 1 platform(s)
```

Because websocket mode worked, the smoke did not require a public HTTPS webhook callback.

## Reserved HTTPS Callback Address

The DNS name prepared for future webhook or reverse-proxy mode is:

```text
https://feishu.cccai.store/webhook/feishu
```

DNS resolution observed:

```text
feishu.cccai.store -> [REDACTED_SERVER_IP]
```

## Evidence Files

- `docs/phase3/linux-ops/feishu-real-env-check.log`
- `docs/phase3/linux-ops/feishu-real-gateway-config-check.log`
- `docs/phase3/linux-ops/feishu-real-gateway-discovery.log`
- `docs/phase3/linux-ops/feishu-real-gateway.log`
- `docs/phase3/linux-ops/feishu-real-pm-dev-loop.log`

## Production Follow-ups

Before production use:

- Replace `GATEWAY_ALLOW_ALL_USERS=true` with a Feishu user allowlist.
- Run Gateway as a durable service instead of foreground smoke mode.
- Keep real Feishu secrets only in Linux secret/config files.
- Continue saving only redacted evidence to the repository.
- Decide whether HTTPS webhook mode is needed; websocket mode is already proven for Feishu messaging.
