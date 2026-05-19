from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewDecision:
    next_phase: str
    next_handler_role: str | None
    reason: str


PASS_DECISIONS = {
    "requirement": ReviewDecision("REQUIREMENT_APPROVED", "PM", "requirement_review_passed"),
    "tech_design": ReviewDecision("TECH_DESIGN_APPROVED", "PM", "tech_design_review_passed"),
    "test_case": ReviewDecision("TEST_CASE_APPROVED", "PM", "test_case_review_passed"),
    "self_test": ReviewDecision("TESTING_AND_SECURITY", "TEST", "self_test_passed"),
    "quality_security": ReviewDecision("PRODUCT_ACCEPTANCE", "PDM", "quality_security_passed"),
    "acceptance": ReviewDecision("DONE", None, "acceptance_passed"),
}

FAIL_DECISIONS = {
    "requirement": ReviewDecision("REQUIREMENT_DRAFTING", "PDM", "requirement_review_failed"),
    "tech_design": ReviewDecision("TECH_DESIGN_DRAFTING", "ARCH", "tech_design_review_failed"),
    "test_case": ReviewDecision("TEST_CASE_DRAFTING", "TEST", "test_case_review_failed"),
    "self_test": ReviewDecision("DEVELOPMENT", "DEV", "self_test_failed"),
    "quality_security": ReviewDecision("FIXING", "DEV", "quality_security_failed"),
    "acceptance": ReviewDecision("FIXING", "DEV", "acceptance_failed"),
}


def review_decision(review_type: str, passed: bool) -> ReviewDecision:
    decisions = PASS_DECISIONS if passed else FAIL_DECISIONS
    if review_type not in decisions:
        raise ValueError(f"Unknown review type: {review_type}")
    return decisions[review_type]
