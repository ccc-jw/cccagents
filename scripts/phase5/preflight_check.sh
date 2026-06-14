#!/usr/bin/env bash
set -euo pipefail

# phase5 preflight check
# Verifies core dependencies, network, env config, and model/gateway settings.

HERMES_ENV="${HERMES_ENV:-/home/ubuntu/.env}"
HERMES_CONFIG="${HERMES_CONFIG:-/home/ubuntu/.hermes/config.yaml}"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

# --- dependency versions ---
python3 --version || fail "python3 not found"
node --version    || fail "node not found"
npm --version     || fail "npm not found"
claude --version  || fail "claude CLI not found"
hermes --help     || fail "hermes not found"

# --- network: cccai.store:80 reachable ---
if ! timeout 5 bash -c 'echo > /dev/tcp/cccai.store/80' 2>/dev/null; then
  fail "cccai.store:80 unreachable within 5s"
fi

# --- .env file ---
[[ -f "$HERMES_ENV" ]] || fail ".env not found at $HERMES_ENV"
perm=$(stat -c '%a' "$HERMES_ENV" 2>/dev/null || stat -f '%Lp' "$HERMES_ENV" 2>/dev/null)
[[ "$perm" == "600" ]] || fail ".env permissions are $perm, expected 600"

# --- config.yaml required entries ---
[[ -f "$HERMES_CONFIG" ]] || fail "config.yaml not found at $HERMES_CONFIG"

grep -q 'gpt-5.5'              "$HERMES_CONFIG" || fail "config.yaml missing gpt-5.5"
grep -q 'cccai.store/v1'       "$HERMES_CONFIG" || fail "config.yaml missing cccai.store/v1 endpoint"
grep -q 'terminal'             "$HERMES_CONFIG" || fail "config.yaml missing terminal"
grep -q 'GATEWAY_ALLOW_ALL_USERS=false' "$HERMES_CONFIG" || fail "config.yaml missing GATEWAY_ALLOW_ALL_USERS=false"

printf 'phase5 preflight PASS\n'
