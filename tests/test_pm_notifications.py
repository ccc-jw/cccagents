from cccagents.pm_notifications import PMNotification, format_pm_notification


def test_formats_progress_summary_without_secrets():
    notification = PMNotification(
        project_id="project_1",
        event_type="progress_summary",
        title="Phase 4 progress",
        body="Running recovery smoke with ANTHROPIC_API_KEY=secret-value",
        required_action="none",
        task_id="task_1",
    )

    message = format_pm_notification(notification)

    assert "PM update for project_1" in message
    assert "progress_summary" in message
    assert "ANTHROPIC_API_KEY=[REDACTED]" in message
    assert "secret-value" not in message


def test_formats_restart_recovery_decision():
    notification = PMNotification(
        project_id="project_1",
        event_type="restart_recovery",
        title="Task interrupted after restart",
        body="task_1 requires retry decision",
        required_action="approve_retry_or_stop",
        task_id="task_1",
    )

    message = format_pm_notification(notification)

    assert "Task interrupted after restart" in message
    assert "Required action: approve_retry_or_stop" in message
    assert "Task: task_1" in message


def test_rejects_unknown_event_type():
    notification = PMNotification(
        project_id="project_1",
        event_type="debug_noise",
        title="Debug",
        body="ignore",
        required_action="none",
        task_id=None,
    )

    try:
        format_pm_notification(notification)
    except ValueError as error:
        assert "unsupported PM notification event" in str(error)
    else:
        raise AssertionError("expected unsupported event error")
