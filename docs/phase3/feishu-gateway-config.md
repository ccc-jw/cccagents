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
