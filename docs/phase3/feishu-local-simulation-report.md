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

## Linux Note

Linux repository copy currently lacks pytest, so the Linux command recorded `/usr/bin/python3: No module named pytest`. The accepted interim simulation evidence is the same command run in the Mac worktree after syncing the Feishu contract code to Linux.

## Secret Handling

No real Feishu app secret, verification token, encrypt key, API key, or authorization header is stored in repository evidence.
