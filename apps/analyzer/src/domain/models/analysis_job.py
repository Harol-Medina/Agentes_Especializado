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
