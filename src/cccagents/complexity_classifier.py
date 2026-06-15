from dataclasses import dataclass


ROLE_PLANS = {
    "S0": ["PM", "DEV"],
    "S1": ["PM", "DEV", "TEST"],
    "S2": ["PM", "PDM", "ARCH", "DEV", "TEST"],
    "S3": ["PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC"],
}

S0_KEYWORDS = ("typo", "README", "readme", "文案", "注释", "拼写")
S1_KEYWORDS = ("bug", "局部", "简单", "函数", "本地测试", "loading")
S2_KEYWORDS = ("新增", "功能", "接口", "跨文件", "模块", "测试用例", "CSV")
S3_KEYWORDS = (
    "认证",
    "权限",
    "密钥",
    "secret",
    "SECRET",
    "token",
    "TOKEN",
    "deploy",
    "部署",
    "生产",
    "数据库",
    "migration",
    "删除",
    "force",
    "支付",
    "外部 API",
    "FEISHU_APP_SECRET",
)
RESEARCH_KEYWORDS = ("调研", "选型", "对比", "方案比较", "向量数据库")


@dataclass(frozen=True)
class ComplexityDecision:
    complexity: str
    required_roles: list[str]
    risk_flags: list[str]
    requires_user_approval: bool
    reason: str


def classify_project_request(text: str) -> ComplexityDecision:
    risk_flags: list[str] = []
    normalized = text.strip()

    if _contains(normalized, S3_KEYWORDS):
        risk_flags.extend(["security_sensitive", "external_side_effect"])
        if _contains(normalized, RESEARCH_KEYWORDS):
            risk_flags.append("research_required")
        return ComplexityDecision(
            complexity="S3",
            required_roles=ROLE_PLANS["S3"],
            risk_flags=_unique(risk_flags),
            requires_user_approval=True,
            reason="请求涉及安全、权限、部署、生产、数据库、删除或外部副作用，需要完整团队和人工审批",
        )

    if _contains(normalized, RESEARCH_KEYWORDS):
        return ComplexityDecision(
            complexity="S3",
            required_roles=ROLE_PLANS["S3"],
            risk_flags=["research_required"],
            requires_user_approval=False,
            reason="请求需要调研或技术选型，需要 RES 参与",
        )

    if _contains(normalized, S2_KEYWORDS):
        return ComplexityDecision(
            complexity="S2",
            required_roles=ROLE_PLANS["S2"],
            risk_flags=["feature_change", "test_case_required"],
            requires_user_approval=False,
            reason="请求是中型功能或跨文件变更，需要需求、方案、开发和测试协作",
        )

    if _contains(normalized, S1_KEYWORDS):
        return ComplexityDecision(
            complexity="S1",
            required_roles=ROLE_PLANS["S1"],
            risk_flags=["code_change", "local_test_required"],
            requires_user_approval=False,
            reason="请求是小型代码变更，需要开发和测试验证",
        )

    if _contains(normalized, S0_KEYWORDS):
        return ComplexityDecision(
            complexity="S0",
            required_roles=ROLE_PLANS["S0"],
            risk_flags=["docs_only"],
            requires_user_approval=False,
            reason="请求是极小低风险变更，只需要 PM 和 DEV",
        )

    return ComplexityDecision(
        complexity="S2",
        required_roles=ROLE_PLANS["S2"],
        risk_flags=["unclear_scope", "needs_requirement_clarification"],
        requires_user_approval=False,
        reason="请求范围不够明确，默认按中型功能处理并要求 PDM 澄清",
    )


def _contains(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _unique(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result
