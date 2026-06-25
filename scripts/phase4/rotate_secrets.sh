#!/usr/bin/env bash
# cccagents secret rotation
#
# Replaces one or more secrets in /home/ubuntu/.hermes/.env, backs up the
# previous version, and restarts the services that consume them.  Use this
# after a teammate offboards, when a Feishu app credential leaks, or
# periodically as a hygiene measure.
#
# Usage (must run as root; writes to /home/ubuntu/.hermes/.env which is
# owned by ubuntu):
#
#   SSHPASS=… ./scripts/phase4/rotate_secrets.sh --remote root@host [port] \
#     --set ANTHROPIC_API_KEY=sk-new-... \
#     --set FEISHU_APP_SECRET=...
#
# At least one --set is required.  --unset removes a variable.  The
# previous .env is copied to /var/backups/cccagents/secrets-<ts>.env.bak
# before any change.
set -euo pipefail

SSH_TARGET=""
SSH_PORT="${SSH_PORT:-22}"
SSHPASS="${SSHPASS:-}"

declare -a SETS=()
declare -a UNSETS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --remote)
      SSH_TARGET="${2:-}"
      shift 2
      ;;
    --port)
      SSH_PORT="${2:-}"
      shift 2
      ;;
    --set)
      SETS+=("${2:-}")
      shift 2
      ;;
    --unset)
      UNSETS+=("${2:-}")
      shift 2
      ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 2
      ;;
  esac
done

if [ ${#SETS[@]} -eq 0 ] && [ ${#UNSETS[@]} -eq 0 ]; then
  echo "no --set or --unset given; nothing to do" >&2
  exit 2
fi

run() {
  if [ -z "$SSH_TARGET" ]; then
    bash -c "$1"
  else
    sshpass -p "$SSHPASS" ssh -p "$SSH_PORT" \
      -o StrictHostKeyChecking=no \
      -o PreferredAuthentications=password -o PubkeyAuthentication=no \
      "$SSH_TARGET" "$1"
  fi
}

# 1. Back up the existing .env (overwrite previous backup if any).
ts="$(date -u +%Y%m%dT%H%M%SZ)"
backup_path="/var/backups/cccagents/secrets-${ts}.env.bak"
run "mkdir -p /var/backups/cccagents && cp -p /home/ubuntu/.hermes/.env '$backup_path' && chmod 600 '$backup_path'"
echo "backup written: $backup_path"

# 2. Apply each --set and --unset.
set_cmd=""
for kv in "${SETS[@]}"; do
  key="${kv%%=*}"
  val="${kv#*=}"
  # Escape single quotes for the inner single-quoted shell arg.
  esc_val="${val//\'/\'\\\'\'}"
  set_cmd+="printf '%s=%s\\n' '$key' '$esc_val' >> /home/ubuntu/.hermes/.env.tmp; "
done
# 3. Remove existing occurrences of any key we're setting, then append new.
remove_cmd=""
for kv in "${SETS[@]}"; do
  key="${kv%%=*}"
  remove_cmd+="sed -i '/^${key}=/d' /home/ubuntu/.hermes/.env; "
done
for key in "${UNSETS[@]}"; do
  remove_cmd+="sed -i '/^${key}=/d' /home/ubuntu/.hermes/.env; "
done

run "set -e; cp /home/ubuntu/.hermes/.env /home/ubuntu/.hermes/.env.tmp; \
     $remove_cmd \
     $set_cmd \
     if [ -f /home/ubuntu/.hermes/.env.tmp ]; then cat /home/ubuntu/.hermes/.env.tmp >> /home/ubuntu/.hermes/.env; rm /home/ubuntu/.hermes/.env.tmp; fi; \
     chmod 600 /home/ubuntu/.hermes/.env; chown ubuntu:ubuntu /home/ubuntu/.hermes/.env"

# 4. Reload the services that depend on the env.
echo "restarting services…"
for svc in cccagents-hermes-gateway cccagents-pm-scheduler cccagents-feishu-webhook; do
  run "systemctl reload-or-restart $svc" || run "systemctl restart $svc"
  echo "  reloaded: $svc"
done

# 5. Sanity check — re-run health and print which keys were set/unset.
echo
echo "applied changes:"
for kv in "${SETS[@]}"; do
  key="${kv%%=*}"
  echo "  SET   $key"
done
for key in "${UNSETS[@]}"; do
  echo "  UNSET $key"
done

echo
echo "current .env (redacted):"
run "sed -E 's/(KEY|SECRET|TOKEN)=.*/\1=[REDACTED]/' /home/ubuntu/.hermes/.env"

echo
echo "rotation done.  Backup: $backup_path"
