"""POST /analyze — Accept and enqueue a new analysis job.

The endpoint returns 202 immediately and executes the pipeline as a
FastAPI background task. The pipeline runs the full AgentPipeline from
task 4.2, starting with RepositoryAgent (task 4.4) and continuing through
placeholder agents for subsequent tasks.

Implements requirements 12.1, 12.3, 6.5.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, status

from src.adapters.webhook_adapter import WebhookAdapter
from src.agents.architecture_agent import ArchitectureAgent
from src.agents.documentation_agent import DocumentationAgent
from src.agents.kiro_agent import KiroAgent
from src.agents.modernization_agent import ModernizationAgent
from src.agents.pipeline import AgentPipeline, PipelineTerminatedError
from src.agents.quality_agent import QualityAgent
from src.agents.repository_agent import RepositoryAgent
from src.agents.security_agent import SecurityAgent
from src.api.job_store import jobs
from src.api.schemas import AnalyzeRequest, AnalyzeResponse
from src.config import get_settings
from src.domain.models.analysis_job import AnalysisJob, JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["analyze"])


async def _run_pipeline(job: AnalysisJob, webhook_url: str) -> None:
    """Execute the agent pipeline in the background.

    Updates the in-memory job store with progress as agents complete.
    On completion or failure, sends a webhook to the Backend.
    """
    settings = get_settings()

    # Update job state to cloning
    job.status = JobStatus.CLONING
    job.current_agent = "repository_agent"

    # Build the list of agents (full pipeline: 7 agents in order)
    agents = [
        RepositoryAgent(),
        ArchitectureAgent(),
        QualityAgent(),
        SecurityAgent(),
        DocumentationAgent(),
        ModernizationAgent(),
        KiroAgent(),
    ]

    # Create webhook adapter for notifications
    webhook_adapter = WebhookAdapter(
        webhook_url=webhook_url,
        webhook_secret=settings.webhook_secret,
    )

    # Create and execute the pipeline
    pipeline = AgentPipeline(agents=agents, webhook_adapter=webhook_adapter)

    # Set up progressive results: update job as each agent completes
    def _on_agent_done(agent_name: str, context) -> None:
        """Update the job store incrementally after each agent."""
        job.current_agent = agent_name
        job.agent_results = context.agent_results
        # Persist partial data as it becomes available
        if context.project_model is not None:
            job.project = context.project_model
        if context.architecture_report is not None:
            job.architecture_report = context.architecture_report
        if context.quality_report is not None:
            job.quality_report = context.quality_report
        if context.security_report is not None:
            job.security_report = context.security_report
        if context.documentation_bundle is not None:
            job.documentation_bundle = context.documentation_bundle
        if context.modernization_plan is not None:
            job.modernization_plan = context.modernization_plan
        if context.kiro_spec is not None:
            job.kiro_spec = context.kiro_spec

    pipeline.set_on_agent_complete(_on_agent_done)

    # Set up cancellation check
    pipeline.set_cancel_check(lambda: job.cancel_requested)

    try:
        job.status = JobStatus.ANALYZING
        context = await pipeline.execute(job_id=job.id, repo_url=job.repo_url)

        # Pipeline completed successfully
        job.status = JobStatus.COMPLETED
        job.current_agent = None
        job.agent_results = context.agent_results
        job.project = context.project_model
        job.architecture_report = context.architecture_report
        job.quality_report = context.quality_report
        job.security_report = context.security_report
        job.documentation_bundle = context.documentation_bundle
        job.modernization_plan = context.modernization_plan
        job.kiro_spec = context.kiro_spec

        logger.info("Pipeline completed — job_id=%s", job.id)

    except PipelineTerminatedError as exc:
        if job.cancel_requested:
            job.status = JobStatus.CANCELLED
            job.current_agent = None
            job.error_message = "Analysis cancelled by user"
            logger.info("Pipeline cancelled — job_id=%s", job.id)
        else:
            job.status = JobStatus.FAILED
            job.current_agent = None
            job.error_message = exc.message
            logger.error(
                "Pipeline terminated — job_id=%s, error=%s", job.id, exc.message
            )

    except Exception as exc:  # noqa: BLE001
        job.status = JobStatus.FAILED
        job.current_agent = None
        job.error_message = str(exc)

        logger.error(
            "Pipeline failed unexpectedly — job_id=%s, error=%s",
            job.id,
            str(exc),
        )


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=AnalyzeResponse,
    summary="Start repository analysis",
)
async def start_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
) -> AnalyzeResponse:
    """Accept a repository analysis request and schedule the pipeline.

    Returns 202 immediately. The pipeline runs asynchronously and
    notifies the Backend via webhook on completion.
    """
    # Create the job in memory
    job = AnalysisJob(
        id=request.job_id,
        repo_url=request.repo_url,
        status=JobStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    jobs[job.id] = job

    # Schedule pipeline execution as a background task
    background_tasks.add_task(_run_pipeline, job, request.webhook_url)

    logger.info(
        "Analysis accepted — job_id=%s, repo_url=%s",
        job.id,
        request.repo_url,
    )

    return AnalyzeResponse(
        job_id=job.id,
        status="pending",
        estimated_duration="5-15 minutes",
    )
