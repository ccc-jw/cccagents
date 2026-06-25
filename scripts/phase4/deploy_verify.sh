#!/usr/bin/env bash
# cccagents end-to-end deploy verification
#
# Combines the unit-level E2E smoke with the systemd-level health check.
# Both must pass for the deploy to be considered green.  Use this as a
# post-deploy gate (e.g. run it from CI after `scp` + `systemctl restart`).
#
# Usage:
#   ./scripts/phase4/deploy_verify.sh                       # local
#   SSHPASS=… ./scripts/phase4/deploy_verify.sh --remote user@host [port]
#
# Exit codes:
#   0 = both green
#   1 = one or both failed
#   2 = missing dependency

set -uo pipefail

SSH_TARGET=""
SSH_PORT="${SSH_PORT:-22}"
SSHPASS="${SSHPASS:-}"
if [ "${1:-}" = "--remote" ] && [ -n "${2:-}" ]; then
  SSH_TARGET="$2"
  SSH_PORT="${3:-22}"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

pass()  { printf '%b  ✔%b %s\n' "$GREEN" "$NC" "$1"; }
fail()  { printf '%b  ✗%b %s\n' "$RED"   "$NC" "$1"; }
info()  { printf '%b  ▶%b %s\n' "$BLUE"  "$NC" "$1"; }

# Resolve script directory (so the script works regardless of cwd).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------- Pre-flight ----------
if [ -n "$SSH_TARGET" ] && ! command -v sshpass >/dev/null 2>&1; then
  fail "sshpass not installed (required for --remote)"
  exit 2
fi

# ---------- 1. E2E smoke (local) ----------
info "running E2E smoke (handle_approval_webhook + project state)"
SMOKE_OUT="$(mktemp)"
SMOKE_ENV=(
  PYTHONPATH="${PYTHONPATH:-$(cd "$SCRIPT_DIR/../.." && pwd)/src}"
  PROJECT_ROOT="${PROJECT_ROOT:-/tmp/cccagents-deploy-verify-projects}"
  PROJECT_ID="deploy-verify-$(date +%s)"
  ALLOWED_USER="ou_verify_user"
)
if env "${SMOKE_ENV[@]}" "$SCRIPT_DIR/e2e_smoke.sh" > "$SMOKE_OUT" 2>&1; then
  if grep -qE "E2E smoke: [0-9]+ passed, 0 failed" "$SMOKE_OUT"; then
    pass "E2E smoke passed"
    SMOKE_OK=1
  else
    fail "E2E smoke ran but reported failures — see $SMOKE_OUT"
    SMOKE_OK=0
  fi
else
  fail "E2E smoke failed (exit=$?) — see $SMOKE_OUT"
  SMOKE_OK=0
fi

# ---------- 2. Health check ----------
info "running health check"
HEALTH_ARGS=()
if [ -n "$SSH_TARGET" ]; then
  HEALTH_ARGS=(--remote "$SSH_TARGET" "$SSH_PORT")
fi
HEALTH_OUT="$(mktemp)"
HEALTH_LOG="$(mktemp)"
if [ "${#HEALTH_ARGS[@]}" -gt 0 ]; then
  LOG_FILE="$HEALTH_LOG" "$SCRIPT_DIR/health_check.sh" "${HEALTH_ARGS[@]}" > "$HEALTH_OUT" 2>&1
else
  LOG_FILE="$HEALTH_LOG" "$SCRIPT_DIR/health_check.sh" > "$HEALTH_OUT" 2>&1
fi
HC_EXIT=$?
if [ "$HC_EXIT" -eq 0 ]; then
  HC_OK=1
  pass "health check returned exit 0"
else
  HC_OK=0
  fail "health check returned exit $HC_EXIT"
fi
# Even when the script returns 0, the report line tells us the truth.
if grep -q "ALL CHECKS PASSED" "$HEALTH_OUT"; then
  pass "health check report: ALL CHECKS PASSED"
else
  HC_OK=0
  fail "health check report did not say ALL CHECKS PASSED"
fi

# ---------- Summary ----------
echo
echo "============================================"
if [ "${SMOKE_OK:-0}" -eq 1 ] && [ "${HC_OK:-0}" -eq 1 ]; then
  printf "%bDEPLOY VERIFY: PASS%b\n" "$GREEN" "$NC"
  echo "============================================"
  exit 0
fi
printf "%bDEPLOY VERIFY: FAIL%b\n" "$RED" "$NC"
echo "  E2E smoke log:    $SMOKE_OUT"
echo "  Health check log: $HEALTH_OUT"
echo "============================================"
exit 1
