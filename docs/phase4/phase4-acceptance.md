# Phase 4 Acceptance

Date: 2026-06-24

## Server Inventory

| Field | Value |
| --- | --- |
| Server | `113.142.217.41` (NAT 172.16.0.142), Ubuntu 24.04.1 LTS |
| Project source | `/home/ubuntu/cccagents-source` |
| Runtime root | `/home/ubuntu/cccagents` |
| Hermes env | `/home/ubuntu/.hermes/.env` (chmod 600, owned by ubuntu) |
| SSH | port 20109 → 22 |
| Public HTTP | port 31351 → 80 (cloud-vendor unfiltered) |
| Public HTTPS | port 32945 → 443 (cloud-vendor unfiltered) |
| Claude CLI | 2.1.187 (via `npmmirror.com`) |
| Hermes Agent | 0.17.0 (via `mirrors.aliyun.com/pypi`) |
| Python | 3.12.3, pytest 8.3.4, requests 2.34.2, cryptography 49.0.0 |
| nginx | 1.24.0 (systemd managed) |

## Gate Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Claude Code CLI gates OpenAI-compatible gateway natively | pass | `claude -p "OK" --model gpt-5.5` returns `OK` |
| Hermes chat with custom provider returns OK | pass | `hermes chat --provider custom:cccai --model gpt-5.5` returns `OK` |
| All systemd services enabled/active | pass | `service-install.log`: 4/4 active |
| Local port listeners (80/443/8080) | pass | `listen-ports.log` |
| nginx TLS handshake OK | pass | `curl -sk https://127.0.0.1:443/...` → 200/301 |
| nginx → 127.0.0.1:8080 reverse proxy works | pass | `POST /webhook/feishu` via 127.0.0.1:443 returns 200 |
| Public HTTPS webhook reachable end-to-end | pass | `https://113.142.217.41:32945/webhook/feishu?echostr=...` (encrypted) round-trips with AES-256-CBC; final body decrypts to `{"challenge": "end_to_end_2026"}` |
| Feishu URL-verification challenge handler (plaintext + encrypted) | pass | `tests/test_feishu_webhook_server.py::test_challenge_*` |
| Hermes Gateway/worker durable service | pass | `service-install.log`: `cccagents-hermes-gateway` enabled/active |
| Feishu webhook service durable | pass | `service-install.log`: `cccagents-feishu-webhook` enabled/active |
| PM Scheduler durable | pass | `service-install.log`: `cccagents-pm-scheduler` enabled/active |
| Feishu allowlist (secrets redacted) | pass | `allowlist-check.log`: `GATEWAY_ALLOW_ALL_USERS=false`, all `FEISHU_*` keys redacted |
| Secret safety in evidence | pass | `grep` for `sk-…`, `FEISHU_APP_SECRET=…` in `docs/`, `src/`, `tests/`, `scripts/`, `hermes/` only matches `[REDACTED]` / `<redacted-api-key>` / test fixtures |
| Local + Linux tests | pass | `test-results.log`: 134 passed |
| Health check (18 checks) | pass | `health-check.log`: `ALL CHECKS PASSED` |
| system unit definitions preserved | pass | `systemd-units.log`: 3 cccagents units + nginx site config |

## Pending (Phase 4.5 / external)

| Item | Status | Owner |
| --- | --- | --- |
| Formal TLS certificate (currently self-signed) | pending | user — cloud-vendor free cert or Let's Encrypt |
| Feishu backend URL verification live test | pending | user — fill `https://feishu.cccai.store/webhook/feishu` in Feishu console |
| `FEISHU_ALLOWED_USERS` populated | pending | user — observe `ou_…` from first inbound message, then set allowlist |

## Decision

Core Phase 4 acceptance passed.  All services are durable, secrets are redacted in
evidence, the Feishu webhook endpoint accepts the encrypted URL-verification
challenge end-to-end through the public HTTPS port mapping, and 134/134 unit
tests pass both locally and on the server.  Three externally-owned items remain
before the Feishu integration is end-to-end live (formal cert, console URL
verify, first-message allowlist observation).
