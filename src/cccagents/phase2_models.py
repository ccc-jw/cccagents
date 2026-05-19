from dataclasses import dataclass, field
from enum import StrEnum


AGENT_ROLES = ("PM", "PDM", "RES", "ARCH", "DEV", "TEST", "SEC")


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    BLOCKED = "blocked"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class ArtifactStatus(StrEnum):
    DRAFT = "draft"
    FINAL = "final"
    REVIEW = "review"
    REPORT = "report"
    LOG = "log"


@dataclass(frozen=True)
class Project:
    id: str
    name: str
    status: str
    current_phase: str
    owner: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Task:
    id: str
    project_id: str
    phase: str
    flow: str
    assignee_role: str
    title: str
    description: str
    created_at: str
    parent_task_id: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    input_artifact_ids: list[str] = field(default_factory=list)
    output_artifact_ids: list[str] = field(default_factory=list)
    issue_ids: list[str] = field(default_factory=list)
    started_at: str | None = None
    updated_at: str | None = None
    due_at: str | None = None
    completed_at: str | None = None
    next_handler_role: str | None = None
    next_handler_reason: str | None = None

    def __post_init__(self) -> None:
        if self.next_handler_role is None:
            object.__setattr__(self, "next_handler_role", self.assignee_role)


@dataclass(frozen=True)
class Review:
    id: str
    project_id: str
    phase: str
    review_type: str
    status: str
    participants: list[str]
    required_roles: list[str]
    issues: list[str]
    decision_summary: str
    created_at: str
    completed_at: str | None = None


@dataclass(frozen=True)
class Artifact:
    id: str
    project_id: str
    phase: str
    owner_role: str
    type: str
    path: str
    version: int
    status: ArtifactStatus
    created_at: str
    updated_at: str | None = None
    source_artifact_id: str | None = None


@dataclass(frozen=True)
class Issue:
    id: str
    project_id: str
    source: str
    severity: str
    title: str
    description: str
    owner_role: str
    status: str
    created_at: str
    related_task_id: str | None = None
    related_artifact_id: str | None = None
    updated_at: str | None = None
    closed_at: str | None = None


@dataclass(frozen=True)
class AgentModelConfig:
    role_code: str
    model_base_url: str
    model_api_key_ref: str
    model_name: str
    executor_type: str = "claude_code_cli"
    enabled: bool = True
