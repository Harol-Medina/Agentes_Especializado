"""Abstract persistence (storage) port."""

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.analysis_job import AnalysisJob
from src.domain.models.project_model import ProjectModel


class StoragePort(ABC):
    """Defines the contract for persisting and retrieving domain objects."""

    # ------------------------------------------------------------------ jobs

    @abstractmethod
    async def save_job(self, job: AnalysisJob) -> None:
        """Upsert an AnalysisJob record."""
        ...

    @abstractmethod
    async def get_job(self, job_id: UUID) -> AnalysisJob | None:
        """Retrieve an AnalysisJob by its ID, or None if not found."""
        ...

    # --------------------------------------------------------------- projects

    @abstractmethod
    async def save_project(self, project: ProjectModel, job_id: UUID) -> None:
        """Persist a ProjectModel and its associated graph nodes/edges."""
        ...

    @abstractmethod
    async def get_project(self, project_id: UUID) -> ProjectModel | None:
        """Retrieve a ProjectModel by its ID, or None if not found."""
        ...
