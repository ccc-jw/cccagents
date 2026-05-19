from cccagents.pm_scheduler import build_startup_summary


def test_build_startup_summary_reports_project_root_and_interval():
    summary = build_startup_summary(project_root="/home/ubuntu/cccagents/projects", interval_seconds=60)

    assert summary == "PM Scheduler watching /home/ubuntu/cccagents/projects every 60s"
