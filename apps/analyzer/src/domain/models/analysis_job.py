"""Analysis job state machine domain model."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from src.domain.models.agent_result import AgentResult
from src.domain.models.project_model import ProjectModel


class JobStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AnalysisJob:
    """
    Represents a single repository analysis job.

    Tracks the overall lifecycle from submission to completion,
    the currently executing agent, and accumulated agent results.
    """

    id: UUID = field(default_factory=uuid4)
    repo_url: str = ""
    status: JobStatus = JobStatus.PENDING
    current_agent: Optional[str] = None
    agent_results: list[AgentResult] = field(default_factory=list)
    project: Optional[ProjectModel] = None
    created_at: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None
    # Report data from pipeline agents
    architecture_report: Optional[dict] = None
    quality_report: Optional[dict] = None
    security_report: Optional[dict] = None
    documentation_bundle: Optional[dict] = None
    modernization_plan: Optional[dict] = None
    kiro_spec: Optional[str] = None
    # Cancellation flag — checked by the pipeline between agents
    cancel_requested: bool = False
