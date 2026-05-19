from cccagents.command_policy import classify_command, decide_command


def test_classifies_read_only_commands_as_l0():
    for command in ["ls", "git status", "git diff", "rg TODO", "grep -R foo ."]:
        assert classify_command(command) == "L0"


def test_classifies_local_write_and_tests_as_l1():
    for command in ["pytest", "npm test", "mkdir -p docs", "python scripts/generate.py"]:
        assert classify_command(command) == "L1"


def test_classifies_project_changes_as_l2():
    for command in ["npm install", "pip install requests", "alembic upgrade head", "npm run migrate"]:
        assert classify_command(command) == "L2"


def test_classifies_external_impact_as_l3():
    for command in ["git push", "gh pr create", "kubectl apply -f deploy.yaml", "terraform apply"]:
        assert classify_command(command) == "L3"


def test_dangerous_delete_and_force_require_approval():
    assert classify_command("rm -rf /tmp/demo") == "L3"
    assert classify_command("git push --force") == "L3"


def test_decision_allows_l0_and_l1_but_requires_approval_for_l2_l3():
    assert decide_command("L0") == "allow"
    assert decide_command("L1") == "allow"
    assert decide_command("L2") == "require_approval"
    assert decide_command("L3") == "require_approval"


def test_decision_denies_unbound_write():
    assert decide_command("L1", bound_project=False) == "deny"
