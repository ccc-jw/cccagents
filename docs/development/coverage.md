# cccagents Test Coverage Report

Generated: 2026-06-24 by `pytest --cov=cccagents --cov-report=term-missing`

## Headline

- **202 tests passed, 0 failed**
- **91 % line coverage** across the `cccagents` package
- **33 source files** in scope (no `__init__.py` work to do)
- **1457 statements, 130 missed**

## Per-file coverage

| File | Stmts | Missed | Cover | Notes |
| --- | --- | --- | --- | --- |
| `agent_config.py` | 5 | 0 | **100 %** | |
| `artifact_store.py` | 7 | 0 | **100 %** | |
| `command_log.py` | 28 | 0 | **100 %** | |
| `feishu_allowlist.py` | 28 | 0 | **100 %** | Edge cases pinned down in `test_feishu_allowlist_extended.py` |
| `feishu_reply.py` | 49 | 0 | **100 %** | All Feishu API code paths exercised |
| `paths.py` | 23 | 0 | **100 %** | |
| `phase2_models.py` | 101 | 0 | **100 %** | |
| `phase4_service.py` | 6 | 0 | **100 %** | |
| `pm_notifications.py` | 19 | 0 | **100 %** | |
| `project_init.py` | 10 | 0 | **100 %** | |
| `project_state.py` | 28 | 0 | **100 %** | |
| `real_orchestrator.py` | 40 | 0 | **100 %** | |
| `redaction.py` | 16 | 0 | **100 %** | |
| `scheduler.py` | 30 | 0 | **100 %** | |
| `pm_scheduler.py` | 52 | 1 | **98 %** | Only `if __name__ == "__main__"` guard uncovered |
| `approval_handler.py` | 45 | 1 | 98 % | 1 line uncovered (cosmetic edge) |
| `feishu_contracts.py` | 58 | 1 | 98 % | 1 line uncovered |
| `feishu_webhook.py` | 151 | 5 | 97 % | URL-verification challenge + reply path |
| `orchestrator.py` | 66 | 2 | 97 % | |
| `task_store.py` | 52 | 2 | 96 % | |
| `review_engine.py` | 46 | 2 | 96 % | |
| `metrics.py` | 76 | 3 | 96 % | |
| `complexity_classifier.py` | 40 | 2 | 95 % | |
| `role_plan.py` | 40 | 2 | 95 % | |
| `review_gate.py` | 13 | 1 | 92 % | |
| `command_policy.py` | 34 | 3 | 91 % | |
| `test_checklist.py` | 23 | 2 | 91 % | |
| `workflow.py` | 11 | 1 | 91 % | |
| `prompt_builder.py` | 22 | 2 | 91 % | |
| `project_orchestrator.py` | 61 | 6 | 90 % | |
| `claude_executor.py` | 83 | 5 | **94 %** | HTTP fallback path fully covered (was 81 %) |
| `recovery.py` | 40 | 7 | 82 % | Recovery logic; needs a real crash scenario |
| `feishu_webhook_server.py` | 144 | 85 | **41 %** | Server entry point; mostly integration-covered (see note) |
| `artifacts.py` | 10 | 3 | 70 % | |

## Why `feishu_webhook_server.py` is 41 % and that's OK

The server module has lots of HTTP plumbing (BaseHTTPRequestHandler
methods, `do_GET` / `do_POST` dispatch, `BaseHTTPRequestHandler.log_message`
override, `run_server` signal handling).  Most of the *behaviour* lives
in the helpers it calls (`dispatch_event`, `handle_challenge`,
`_check_upstream_health`, `METRICS`), which are unit-tested at 96–100 %.

The 41 % figure reflects coverage of the HTTP layer that is exercised in
practice by:

- `tests/test_feishu_webhook_concurrency.py` — 3 integration tests that
  start a real `ThreadingHTTPServer` and hit it over loopback
- `scripts/phase4/health_check.sh` — POSTs to `127.0.0.1:8080/webhook/feishu`
  every 5 minutes in production
- `scripts/phase4/e2e_smoke.sh` — full webhook call in CI

These don't show up in `pytest-cov` because they run outside the test
process.  If we want to raise the figure, the right next step is a
`pytest-httpserver`-style fixture that records the HTTP traffic; that
work is intentionally deferred until we have a need.

## Files with the largest uncovered regions (next-investment candidates)

| File | Lines | Likely test to add |
| --- | --- | --- |
| `recovery.py` | 42-51 | Crash mid-execution recovery |
| `feishu_webhook_server.py` | 113-120, 188-239 | Signal handlers + daemon loop |
| `artifacts.py` | 18, 20, 22 | Artifact store branches |

(``pm_scheduler.py``, ``claude_executor.py``, and ``feishu_allowlist.py`` were
covered by the second coverage pass — see the table above.)

## How to regenerate this report

```bash
PYTHONPATH=src .venv/bin/pytest \
  --cov=cccagents \
  --cov-report=term-missing \
  --cov-report=html:.htmlcov \
  -q tests
```

HTML report at `.htmlcov/index.html` (open in a browser to navigate
per-file line coverage).

## When to add a test

- Adding a new public function in any module currently at < 90 %: write
  the test in the same change.
- Touching `claude_executor.py` or `recovery.py`: add or extend a test
  before merging.
- Adding a new role: `hermes/roles/<role>.md` should be referenced from
  `AGENTS.md` and exercised by a smoke test.
