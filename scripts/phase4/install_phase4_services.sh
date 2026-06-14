#!/usr/bin/env bash
set -euo pipefail

PROJECT_SOURCE="${PROJECT_SOURCE:-/home/ubuntu/cccagents-source}"
PROJECT_ROOT="${PROJECT_ROOT:-/home/ubuntu/cccagents/projects}"
HERMES_ENV="${HERMES_ENV:-/home/ubuntu/.env}"
RUN_USER="${RUN_USER:-ubuntu}"
UNIT_DIR="${UNIT_DIR:-/tmp/cccagents-systemd-units}"

mkdir -p "$UNIT_DIR"

cat > "$UNIT_DIR/cccagents-hermes-gateway.service" <<EOF
[Unit]
Description=cccagents Hermes Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$PROJECT_SOURCE
EnvironmentFile=$HERMES_ENV
ExecStart=/home/ubuntu/.local/bin/hermes gateway run --accept-hooks --replace
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > "$UNIT_DIR/cccagents-pm-scheduler.service" <<EOF
[Unit]
Description=cccagents PM Scheduler
After=network-online.target cccagents-hermes-gateway.service
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$PROJECT_SOURCE
EnvironmentFile=$HERMES_ENV
Environment=CCCAGENTS_PROJECT_ROOT=$PROJECT_ROOT
Environment=PYTHONPATH=$PROJECT_SOURCE/src
ExecStart=$PROJECT_SOURCE/.venv/bin/python -m cccagents.pm_scheduler
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

printf 'unit_dir=%s\n' "$UNIT_DIR"
printf 'gateway_unit=%s\n' "$UNIT_DIR/cccagents-hermes-gateway.service"
printf 'scheduler_unit=%s\n' "$UNIT_DIR/cccagents-pm-scheduler.service"
printf 'install_hint=review units, then copy to /etc/systemd/system and run systemctl daemon-reload enable --now\n'
