import pytest

from cccagents.workflow import can_enter_development, next_main_phase


def test_next_main_phase_advances_requirement_flow():
    assert next_main_phase("CREATED") == "REQUIREMENT_DRAFTING"
    assert next_main_phase("REQUIREMENT_DRAFTING") == "REQUIREMENT_REVIEW"
    assert next_main_phase("REQUIREMENT_REVIEW", review_passed=True) == "REQUIREMENT_APPROVED"


def test_requirement_review_failure_returns_to_drafting():
    assert next_main_phase("REQUIREMENT_REVIEW", review_passed=False) == "REQUIREMENT_DRAFTING"


def test_can_enter_development_requires_both_parallel_flows():
    assert can_enter_development("TECH_DESIGN_APPROVED", "TEST_CASE_APPROVED") is True
    assert can_enter_development("TECH_DESIGN_APPROVED", "TEST_CASE_REVIEW") is False


def test_unknown_phase_is_rejected():
    with pytest.raises(ValueError, match="Unknown main phase"):
        next_main_phase("NOPE")
