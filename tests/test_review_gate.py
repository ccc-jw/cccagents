from cccagents.review_gate import review_decision


def test_requirement_review_fail_routes_to_pdm():
    decision = review_decision("requirement", passed=False)

    assert decision.next_phase == "REQUIREMENT_DRAFTING"
    assert decision.next_handler_role == "PDM"


def test_tech_design_review_fail_routes_to_arch():
    decision = review_decision("tech_design", passed=False)

    assert decision.next_phase == "TECH_DESIGN_DRAFTING"
    assert decision.next_handler_role == "ARCH"


def test_test_case_review_fail_routes_to_test():
    decision = review_decision("test_case", passed=False)

    assert decision.next_phase == "TEST_CASE_DRAFTING"
    assert decision.next_handler_role == "TEST"


def test_acceptance_pass_finishes_project():
    decision = review_decision("acceptance", passed=True)

    assert decision.next_phase == "DONE"
    assert decision.next_handler_role is None
