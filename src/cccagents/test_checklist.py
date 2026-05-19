from pathlib import Path

from openpyxl import Workbook


CHECKLIST_FIELDS = [
    "case_id",
    "requirement_id",
    "module",
    "scenario",
    "preconditions",
    "steps",
    "expected_result",
    "priority",
    "case_type",
    "execution_status",
    "actual_result",
    "defect_id",
    "remark",
]


def _parse_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def markdown_table_to_xlsx(markdown_path: Path, xlsx_path: Path) -> None:
    lines = [line for line in markdown_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("Markdown checklist must contain header and separator")

    header = _parse_markdown_row(lines[0])
    if header != CHECKLIST_FIELDS:
        raise ValueError(f"Checklist header mismatch: {header}")

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "test-checklist"
    sheet.append(CHECKLIST_FIELDS)

    for line in lines[2:]:
        row = _parse_markdown_row(line)
        if len(row) != len(CHECKLIST_FIELDS):
            raise ValueError(f"Checklist row length mismatch: {row}")
        sheet.append(row)

    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(xlsx_path)
