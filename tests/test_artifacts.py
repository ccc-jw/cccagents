from pathlib import Path

from cccagents.artifacts import artifact_path


def test_tech_design_draft_path_uses_version():
    path = artifact_path(Path("projects/proj_001"), "tech-design", "tech-design", "draft", 2, "md")

    assert path == Path("projects/proj_001/02-tech-design/tech-design.v2.draft.md")


def test_test_checklist_final_xlsx_path():
    path = artifact_path(Path("projects/proj_001"), "test-cases", "test-checklist", "final", 1, "xlsx")

    assert path == Path("projects/proj_001/03-test-cases/test-checklist.v1.final.xlsx")


def test_review_artifact_path():
    path = artifact_path(Path("projects/proj_001"), "tech-design", "tech-design-review", "review", 3, "md")

    assert path == Path("projects/proj_001/02-tech-design/tech-design-review.v3.review.md")
