from cccagents.complexity_classifier import ComplexityDecision
from cccagents.role_plan import build_role_plan


def test_s0_role_plan_has_dev_only_flow():
    decision = ComplexityDecision("S0", ["PM", "DEV"], ["docs_only"], False, "small")

    plan = build_role_plan(decision)

    assert [phase.name for phase in plan.phases] == ["DEV_IMPLEMENTATION", "DEV_SELF_TEST", "PM_AUTO_ACCEPTANCE"]
    assert plan.phases[0].tasks[0].role == "DEV"
    assert plan.requires_user_approval is False


def test_s1_role_plan_adds_test_validation():
    decision = ComplexityDecision("S1", ["PM", "DEV", "TEST"], ["code_change"], False, "bug")

    plan = build_role_plan(decision)

    assert [phase.name for phase in plan.phases] == ["DEV_IMPLEMENTATION", "DEV_SELF_TEST", "TEST_VALIDATION", "PM_AUTO_ACCEPTANCE"]
    assert plan.phases[2].tasks[0].role == "TEST"


def test_s2_role_plan_has_parallel_design_and_testcase_with_isolation():
    decision = ComplexityDecision("S2", ["PM", "PDM", "ARCH", "DEV", "TEST"], ["feature_change"], False, "feature")

    plan = build_role_plan(decision)

    parallel = plan.phase_by_name("PARALLEL_DESIGN_AND_TESTCASE")
    assert parallel.parallel is True
    assert parallel.isolation is True
    assert [task.role for task in parallel.tasks] == ["ARCH", "TEST"]
    assert parallel.tasks[0].template == "draft_tech_design"
    assert parallel.tasks[1].template == "draft_test_cases"


def test_security_risk_requires_user_approval_even_for_lower_complexity():
    decision = ComplexityDecision("S1", ["PM", "DEV", "TEST", "SEC"], ["security_sensitive"], True, "secret")

    plan = build_role_plan(decision)

    assert plan.requires_user_approval is True
    assert "SECURITY_REVIEW" in [phase.name for phase in plan.phases]
