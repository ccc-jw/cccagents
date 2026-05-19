#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="${1:-docs/phase4/linux-ops}"
mkdir -p "$OUTPUT_DIR"

{
  date -u +%Y-%m-%dT%H:%M:%SZ
  systemctl is-enabled cccagents-hermes-gateway 2>/dev/null || true
  systemctl is-active cccagents-hermes-gateway 2>/dev/null || true
  systemctl is-enabled cccagents-pm-scheduler 2>/dev/null || true
  systemctl is-active cccagents-pm-scheduler 2>/dev/null || true
} > "$OUTPUT_DIR/service-install.log"

{
  date -u +%Y-%m-%dT%H:%M:%SZ
  if [ -f /home/ubuntu/.hermes/.env ]; then
    grep -E 'GATEWAY_ALLOW_ALL_USERS|FEISHU' /home/ubuntu/.hermes/.env | sed -E 's/(FEISHU_[A-Z_]+=).*/\1[REDACTED]/; s/(ou_)[A-Za-z0-9_-]+/\1[REDACTED]/g'
  else
    printf 'hermes_env=missing\n'
  fi
} > "$OUTPUT_DIR/allowlist-check.log"

if [ -f /home/ubuntu/cccagents/projects/phase4-recovery-smoke/08-logs/restart-recovery.jsonl ]; then
  cp /home/ubuntu/cccagents/projects/phase4-recovery-smoke/08-logs/restart-recovery.jsonl "$OUTPUT_DIR/restart-recovery.log"
else
  {
    date -u +%Y-%m-%dT%H:%M:%SZ
    printf 'restart-recovery evidence pending live smoke\n'
  } > "$OUTPUT_DIR/restart-recovery.log"
fi

if [ -f /home/ubuntu/cccagents/projects/phase4-scheduler-smoke/08-logs/multi-project-scheduler.jsonl ]; then
  cp /home/ubuntu/cccagents/projects/phase4-scheduler-smoke/08-logs/multi-project-scheduler.jsonl "$OUTPUT_DIR/multi-project-scheduler.log"
else
  {
    date -u +%Y-%m-%dT%H:%M:%SZ
    printf 'multi-project-scheduler evidence pending live smoke\n'
  } > "$OUTPUT_DIR/multi-project-scheduler.log"
fi

{
  date -u +%Y-%m-%dT%H:%M:%SZ
  printf 'pm-notification evidence pending live smoke\n'
} > "$OUTPUT_DIR/pm-notification.log"
