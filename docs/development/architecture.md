# cccagents Architecture

> High-level system architecture for new contributors.  Read this end-to-end
> before touching any code — the design is opinionated and most of it is
> pinned down by tests.

## One-line summary

A Feishu user talks to the PM agent.  PM orchestrates a multi-role team
(PDM / RES / ARCH / DEV / TEST / SEC) by invoking Claude Code CLI as a
subprocess per role.  All artifacts are stored on the local filesystem
under `/home/ubuntu/cccagents/projects/<project_id>/`.

## End-to-end request flow

```
            ┌─────────────┐
            │  Feishu     │
            │  user (p2p) │
            └──────┬──────┘
                   │ HTTPS POST
                   │ GET  /webhook/feishu  (URL-verification challenge)
                   │ POST /webhook/feishu  (im.message.receive_v1 / card_action)
                   ▼
       ┌──────────────────────┐
       │  nginx  (port 443)   │  TLS termination + reverse proxy
       │  /etc/nginx/sites-   │  80 → 301 → 443
       │  enabled/feishu-…    │  /webhook/* → 127.0.0.1:8080
       └──────────┬───────────┘
                  │ proxy_pass (http://127.0.0.1:8080)
                  ▼
       ┌──────────────────────────────────┐
       │  cccagents-feishu-webhook        │  ThreadingHTTPServer (10 concurrent)
       │  src/cccagents/feishu_webhook_   │  - GET  → handle_challenge
       │         server.py                │           (plain / AES-256-CBC)
       │                                  │  - POST → dispatch_event
       │  /healthz → upstream probe      │
       └──────────┬───────────────────────┘
                  │ dispatch_event
                  ▼
       ┌──────────────────────────────────┐
       │  cccagents/feishu_webhook.py     │  Router:
       │  - handle_inbound_message        │  - im.message.receive_v1
       │  - handle_approval_webhook       │    → handle_inbound_message → PM
       │  - handle_challenge              │  - card_action / card_action.trigger
       │                                  │    → handle_approval_webhook → Approval
       │  Reply path:                     │  - url_verification
       │  - reply_to_feishu  (Open API)    │    → handle_challenge (echoes)
       └──────────┬───────────────────────┘
                  │
   ┌──────────────┼─────────────────────────┐
   │              │                         │
   ▼              ▼                         ▼
[PM route]   [Approval flow]           [Challenge]
build_pm_route  process_approval_action   _feishu_decrypt
project_id=""  loads project_state.json   _feishu_encrypt
payload:        writes approval-events     (SHA-256(encrypt_key)
  feishu_…       .jsonl                    + AES-256-CBC
  text         updates project state       + PKCS7(128) padding)
  received_at
   │
   ▼
┌──────────────────────────┐
│ cccagents/pm_scheduler   │  Polls /home/ubuntu/cccagents/projects
│  Every 60 s              │  Picks up new tasks, dispatches them to
│  systemd service         │  DEV / TEST / SEC roles
└──────────┬───────────────┘
           │ dispatch (project_id, role, …)
           ▼
┌──────────────────────────────────┐
│ cccagents/claude_executor.py     │  subprocess.run(claude, -p <prompt>, --allowedTools …)
│ run_claude_task(request)         │  ANTHROPIC_BASE_URL=… env override
│                                  │  Writes prompt.md / stdout.txt / stderr.txt / result.json
└──────────┬───────────────────────┘
           │ subprocess
           ▼
┌──────────────────────────────────┐
│  Claude Code CLI  (npm global)   │  Tools: Read, Write, … (per role allowlist)
│  Talks to ANTHROPIC_BASE_URL     │  Project-scoped workspace:
│  = https://cccai.store/v1         │  /home/ubuntu/cccagents/workspaces/<id>/repo
└──────────┬───────────────────────┘
           │ HTTPS
           ▼
   ┌───────────────────┐
   │ OpenAI-compatible │  ANTHROPIC_API_KEY (Bearer)
   │ gateway           │  Model: gpt-5.5
   │ cccai.store        │
   └───────────────────┘
```

## Role contract (AGENTS.md)

The `AGENTS.md` file in the source root is injected by Hermes Gateway as
the system prompt for every agent invocation.  It pins down the
**Feishu → PM** boundary:

> Feishu users only talk to PM.  PM is the only user-facing entry point and
> notification exit.  Do not let PDM, RES, ARCH, DEV, TEST, or SEC directly
> contact the Feishu user.

This is enforced by:

1. `src/cccagents/feishu_webhook.py:handle_inbound_message` — always
   returns `target_role="PM"`.
2. `tests/test_pm_only_boundary.py` — every test asserts that
   `target_role == "PM"` for inbound messages, never one of the forbidden
   roles (PDM / RES / ARCH / DEV / TEST / SEC).
3. `hermes/roles/*.md` — when delegating, PM picks one of the role files
   as the *behavioural* source; the Feishu boundary still holds.

## Module map

| File | Role |
| --- | --- |
| `src/cccagents/feishu_webhook_server.py` | HTTP ingress, challenge handler, /healthz, ThreadingHTTPServer |
| `src/cccagents/feishu_webhook.py` | Event router + parsers (message, approval, challenge) |
| `src/cccagents/feishu_reply.py` | Outbound: tenant_access_token cache + `im/v1/messages` send |
| `src/cccagents/feishu_contracts.py` | Frozen dataclasses for Feishu types + validation rules |
| `src/cccagents/claude_executor.py` | `subprocess.run` of the local `claude` CLI; writes 4 artefacts per run |
| `src/cccagents/real_orchestrator.py` | Top-level orchestration across PM → DEV → … roles |
| `src/cccagents/pm_scheduler.py` | systemd-managed cron that watches for new project tasks |
| `src/cccagents/approval_handler.py` | Approval lifecycle: pending → approved/rejected with allowlist check |
| `src/cccagents/project_state.py` | Frozen dataclass for `project-state.json` (status, retries, etc.) |
| `src/cccagents/redaction.py` | Regex-based secret scrubber for logs and Feishu replies |
| `src/cccagents/complexity_classifier.py` | Heuristic for S0 / S1 / S2 / S3 task routing |
| `src/cccagents/role_plan.py` | Builds a role-by-role plan from a classification |
| `src/cccagents/scheduler.py` | Multi-project write-lock + dispatch decisions |
| `src/cccagents/paths.py` | `ProjectPaths` helper for workspace / project / log layout |
| `hermes/roles/*.md` | Source-of-truth behaviour for each role |
| `scripts/phase4/*.sh` | Deployment, health, smoke, backup, secret rotation |
| `scripts/phase4/*.service / .timer` | systemd units for periodic health and self-heal |

## Where the state lives

```
/home/ubuntu/
├── .hermes/
│   ├── .env                 # secrets (chmod 600, owned by ubuntu)
│   └── config.yaml         # Hermes custom provider config
├── cccagents-source/        # this repo
└── cccagents/
    ├── projects/
    │   └── <project_id>/
    │       ├── project-state.json
    │       ├── role-plan.json
    │       └── 08-logs/
    │           ├── command-log.jsonl
    │           ├── approval-events.jsonl
    │           └── hermes-runs/<run_id>/
    │               ├── prompt.md
    │               ├── stdout.txt
    │               ├── stderr.txt
    │               └── result.json
    └── workspaces/
        └── <project_id>/repo   # where DEV writes code
```

## Service topology

| Unit | Type | Purpose |
| --- | --- | --- |
| `cccagents-hermes-gateway.service` | `simple` | Hermes Agent (PM role), running messaging + cron |
| `cccagents-pm-scheduler.service` | `simple` | Watches `/home/ubuntu/cccagents/projects` for new tasks every 60 s |
| `cccagents-feishu-webhook.service` | `simple` | HTTP webhook ingress (ThreadingHTTPServer) |
| `nginx.service` | `simple` | TLS termination + reverse proxy |
| `cccagents-health-check.{service,timer}` | `oneshot` + timer | 18 checks every 5 min → `/var/log/cccagents-health.log` |
| `cccagents-self-heal.{service,timer}` | `oneshot` + timer | Reads health log, restarts failing services |

## Trust boundaries

| Boundary | Defence |
| --- | --- |
| Internet → nginx | TLS, server_name allowlist, body size limit |
| nginx → webhook | `proxy_set_header X-Real-IP` (audit), 30 s read timeout |
| Internet → webhook handler | (in-process) allowlist check on `FEISHU_ALLOWED_USERS` |
| Inbound message → role | **PM only** (enforced in `handle_inbound_message`) |
| User → approval | allowlist + signature + replay protection in `FeishuSecurityContext` |
| DEV → host | `claude --allowedTools <narrow list>` (per role, not `--dangerously-skip-permissions`) |
| Logs | `redaction.redact_text` scrubs API keys, tokens, secrets before writing |
| .env file | chmod 600, owned by ubuntu, never committed |

## Common modification paths

| You want to … | Touch these files |
| --- | --- |
| Add a new event type from Feishu | `feishu_webhook.py:dispatch_event` + a new handler + `SUPPORTED_EVENT_TYPES` |
| Change the allowlist check | `feishu_contracts.py:validate_approval_action` (already covers most of it) |
| Add a new role | `hermes/roles/<role>.md` + update `AGENTS.md` mention + classification logic |
| Change how Claude is invoked | `claude_executor.py:run_claude_task` + `claude_executor_extended` tests |
| Tweak the dispatcher | `pm_scheduler.py` + `real_orchestrator.py` |
| Add a new deployment check | `scripts/phase4/health_check.sh` (one new `pass`/`fail` block) |

## When you make a change, in this order

1. Write or extend a test first.
2. Make the test fail.
3. Implement until it passes.
4. Run the full test suite — `154 passed` is the floor.
5. Run `scripts/phase4/deploy_verify.sh --remote …` before declaring done.
6. Update the relevant `docs/phase*/` or `docs/operations/` page.

If the test count drops below the floor or `deploy_verify` fails, do not
ship.
