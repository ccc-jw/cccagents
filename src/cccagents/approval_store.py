from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class ApprovalRecord:
    project_id: str
    task_id: str
    action: str
    feishu_user_id: str
    timestamp: str


class ApprovalStore:
    def __init__(self, path: Path):
        self.path = path

    def save(self, record: ApprovalRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), ensure_ascii=False, sort_keys=True) + "\n")

    def load_all(self) -> list[ApprovalRecord]:
        if not self.path.exists():
            return []

        records = []
        for line in self.path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                data = json.loads(line)
                records.append(ApprovalRecord(**data))
        return records
