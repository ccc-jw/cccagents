# Phase 3 Acceptance

Date: 2026-05-19

## Gate Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Hermes Feishu Gateway capability discovered | pass | `docs/phase3/linux-ops/feishu-gateway-capability.log` |
| Feishu config shape documented without secrets | pass | `docs/phase3/feishu-gateway-config.md` |
| PM-only message routing contract tested | pass | `tests/test_feishu_contracts.py` |
| Approval action contract tested | pass | `tests/test_feishu_contracts.py` |
| Signature, timestamp, replay, and approver checks tested | pass | `tests/test_feishu_contracts.py` |
| No real secret in repository evidence | pass | grep verification |
| Phase 3 local simulation report created | pass | `docs/phase3/feishu-local-simulation-report.md` |

## Decision

Phase 3 passes local contract validation. Proceed to Phase 4 long-running async operation after configuring real Feishu credentials only on the Linux host.

## Test Evidence

```text
48 passed in 0.12s
```

Focused Feishu simulation:

```text
7 passed in 0.01s
```

## Linux Evidence

Hermes Gateway capability was collected on Linux. Linux Python test execution could not run because pytest is not installed in the Linux repository copy, so the interim Feishu simulation evidence is the Mac worktree pytest run after syncing Phase 3 files to Linux.

## Open Issues

- Real Feishu app credentials are not committed and must be configured only on the Linux host.
- Production Feishu callback delivery requires an externally reachable callback endpoint or gateway deployment mode.
- Linux repository copy still needs repeatable Python test setup before Linux-side pytest can become blocking evidence.
