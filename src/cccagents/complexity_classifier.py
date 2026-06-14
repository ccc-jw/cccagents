from dataclasses import dataclass


@dataclass(frozen=True)
class ComplexityDecision:
    complexity: str
    required_roles: list[str]
    requires_user_approval: bool
    risk_flags: list[str]


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def classify_project_request(text: str) -> ComplexityDecision:
    if _has_any(text, ("调研", "向量数据库", "技术选型", "方案")):
        return ComplexityDecision(
            complexity="S3",
            required_roles=["PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC"],
            requires_user_approval=False,
            risk_flags=["research_required"],
        )

    if _has_any(text, ("安全", "认证", "权限", "部署", "生产", "secret", "feishu_app_secret")):
        flags = []
        if _has_any(text, ("安全", "认证", "权限", "secret", "feishu_app_secret")):
            flags.append("security_sensitive")
        if _has_any(text, ("部署", "生产")):
            flags.append("external_side_effect")
        return ComplexityDecision(
            complexity="S3",
            required_roles=["PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC"],
            requires_user_approval=True,
            risk_flags=flags,
        )

    if _has_any(text, ("新增", "功能", "接口", "测试用例", "csv")):
        return ComplexityDecision(
            complexity="S2",
            required_roles=["PM", "PDM", "ARCH", "DEV", "TEST"],
            requires_user_approval=False,
            risk_flags=["feature_change"],
        )

    if _has_any(text, ("bug", "loading", "局部", "本地测试")):
        return ComplexityDecision(
            complexity="S1",
            required_roles=["PM", "DEV", "TEST"],
            requires_user_approval=False,
            risk_flags=["local_test_required"],
        )

    if _has_any(text, ("typo", "readme", "文档", "docs")):
        return ComplexityDecision(
            complexity="S0",
            required_roles=["PM", "DEV"],
            requires_user_approval=False,
            risk_flags=["docs_only"],
        )

    return ComplexityDecision(
        complexity="S1",
        required_roles=["PM", "DEV", "TEST"],
        requires_user_approval=False,
        risk_flags=["local_test_required"],
    )
