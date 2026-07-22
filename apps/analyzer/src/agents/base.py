"""Base agent abstract class and shared context/output dataclasses.

Full interface documentation lives in the design document.
Concrete agent implementations start in task 4.2 (pipeline) and 4.4 (Repository_Agent).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from src.domain.models.agent_result import AgentResult, AgentStatus
from src.domain.models.project_model import ProjectModel


@dataclass
class PipelineContext:
    """Accumulated context passed through the agent chain."""

    job_id: UUID
    repo_url: str
    repo_path: Optional[str] = None
    project_model: Optional[ProjectModel] = None
    architecture_report: Optional[dict] = None
    quality_report: Optional[dict] = None
    security_report: Optional[dict] = None
    documentation_bundle: Optional[dict] = None
    modernization_plan: Optional[dict] = None
    kiro_spec: Optional[str] = None
    agent_results: list[AgentResult] = field(default_factory=list)


@dataclass
class AgentOutput:
    """Structured output from a single agent execution."""

    agent_name: str
    status: AgentStatus
    data: dict
    context_updates: dict  # Keys to merge back into PipelineContext
    error: Optional[str] = None


class AgentExecutionError(Exception):
    """Raised when an agent encounters a non-recoverable error."""

    def __init__(self, agent_name: str, message: str) -> None:
        self.agent_name = agent_name
        self.message = message
        super().__init__(f"[{agent_name}] {message}")


class BaseAgent(ABC):
    """Abstract base class for all pipeline agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique agent identifier (snake_case)."""
        ...

    @property
    @abstractmethod
    def execution_order(self) -> int:
        """Position in the pipeline (1–7)."""
        ...

    @abstractmethod
    async def execute(self, context: PipelineContext) -> AgentOutput:
        """
        Execute the agent's analysis task.

        Args:
            context: Accumulated context from all previous agents.

        Returns:
            AgentOutput with structured results and context updates.

        Raises:
            AgentExecutionError: If the agent fails non-recoverably.
        """
        ...

    def can_execute(self, context: PipelineContext) -> bool:
        """Return True if minimum required context exists to run this agent.

        The default implementation requires a non-None project_model.
        Repository_Agent overrides this to always return True.
        """
        return context.project_model is not None
