from cccagents.phase4_service import build_gateway_service_unit, build_scheduler_service_unit


def test_gateway_service_unit_is_restartable_and_uses_env_file():
    unit = build_gateway_service_unit(
        user="ubuntu",
        working_directory="/home/ubuntu/cccagents-source",
        env_file="/home/ubuntu/.hermes/.env",
    )

    assert "Description=cccagents Hermes Gateway" in unit
    assert "User=ubuntu" in unit
    assert "WorkingDirectory=/home/ubuntu/cccagents-source" in unit
    assert "EnvironmentFile=/home/ubuntu/.hermes/.env" in unit
    assert "ExecStart=/home/ubuntu/.local/bin/hermes gateway run --accept-hooks" in unit
    assert "Restart=always" in unit
    assert "WantedBy=multi-user.target" in unit
    assert "FEISHU_APP_SECRET" not in unit
    assert "ANTHROPIC_API_KEY" not in unit


def test_scheduler_service_unit_is_restartable_and_project_root_bound():
    unit = build_scheduler_service_unit(
        user="ubuntu",
        working_directory="/home/ubuntu/cccagents-source",
        env_file="/home/ubuntu/.hermes/.env",
        project_root="/home/ubuntu/cccagents/projects",
    )

    assert "Description=cccagents PM Scheduler" in unit
    assert "User=ubuntu" in unit
    assert "WorkingDirectory=/home/ubuntu/cccagents-source" in unit
    assert "EnvironmentFile=/home/ubuntu/.hermes/.env" in unit
    assert "Environment=CCCAGENTS_PROJECT_ROOT=/home/ubuntu/cccagents/projects" in unit
    assert "ExecStart=/usr/bin/env python3 -m cccagents.pm_scheduler" in unit
    assert "Restart=always" in unit
    assert "WantedBy=multi-user.target" in unit
