from pathlib import Path


ROLES = {
    "pm.md": ["项目经理", "task router", "review gate"],
    "pdm.md": ["产品经理", "PRD", "acceptance"],
    "res.md": ["调研员", "research", "feasibility"],
    "arch.md": ["架构师", "tech-design", "ARCH/DEV 与 TEST"],
    "dev.md": ["开发工程师", "Claude Code CLI", "self-test"],
    "test.md": ["测试工程师", "test-checklist", "Excel"],
    "sec.md": ["安全工程师", "security", "SAST"],
}


def test_hermes_role_files_define_required_contracts():
    role_dir = Path("hermes/roles")

    for filename, required_terms in ROLES.items():
        content = (role_dir / filename).read_text(encoding="utf-8")
        assert "## Role" in content
        assert "## Inputs" in content
        assert "## Outputs" in content
        assert "## Forbidden" in content
        assert "## Tool Access" in content
        for term in required_terms:
            assert term in content


def test_gateway_agents_file_binds_feishu_to_pm_boundary():
    content = Path("AGENTS.md").read_text(encoding="utf-8")

    assert "PM Agent" in content
    assert "Feishu users only talk to PM" in content
    assert "PM is the only user-facing entry point" in content
    assert "Do not let PDM, RES, ARCH, DEV, TEST, or SEC directly contact the Feishu user" in content
    assert "hermes/roles/pm.md" in content
    assert "hermes/roles/dev.md" in content
