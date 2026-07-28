"""GET /jobs/{job_id} — Return the current status of an analysis job.

Used by the Backend's polling scheduler (every 5 s) to track pipeline
progress.  Reads from the in-memory job store for active jobs.

Implements requirements 12.3 (job status polling).
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.api.job_store import jobs
from src.api.schemas import AgentProgressItem, JobProgress, JobStatusResponse
from src.domain.models.agent_result import AgentStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Get analysis job status",
)
async def get_job_status(job_id: UUID) -> JobStatusResponse:
    """Return the current status and per-agent progress for *job_id*.

    Raises 404 if the job is not found in the in-memory store.
    """
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    # Build progress from agent_results
    completed_agents: list[str] = []
    pending_agents: list[str] = []
    failed_agents: list[str] = []
    agents_list: list[AgentProgressItem] = []

    for result in job.agent_results:
        agents_list.append(
            AgentProgressItem(
                name=result.agent_name,
                status=result.status.value,
                execution_order=result.execution_order,
            )
        )
        if result.status == AgentStatus.COMPLETED:
            completed_agents.append(result.agent_name)
        elif result.status == AgentStatus.FAILED:
            failed_agents.append(result.agent_name)
        elif result.status in (AgentStatus.PENDING, AgentStatus.SKIPPED):
            pending_agents.append(result.agent_name)

    # Include the currently running agent if not already in results
    if job.current_agent:
        already_listed = any(a.name == job.current_agent for a in agents_list)
        if not already_listed:
            agents_list.append(
                AgentProgressItem(
                    name=job.current_agent,
                    status="running",
                    execution_order=len(agents_list) + 1,
                )
            )

    progress = JobProgress(
        completed_agents=completed_agents,
        current_agent=job.current_agent,
        pending_agents=pending_agents,
        failed_agents=failed_agents,
        agents=agents_list,
    )

    return JobStatusResponse(
        job_id=job.id,
        status=job.status.value,
        current_agent=job.current_agent,
        progress=progress,
        error_message=job.error_message,
    )


@router.post(
    "/{job_id}/cancel",
    summary="Cancel a running analysis job",
    status_code=status.HTTP_200_OK,
)
async def cancel_job(job_id: UUID) -> dict:
    """Request cancellation of a running job.

    Sets the cancel_requested flag on the job. The pipeline checks this
    flag between agents and will stop gracefully at the next opportunity.
    """
    from src.domain.models.analysis_job import JobStatus

    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    # Only cancel jobs that are still running
    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        return {
            "jobId": str(job_id),
            "cancelled": False,
            "message": f"Job is already in terminal state: {job.status.value}",
        }

    # Set the cancellation flag — pipeline will pick it up between agents
    job.cancel_requested = True

    return {
        "jobId": str(job_id),
        "cancelled": True,
        "message": "Cancellation requested. The job will stop after the current agent completes.",
    }
