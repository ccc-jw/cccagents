from cccagents.review_engine import ReviewInput, automatic_acceptance_allowed, evaluate_review


def test_quality_review_passes_when_exit_code_zero_and_artifacts_exist():
    result = evaluate_review(
        ReviewInput(
            review_type="quality",
            phase="TEST_VALIDATION",
            exit_code=0,
            expected_artifacts_present=True,
            secret_scan_clean=True,
            permission_level="L1",
            issues=[],
        )
    )

    assert result.passed is True
    assert result.next_phase == "PRODUCT_ACCEPTANCE"
    assert result.next_handler_role == "PDM"


def test_quality_review_fails_on_exit_code():
    result = evaluate_review(
        ReviewInput(
            review_type="quality",
            phase="TEST_VALIDATION",
            exit_code=1,
            expected_artifacts_present=True,
            secret_scan_clean=True,
            permission_level="L1",
            issues=["pytest failed"],
        )
    )

    assert result.passed is False
    assert result.next_phase == "FIXING"
    assert result.next_handler_role == "DEV"
    assert "pytest failed" in result.issues


def test_security_review_fails_on_secret_scan():
    result = evaluate_review(
        ReviewInput(
            review_type="security",
            phase="SECURITY_REVIEW",
            exit_code=0,
            expected_artifacts_present=True,
            secret_scan_clean=False,
            permission_level="L1",
            issues=[],
        )
    )

    assert result.passed is False
    assert result.next_handler_role == "DEV"
    assert "secret_scan_failed" in result.issues


def test_automatic_acceptance_allowed_for_low_risk_s2():
    assert automatic_acceptance_allowed(
        complexity="S2",
        permission_level="L1",
        risk_flags=["feature_change"],
        reviews_passed={"requirement", "tech_design", "test_case", "self_test", "quality", "acceptance"},
    ) is True


def test_automatic_acceptance_denied_for_l2_or_security_risk():
    assert automatic_acceptance_allowed(
        complexity="S2",
        permission_level="L2",
        risk_flags=["feature_change"],
        reviews_passed={"requirement", "tech_design", "test_case", "self_test", "quality", "acceptance"},
    ) is False
    assert automatic_acceptance_allowed(
        complexity="S1",
        permission_level="L1",
        risk_flags=["security_sensitive"],
        reviews_passed={"self_test", "quality"},
    ) is False
