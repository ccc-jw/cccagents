from cccagents.project_state import ProjectState, load_project_state, save_project_state


def test_project_state_round_trips(tmp_path):
    project_dir = tmp_path / "demo"
    state = ProjectState(
        project_id="demo",
        status="done",
        complexity="S0",
        executed_roles=["DEV", "PM"],
        artifacts=["05-development/dev-summary.md"],
        updated_at="2026-06-14T00:00:00Z",
    )

    save_project_state(project_dir, state)
    loaded = load_project_state(project_dir)

    assert loaded == state
