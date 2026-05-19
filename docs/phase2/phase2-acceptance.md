# Phase 2 Acceptance

Date: 2026-05-19

## Gate Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Hermes installed on Linux | pass | `docs/phase2/linux-ops/hermes-install.log`, `docs/phase2/hermes-install-checklist.md` |
| Hermes doctor has no blocking issue | pass | `docs/phase2/hermes-capability-report.md` |
| Hermes OpenAI-compatible model works | pass | `docs/phase2/hermes-openai-compat-gate.md`, `docs/phase2/linux-ops/hermes-openai-v1-retry.log` |
| Hermes role definitions exist | pass | `hermes/roles/`, `tests/test_hermes_roles.py` |
| Hermes can route a minimal PM -> DEV task | pass | `docs/phase2/linux-ops/hermes-local-loop.log` |
| Claude Code CLI executor works under Hermes flow | pass | `docs/phase2/hermes-local-loop-report.md` |
| Project artifacts are project_id isolated | pass | `/home/ubuntu/cccagents/workspaces/phase2-hermes-smoke/repo`, `/home/ubuntu/cccagents/projects/phase2-hermes-smoke/` |
| No real API key in committed evidence | pass | local grep verification; matches were redacted placeholders, command templates, or test fixtures only |

## Decision

Phase 2 passes. Proceed to Phase 3 Feishu integration.

## Accepted Phase 2 Scope

- Hermes is installed and usable on the Linux host.
- Hermes can call the user OpenAI-compatible model gateway when `model.base_url` includes `/v1`.
- PM/PDM/RES/ARCH/DEV/TEST/SEC role contracts exist as Hermes-facing role definitions.
- Claude Code CLI executor protocol is documented with request fields, environment mapping, path boundaries, audit logs, and secret rules.
- Local no-Feishu PM -> DEV smoke loop passes.
- L1 project-local Claude Code CLI automation should use explicit tool allowlists such as `--allowedTools Read,Write`; do not use `--dangerously-skip-permissions` for the executor default.

## Test Evidence

Local test suite:

```text
41 passed in 0.16s
```

Focused Phase 2 tests are included in the full run:

```text
tests/test_hermes_roles.py
tests/test_claude_executor.py
tests/test_executor_protocol_doc.py
tests/test_agent_config.py
```

## Open Issues

- Linux repository copy does not currently have a Python test virtualenv, so Python tests were run in the Mac worktree after syncing evidence back. This does not block Phase 3, but Phase 3 should add repeatable Linux-side test setup if Hermes will run project checks directly.
- Feishu Gateway is not configured in Phase 2 by design. Phase 3 must verify Feishu app credentials, callback/event handling, PM-only user entry, and message redaction.
- Hermes role files are repository role contracts, not yet fully wired into a production Hermes Gateway routing policy. Phase 3 should map Feishu PM messages to Hermes role dispatch explicitly.
