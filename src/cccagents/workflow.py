MAIN_TRANSITIONS = {
    "CREATED": "REQUIREMENT_DRAFTING",
    "REQUIREMENT_DRAFTING": "REQUIREMENT_REVIEW",
    "REQUIREMENT_APPROVED": "PARALLEL_DESIGN_AND_TESTCASE",
    "PARALLEL_DESIGN_AND_TESTCASE": "DEVELOPMENT",
    "DEVELOPMENT": "DEV_SELF_TEST",
    "DEV_SELF_TEST": "TESTING_AND_SECURITY",
    "TESTING_AND_SECURITY": "PRODUCT_ACCEPTANCE",
    "PRODUCT_ACCEPTANCE": "DONE",
}


def next_main_phase(current_phase: str, review_passed: bool | None = None) -> str:
    if current_phase == "REQUIREMENT_REVIEW":
        if review_passed is None:
            raise ValueError("review_passed is required for REQUIREMENT_REVIEW")
        return "REQUIREMENT_APPROVED" if review_passed else "REQUIREMENT_DRAFTING"

    if current_phase not in MAIN_TRANSITIONS:
        raise ValueError(f"Unknown main phase: {current_phase}")

    return MAIN_TRANSITIONS[current_phase]


def can_enter_development(tech_design_state: str, test_case_state: str) -> bool:
    return tech_design_state == "TECH_DESIGN_APPROVED" and test_case_state == "TEST_CASE_APPROVED"
