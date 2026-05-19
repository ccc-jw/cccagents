from dataclasses import dataclass

from cccagents.redaction import redact_text


SUPPORTED_PM_EVENTS = {
    "progress_summary",
    "soft_timeout",
    "hard_timeout",
    "waiting_timeout",
    "blocked_timeout",
    "approval_request",
    "completion_notice",
    "restart_recovery",
}


@dataclass(frozen=True)
class PMNotification:
    project_id: str
    event_type: str
    title: str
    body: str
    required_action: str
    task_id: str | None


def format_pm_notification(notification: PMNotification) -> str:
    if notification.event_type not in SUPPORTED_PM_EVENTS:
        raise ValueError(f"unsupported PM notification event: {notification.event_type}")

    redacted_body = redact_text(notification.body).text
    lines = [
        f"PM update for {notification.project_id}",
        f"Event: {notification.event_type}",
        f"Title: {notification.title}",
        f"Body: {redacted_body}",
        f"Required action: {notification.required_action}",
    ]
    if notification.task_id:
        lines.append(f"Task: {notification.task_id}")
    return "\n".join(lines)
