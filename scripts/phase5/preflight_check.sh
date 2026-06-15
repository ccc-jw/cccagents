#!/usr/bin/env bash
set -euo pipefail

HERMES_ENV="${HERMES_ENV:-/home/ubuntu/.hermes/.env}"
HERMES_CONFIG="${HERMES_CONFIG:-/home/ubuntu/.hermes/config.yaml}"

python3 --version
node --version
npm --version
claude --version
hermes --help >/dev/null

python3 - <<'PY'
import socket
socket.create_connection(("cccai.store", 80), timeout=5).close()
print("cccai.store reachable")
PY

test -f "$HERMES_ENV"
test -f "$HERMES_CONFIG"
test "$(stat -c '%a' "$HERMES_ENV" 2>/dev/null || stat -f '%Lp' "$HERMES_ENV")" = "600"

grep -q "gpt-5.5" "$HERMES_CONFIG"
grep -q "cccai.store/v1" "$HERMES_CONFIG"
grep -q "terminal" "$HERMES_CONFIG"
grep -q "GATEWAY_ALLOW_ALL_USERS=false" "$HERMES_ENV"

printf 'phase5 preflight PASS\n'
