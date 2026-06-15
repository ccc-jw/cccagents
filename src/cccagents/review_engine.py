from dataclasses import dataclass

from cccagents.review_gate import review_decision


@dataclass(frozen=True)
class ReviewInput:
    review_type: str
    phase: str
    exit_code: int
    expected_artifacts_present: bool
    secret_scan_clean: bool
    permission_level: str
    issues: list[str]


@dataclass(frozen=True)
class ReviewResult:
    review_type: str
    phase: str
    passed: bool
    issues: list[str]
    next_phase: str
    next_handler_role: str | None
    reason: str


REQUIRED_REVIEWS = {
    "S0": {"self_test"},
    "S1": {"self_test", "quality"},
    "S2": {"requirement", "tech_design", "test_case", "self_test", "quality", "acceptance"},
    "S3": {"requirement", "tech_design", "test_case", "self_test", "quality", "security", "acceptance"},
}


def evaluate_review(review_input: ReviewInput) -> ReviewResult:
    issues = list(review_input.issues)
    if review_input.exit_code != 0:
        issues.append("exit_code_failed")
    if not review_input.expected_artifacts_present:
        issues.append("expected_artifacts_missing")
    if not review_input.secret_scan_clean:
        issues.append("secret_scan_failed")

    passed = len(issues) == 0
    gate_type = _gate_type(review_input.review_type)
    decision = review_decision(gate_type, passed)
    return ReviewResult(
        review_type=review_input.review_type,
        phase=review_input.phase,
        passed=passed,
        issues=issues,
        next_phase=decision.next_phase,
        next_handler_role=decision.next_handler_role,
        reason=decision.reason,
    )


def automatic_acceptance_allowed(
    complexity: str,
    permission_level: str,
    risk_flags: list[str],
    reviews_passed: set[str],
) -> bool:
    if permission_level in {"L2", "L3"}:
        return False
    if any(flag in risk_flags for flag in {"security_sensitive", "external_side_effect"}):
        return False
    required = REQUIRED_REVIEWS[complexity]
    return required.issubset(reviews_passed)


def _gate_type(review_type: str) -> str:
    if review_type == "quality":
        return "quality_security"
    if review_type == "security":
        return "quality_security"
    return review_type
