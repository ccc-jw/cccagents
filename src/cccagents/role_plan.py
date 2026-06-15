from dataclasses import dataclass

from cccagents.complexity_classifier import ComplexityDecision


@dataclass(frozen=True)
class RoleTask:
    role: str
    template: str
    expected_artifacts: list[str]


@dataclass(frozen=True)
class PhasePlan:
    name: str
    parallel: bool
    isolation: bool
    tasks: list[RoleTask]


@dataclass(frozen=True)
class RolePlan:
    complexity: str
    required_roles: list[str]
    risk_flags: list[str]
    requires_user_approval: bool
    phases: list[PhasePlan]

    def phase_by_name(self, name: str) -> PhasePlan:
        for phase in self.phases:
            if phase.name == name:
                return phase
        raise KeyError(name)


def build_role_plan(decision: ComplexityDecision) -> RolePlan:
    phases = _base_phases(decision.complexity)
    if "security_sensitive" in decision.risk_flags and not any(phase.name == "SECURITY_REVIEW" for phase in phases):
        phases.append(
            PhasePlan(
                name="SECURITY_REVIEW",
                parallel=False,
                isolation=False,
                tasks=[RoleTask("SEC", "security_review", ["06-security/security-review.md"])],
            )
        )
    return RolePlan(
        complexity=decision.complexity,
        required_roles=decision.required_roles,
        risk_flags=decision.risk_flags,
        requires_user_approval=decision.requires_user_approval,
        phases=phases,
    )


def _base_phases(complexity: str) -> list[PhasePlan]:
    if complexity == "S0":
        return [
            PhasePlan("DEV_IMPLEMENTATION", False, False, [RoleTask("DEV", "implement_small_change", ["05-development/dev-summary.md"])]),
            PhasePlan("DEV_SELF_TEST", False, False, [RoleTask("DEV", "self_test", ["05-development/self-test.md"])]),
            PhasePlan("PM_AUTO_ACCEPTANCE", False, False, [RoleTask("PM", "auto_acceptance", ["07-acceptance/acceptance-report.md"])]),
        ]
    if complexity == "S1":
        return [
            PhasePlan("DEV_IMPLEMENTATION", False, False, [RoleTask("DEV", "implement_code_change", ["05-development/dev-summary.md"])]),
            PhasePlan("DEV_SELF_TEST", False, False, [RoleTask("DEV", "self_test", ["05-development/self-test.md"])]),
            PhasePlan("TEST_VALIDATION", False, False, [RoleTask("TEST", "validate_change", ["04-test-cases/test-result.md"])]),
            PhasePlan("PM_AUTO_ACCEPTANCE", False, False, [RoleTask("PM", "auto_acceptance", ["07-acceptance/acceptance-report.md"])]),
        ]
    if complexity == "S2":
        return [
            PhasePlan("REQUIREMENT_DRAFTING", False, False, [RoleTask("PDM", "draft_prd", ["02-requirements/prd.md"])]),
            PhasePlan("REQUIREMENT_REVIEW", False, False, [RoleTask("PM", "review_requirement", ["02-requirements/prd-review.md"])]),
            PhasePlan(
                "PARALLEL_DESIGN_AND_TESTCASE",
                True,
                True,
                [
                    RoleTask("ARCH", "draft_tech_design", ["03-architecture/tech-design.md"]),
                    RoleTask("TEST", "draft_test_cases", ["04-test-cases/test-cases.md", "04-test-cases/test-cases.xlsx"]),
                ],
            ),
            PhasePlan("DESIGN_AND_TESTCASE_REVIEW", False, False, [RoleTask("PM", "review_design_and_testcase", ["03-architecture/tech-design-review.md"])]),
            PhasePlan("DEVELOPMENT", False, False, [RoleTask("DEV", "implement_feature", ["05-development/dev-summary.md"])]),
            PhasePlan("DEV_SELF_TEST", False, False, [RoleTask("DEV", "self_test", ["05-development/self-test.md"])]),
            PhasePlan("TEST_VALIDATION", False, False, [RoleTask("TEST", "validate_feature", ["04-test-cases/test-result.md"])]),
            PhasePlan("PRODUCT_ACCEPTANCE", False, False, [RoleTask("PDM", "product_acceptance", ["07-acceptance/acceptance-report.md"])]),
        ]
    if complexity == "S3":
        return [
            PhasePlan("REQUIREMENT_DRAFTING", False, False, [RoleTask("PDM", "draft_prd", ["02-requirements/prd.md"])]),
            PhasePlan("RESEARCH", False, False, [RoleTask("RES", "research_options", ["01-input/research-report.md"])]),
            PhasePlan(
                "PARALLEL_DESIGN_TEST_SECURITY",
                True,
                True,
                [
                    RoleTask("ARCH", "draft_tech_design", ["03-architecture/tech-design.md"]),
                    RoleTask("TEST", "draft_test_cases", ["04-test-cases/test-cases.md", "04-test-cases/test-cases.xlsx"]),
                    RoleTask("SEC", "security_plan", ["06-security/security-review.md"]),
                ],
            ),
            PhasePlan("DEVELOPMENT", False, False, [RoleTask("DEV", "implement_feature", ["05-development/dev-summary.md"])]),
            PhasePlan("TEST_VALIDATION", False, False, [RoleTask("TEST", "validate_feature", ["04-test-cases/test-result.md"])]),
            PhasePlan("SECURITY_REVIEW", False, False, [RoleTask("SEC", "security_review", ["06-security/security-review.md"])]),
            PhasePlan("PRODUCT_ACCEPTANCE", False, False, [RoleTask("PDM", "product_acceptance", ["07-acceptance/acceptance-report.md"])]),
        ]
    raise ValueError(f"Unknown complexity: {complexity}")
