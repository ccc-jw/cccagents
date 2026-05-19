# Phase 4 Acceptance

Date: 2026-05-20

## Gate Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Hermes Gateway/worker durable service | pass | `docs/phase4/linux-ops/service-install.log`: gateway and scheduler are enabled and active |
| Feishu allowlist replaces open access | pass | `docs/phase4/linux-ops/allowlist-check.log`: `GATEWAY_ALLOW_ALL_USERS=false`, `FEISHU_ALLOWED_USERS=[REDACTED]` |
| PM-only Feishu boundary preserved | pass | Feishu contract tests |
| Hermes/server restart recovery | pending | `docs/phase4/linux-ops/restart-recovery.log` |
| Interrupted task handling | pass | recovery tests |
| Multi-project isolation | pending | `docs/phase4/linux-ops/multi-project-scheduler.log` |
| Same-project write lock | pass | scheduler tests |
| PM notifications | pass | PM notification tests |
| Approval safety | pass | command policy tests |
| Secret safety | pass | grep verification |
| Local tests | pass | `68 passed in 0.11s` |
| Linux tests | pass | `68 passed in 0.34s` |
| Linux evidence | partial pass | Phase 4A service and allowlist evidence captured; restart recovery, multi-project, and PM notification live smokes remain pending |

## Decision

Pending Phase 4 implementation and Linux smoke verification.
