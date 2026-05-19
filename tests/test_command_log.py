import json

from cccagents.command_log import CommandLogRecord, append_command_log


def test_append_command_log_writes_json_line(tmp_path):
    path = tmp_path / "projects" / "proj_001" / "08-logs" / "command-log.jsonl"
    record = CommandLogRecord(
        project_id="proj_001",
        task_id="task_001",
        run_id="run_001",
        phase="PHASE_1C",
        agent_role="DEV",
        cwd="/srv/cccagents/workspaces/proj_001/repo",
        command="git status",
        permission_level="L0",
        policy_decision="allow",
        risk_reason="read_only_git_status",
        approval_id=None,
        started_at="2026-05-19T10:00:00+08:00",
        completed_at="2026-05-19T10:00:01+08:00",
        exit_code=0,
        stdout_path="projects/proj_001/08-logs/agent-runs/run_001/stdout.log",
        stderr_path="projects/proj_001/08-logs/agent-runs/run_001/stderr.log",
        redacted=False,
        redaction_reason=None,
    )

    append_command_log(path, record)

    data = json.loads(path.read_text().strip())
    assert data["project_id"] == "proj_001"
    assert data["command"] == "git status"
    assert data["policy_decision"] == "allow"
    assert data["approval_id"] is None
