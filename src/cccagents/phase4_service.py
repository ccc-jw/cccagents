GATEWAY_SERVICE_NAME = "cccagents-hermes-gateway"
SCHEDULER_SERVICE_NAME = "cccagents-pm-scheduler"


def build_gateway_service_unit(user: str, working_directory: str, env_file: str) -> str:
    return f"""[Unit]
Description=cccagents Hermes Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_directory}
EnvironmentFile={env_file}
ExecStart=/home/ubuntu/.local/bin/hermes gateway run --accept-hooks --replace
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""


def build_scheduler_service_unit(
    user: str,
    working_directory: str,
    env_file: str,
    project_root: str,
) -> str:
    return f"""[Unit]
Description=cccagents PM Scheduler
After=network-online.target cccagents-hermes-gateway.service
Wants=network-online.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_directory}
EnvironmentFile={env_file}
Environment=CCCAGENTS_PROJECT_ROOT={project_root}
Environment=PYTHONPATH={working_directory}/src
ExecStart={working_directory}/.venv/bin/python -m cccagents.pm_scheduler
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
