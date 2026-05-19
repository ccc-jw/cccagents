from openpyxl import load_workbook

from cccagents.test_checklist import CHECKLIST_FIELDS, markdown_table_to_xlsx


def test_markdown_table_to_xlsx_preserves_schema(tmp_path):
    markdown_path = tmp_path / "test-checklist.final.md"
    xlsx_path = tmp_path / "test-checklist.final.xlsx"
    markdown_path.write_text(
        "| case_id | requirement_id | module | scenario | preconditions | steps | expected_result | priority | case_type | execution_status | actual_result | defect_id | remark |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        "| TC-001 | REQ-001 | login | valid login | user exists | submit credentials | login succeeds | P0 | functional | not_run |  |  |  |\n",
        encoding="utf-8",
    )

    markdown_table_to_xlsx(markdown_path, xlsx_path)

    workbook = load_workbook(xlsx_path)
    sheet = workbook.active
    headers = [cell.value for cell in sheet[1]]
    row = [cell.value for cell in sheet[2]]

    assert headers == CHECKLIST_FIELDS
    assert row[0] == "TC-001"
    assert row[9] == "not_run"


def test_markdown_table_to_xlsx_rejects_wrong_header(tmp_path):
    markdown_path = tmp_path / "bad.md"
    xlsx_path = tmp_path / "bad.xlsx"
    markdown_path.write_text(
        "| case_id | module |\n"
        "| --- | --- |\n"
        "| TC-001 | login |\n",
        encoding="utf-8",
    )

    try:
        markdown_table_to_xlsx(markdown_path, xlsx_path)
    except ValueError as error:
        assert "Checklist header mismatch" in str(error)
    else:
        raise AssertionError("Expected ValueError")
