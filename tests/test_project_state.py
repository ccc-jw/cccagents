from cccagents.project_state import ProjectState, load_project_state, save_project_state


def test_save_and_load_project_state(tmp_path):
    state = ProjectState(
        project_id="demo",
        source="feishu",
        status="running",
        complexity="S2",
        current_phase="DEVELOPMENT",
        required_roles=["PM", "PDM", "ARCH", "DEV", "TEST"],
        risk_flags=["feature_change"],
        approval_policy="auto_if_l0_l1_and_all_reviews_pass",
        retry_count_by_phase={"TEST_VALIDATION": 1},
        created_at="2026-06-13T10:00:00Z",
        updated_at="2026-06-13T11:00:00Z",
        last_pm_notification_at="2026-06-13T10:30:00Z",
    )

    save_project_state(tmp_path, state)
    loaded = load_project_state(tmp_path)

    assert loaded == state


def test_load_missing_project_state_raises_key_error(tmp_path):
    try:
        load_project_state(tmp_path)
    except KeyError as exc:
        assert str(exc) == "'project-state.json'"
    else:
        raise AssertionError("expected KeyError")
