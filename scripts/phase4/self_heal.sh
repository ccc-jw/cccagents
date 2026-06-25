#!/usr/bin/env bash
# cccagents self-heal monitor
#
# Reads the last health-check log and restarts any cccagents service whose
# check has been failing recently.  This is a coarse-grained safety net: it
# complements (not replaces) systemd's per-service Restart=always.
#
# Heuristic: a service is "unhealthy" if the last 3 health-check runs contain
# 2+ FAIL lines matching the service.  This avoids reacting to one-off
# network blips while still catching genuine stuck processes.
#
# Triggered by cccagents-self-heal.timer every 5 minutes.
set -uo pipefail

LOG_FILE="${LOG_FILE:-/var/log/cccagents-health.log}"
SELF_HEAL_LOG="${SELF_HEAL_LOG:-/var/log/cccagents-self-heal.log}"

# Map health-check labels to systemd unit names.
declare -A SERVICE_MAP=(
  ["cccagents-hermes-gateway"]="cccagents-hermes-gateway"
  ["cccagents-pm-scheduler"]="cccagents-pm-scheduler"
  ["cccagents-feishu-webhook"]="cccagents-feishu-webhook"
  ["nginx"]="nginx"
)

mkdir -p "$(dirname "$SELF_HEAL_LOG")"
{
  echo "==== self-heal cycle: $(date -u +%Y-%m-%dT%H:%M:%SZ) ===="
  if [ ! -f "$LOG_FILE" ]; then
    echo "health log missing: $LOG_FILE — skipping"
    exit 0
  fi

  # Look at the last 60 entries (about 5 minutes worth at default cadence).
  recent=$(tail -n 60 "$LOG_FILE" 2>/dev/null || true)
  for label in "${!SERVICE_MAP[@]}"; do
    unit="${SERVICE_MAP[$label]}"
    fails=$(echo "$recent" | grep -cE "FAIL.*$label|FAIL.*$unit" || true)
    if [ "$fails" -ge 2 ]; then
      echo "restart: $unit (fails=$fails in last 60 lines)"
      systemctl restart "$unit" || echo "  restart failed: $unit"
    else
      echo "ok: $unit (fails=$fails)"
    fi
  done
} | tee -a "$SELF_HEAL_LOG" >/dev/null
