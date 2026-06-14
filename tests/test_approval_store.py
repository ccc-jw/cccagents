import json
from pathlib import Path

from cccagents.approval_store import ApprovalStore, ApprovalRecord


def test_approval_store_saves_and_loads(tmp_path):
    store = ApprovalStore(tmp_path / "approvals.jsonl")

    record = ApprovalRecord(
        project_id="demo",
        task_id="task-1",
        action="approve",
        feishu_user_id="user-1",
        timestamp="2026-06-13T10:00:00Z",
    )

    store.save(record)

    records = store.load_all()
    assert len(records) == 1
    assert records[0].project_id == "demo"
    assert records[0].action == "approve"


def test_approval_store_loads_multiple_records(tmp_path):
    store = ApprovalStore(tmp_path / "approvals.jsonl")

    record1 = ApprovalRecord(
        project_id="demo",
        task_id="task-1",
        action="approve",
        feishu_user_id="user-1",
        timestamp="2026-06-13T10:00:00Z",
    )
    record2 = ApprovalRecord(
        project_id="demo",
        task_id="task-2",
        action="reject",
        feishu_user_id="user-1",
        timestamp="2026-06-13T10:01:00Z",
    )

    store.save(record1)
    store.save(record2)

    records = store.load_all()
    assert len(records) == 2


def test_approval_store_handles_missing_file(tmp_path):
    store = ApprovalStore(tmp_path / "nonexistent.jsonl")

    records = store.load_all()
    assert records == []


def test_approval_store_jsonl_format(tmp_path):
    """Verify that records are stored in JSONL format with correct formatting."""
    store = ApprovalStore(tmp_path / "approvals.jsonl")

    record = ApprovalRecord(
        project_id="test-project",
        task_id="test-task",
        action="approve",
        feishu_user_id="test-user",
        timestamp="2026-06-13T10:00:00Z",
    )

    store.save(record)

    # Read raw file content to verify format
    content = (tmp_path / "approvals.jsonl").read_text(encoding="utf-8")
    lines = [line for line in content.strip().split("\n") if line]
    assert len(lines) == 1

    # Verify it's valid JSON with sorted keys
    data = json.loads(lines[0])
    assert list(data.keys()) == sorted(data.keys())
