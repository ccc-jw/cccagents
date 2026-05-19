from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class CommandLogRecord:
    project_id: str
    task_id: str
    run_id: str
    phase: str
    agent_role: str
    cwd: str
    command: str
    permission_level: str
    policy_decision: str
    risk_reason: str
    approval_id: str | None
    started_at: str
    completed_at: str
    exit_code: int
    stdout_path: str
    stderr_path: str
    redacted: bool
    redaction_reason: str | None


def append_command_log(path: Path, record: CommandLogRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True))
        handle.write("\n")
