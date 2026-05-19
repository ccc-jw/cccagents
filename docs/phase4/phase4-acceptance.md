# Phase 4 Acceptance

Date: 2026-05-20

## Gate Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Hermes Gateway/worker durable service | pass | `docs/phase4/linux-ops/service-install.log`: gateway and scheduler are enabled and active |
| Feishu allowlist replaces open access | pass | `docs/phase4/linux-ops/allowlist-check.log`: `GATEWAY_ALLOW_ALL_USERS=false`, `FEISHU_ALLOWED_USERS=[REDACTED]` |
| PM-only Feishu boundary preserved | pass | Feishu contract tests |
| Hermes/server restart recovery | pass | `docs/phase4/linux-ops/restart-recovery.log`: stale running task reconciled to `interrupted` after scheduler restart |
| Interrupted task handling | pass | recovery tests and Linux restart smoke |
| Multi-project isolation | pass | `docs/phase4/linux-ops/multi-project-scheduler.log`: different-project write allowed while same-project write lock blocks concurrent write |
| Same-project write lock | pass | scheduler tests and Linux scheduler smoke |
| PM notifications | pass | PM notification tests and `docs/phase4/linux-ops/pm-notification.log` |
| Approval safety | pass | command policy tests |
| Secret safety | pass | grep verification |
| Local tests | pass | `71 passed in 0.10s` |
| Linux tests | pass | `68 passed in 0.34s` |
| Linux evidence | pass | Phase 4A service/allowlist, Phase 4B restart recovery, Phase 4C scheduler, and Phase 4D PM notification evidence captured |

## Decision

Pending Phase 4 implementation and Linux smoke verification.
