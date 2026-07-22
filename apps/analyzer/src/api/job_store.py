"""In-memory job state store for tracking active analysis jobs.

This is a simple singleton dict used during the MVP. In production,
job state is persisted in PostgreSQL. The in-memory store allows the
GET /jobs/{job_id} endpoint to return progress without a DB round-trip
for active (in-flight) jobs.
"""

from uuid import UUID

from src.domain.models.analysis_job import AnalysisJob

# Singleton dict — maps job_id → AnalysisJob
jobs: dict[UUID, AnalysisJob] = {}
