#!/usr/bin/env bash
# cccagents backup
#
# Bundles the deployable state into a single tarball so we can rebuild the
# host from scratch if the disk dies.  Captures:
#   - /home/ubuntu/.hermes/.env                       (secrets!)
#   - /home/ubuntu/.hermes/config.yaml
#   - /home/ubuntu/cccagents-source/                   (source tree, no venv)
#   - /etc/systemd/system/cccagents-*.service         (unit overrides)
#   - /etc/nginx/sites-enabled/feishu-cccagents       (proxy config)
#   - /etc/nginx/ssl/                                  (TLS cert + key)
#   - /var/log/cccagents-*.log                         (last health logs)
#
# Output: /var/backups/cccagents/cccagents-<UTC-timestamp>.tar.gz
# Retention: keeps the last 7 backups, deletes older.
#
# Run as root (needs to read /etc/* and write to /var/backups).
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/cccagents}"
PROJECT_SOURCE="${PROJECT_SOURCE:-/home/ubuntu/cccagents-source}"
HERMES_HOME="${HERMES_HOME:-/home/ubuntu/.hermes}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
RETENTION_COUNT="${RETENTION_COUNT:-7}"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
out_file="$BACKUP_DIR/cccagents-${timestamp}.tar.gz"

mkdir -p "$BACKUP_DIR"

if [ ! -d "$PROJECT_SOURCE" ]; then
  echo "ERROR: project source not found at $PROJECT_SOURCE" >&2
  exit 1
fi

echo "creating backup: $out_file"
tar czf "$out_file" \
  --exclude='.venv' --exclude='__pycache__' --exclude='.pytest_cache' \
  --exclude='.claude/worktrees' --exclude='.git' \
  -C / \
  "$HERMES_HOME/.env" \
  "$HERMES_HOME/config.yaml" \
  "home/ubuntu/cccagents-source" \
  "etc/systemd/system/cccagents-hermes-gateway.service" \
  "etc/systemd/system/cccagents-pm-scheduler.service" \
  "etc/systemd/system/cccagents-feishu-webhook.service" \
  "etc/systemd/system/cccagents-health-check.service" \
  "etc/systemd/system/cccagents-health-check.timer" \
  "etc/systemd/system/cccagents-self-heal.service" \
  "etc/systemd/system/cccagents-self-heal.timer" \
  "etc/nginx/sites-enabled/feishu-cccagents" \
  "etc/nginx/ssl" \
  2>/dev/null || true

# Also grab the log files (may be missing on a brand-new host).
if compgen -G "/var/log/cccagents-*.log" >/dev/null; then
  tar czf "$out_file.ccagents-logs.tmp" -C / var/log/cccagents-health.log var/log/cccagents-self-heal.log 2>/dev/null || true
  if [ -f "$out_file.ccagents-logs.tmp" ]; then
    # Append logs into the main archive.
    tar -Af "$out_file" -C / var/log/cccagents-health.log var/log/cccagents-self-heal.log 2>/dev/null || true
    rm -f "$out_file.ccagents-logs.tmp"
  fi
fi

# Permissions: backup is sensitive (contains .env).  Restrict to root.
chmod 600 "$out_file"
chown root:root "$out_file"

size=$(du -h "$out_file" | cut -f1)
echo "backup done: $out_file ($size)"

# Retention: keep only the last N backups.
if [ -d "$BACKUP_DIR" ]; then
  cd "$BACKUP_DIR" || exit 1
  ls -1t cccagents-*.tar.gz 2>/dev/null | tail -n +$((RETENTION_COUNT + 1)) | while read -r old; do
    if [ -n "$old" ]; then
      echo "removing old backup: $old"
      rm -f -- "$old"
    fi
  done
fi

# Also enforce max-age as a fallback in case many backups pile up.
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'cccagents-*.tar.gz' -mtime "+$RETENTION_DAYS" -delete || true

echo "current backups:"
ls -lh "$BACKUP_DIR"/cccagents-*.tar.gz 2>/dev/null | tail -5 || echo "  (none)"
