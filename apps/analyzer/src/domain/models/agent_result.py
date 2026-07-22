"""Agent output/result domain models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentResult:
    """
    Captures the outcome of a single agent execution within a pipeline run.

    Stored in the ``agent_results`` table; one row per agent per job.
    """

    agent_name: str = ""
    status: AgentStatus = AgentStatus.PENDING
    output: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_order: int = 0
