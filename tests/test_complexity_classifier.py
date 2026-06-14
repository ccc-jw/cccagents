from cccagents.complexity_classifier import classify_project_request


def test_classifies_typo_or_readme_change_as_s0():
    decision = classify_project_request("修复 README 里的一个 typo")

    assert decision.complexity == "S0"
    assert decision.required_roles == ["PM", "DEV"]
    assert decision.requires_user_approval is False
    assert "docs_only" in decision.risk_flags


def test_classifies_small_bug_as_s1_with_test():
    decision = classify_project_request("修复登录按钮点击后没有 loading 的局部 bug，并跑本地测试")

    assert decision.complexity == "S1"
    assert decision.required_roles == ["PM", "DEV", "TEST"]
    assert "local_test_required" in decision.risk_flags


def test_classifies_new_feature_as_s2():
    decision = classify_project_request("新增一个导出订单 CSV 的功能，包含接口和测试用例")

    assert decision.complexity == "S2"
    assert decision.required_roles == ["PM", "PDM", "ARCH", "DEV", "TEST"]
    assert "feature_change" in decision.risk_flags


def test_classifies_security_or_deploy_as_s3_with_sec_and_approval():
    decision = classify_project_request("修改认证权限并部署到生产，涉及 FEISHU_APP_SECRET 配置")

    assert decision.complexity == "S3"
    assert decision.required_roles == ["PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC"]
    assert decision.requires_user_approval is True
    assert "security_sensitive" in decision.risk_flags
    assert "external_side_effect" in decision.risk_flags


def test_explicit_research_request_adds_res():
    decision = classify_project_request("调研三种向量数据库方案并给出技术选型")

    assert decision.complexity == "S3"
    assert "RES" in decision.required_roles
    assert "research_required" in decision.risk_flags
