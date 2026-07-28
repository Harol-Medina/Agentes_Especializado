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
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, status

from src.adapters.postgres_adapter import PostgresAdapter
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
from src.api.schemas import AnalyzeRequest, AnalyzeResponse, RetryRequest, RetryResponse
from src.config import get_settings
from src.domain.models.analysis_job import AnalysisJob, JobStatus
from src.parsing.chunker import ASTChunker
from src.rag.embeddings import TitanEmbeddingsClient
from src.rag.indexer import EmbeddingIndexer

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

    # Set up agent start notification for real-time progress
    def _on_agent_start(agent_name: str, context) -> None:
        """Update current_agent when a new agent starts executing."""
        job.current_agent = agent_name

    pipeline.set_on_agent_start(_on_agent_start)

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

        # ── Embedding indexing for RAG chat ──────────────────────────────
        # Run after pipeline completes so chat can answer questions
        try:
            await _index_embeddings(job, context)
        except Exception as idx_err:  # noqa: BLE001
            logger.warning(
                "Embedding indexing failed (chat will show no_context) — job_id=%s, error=%s",
                job.id,
                str(idx_err),
            )

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


async def _index_embeddings(job: AnalysisJob, context) -> None:
    """Index code chunks as embeddings for RAG chat.

    Chunks the parsed source files and generates Titan Embeddings V2 vectors,
    then bulk inserts into code_embeddings table.
    """
    # Need repo_path and parsed files from context
    repo_path_str = getattr(context, "repo_path", None)
    project_model = context.project_model

    if not repo_path_str or not project_model:
        logger.warning("No repo_path or project_model — skipping embedding indexing")
        return

    # Get the parsed files from the graph builder's source
    from src.adapters.git_adapter import GitAdapter

    git_adapter = GitAdapter()
    source_files = await git_adapter.list_source_files(Path(repo_path_str))

    if not source_files:
        logger.warning("No source files found for indexing — job_id=%s", job.id)
        return

    # Read file contents and create chunks
    chunker = ASTChunker()

    # Import tree-sitter parser to re-parse for chunking
    from src.parsing.tree_sitter_parser import TreeSitterParser

    parser = TreeSitterParser()
    parsed_files = []
    parseable_exts = {".java", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".py"}

    for file_path in source_files:
        if file_path.suffix.lower() in parseable_exts:
            result = parser.parse_file(file_path)
            if result is not None:
                parsed_files.append(result)

    if not parsed_files:
        logger.warning("No parseable files for chunking — job_id=%s", job.id)
        return

    # Chunk the parsed files
    chunks = chunker.chunk_parsed_files(parsed_files)
    if not chunks:
        logger.warning("Chunker produced 0 chunks — job_id=%s", job.id)
        return

    # Limit chunks to avoid excessive Bedrock calls (cost control)
    max_chunks = 200
    if len(chunks) > max_chunks:
        logger.info(
            "Limiting chunks from %d to %d for embedding — job_id=%s",
            len(chunks), max_chunks, job.id,
        )
        chunks = chunks[:max_chunks]

    logger.info("Generating embeddings for %d chunks — job_id=%s", len(chunks), job.id)

    # Generate embeddings
    embeddings_client = TitanEmbeddingsClient()
    texts = [chunk.text for chunk in chunks]
    embeddings = await embeddings_client.generate_batch(texts)

    # Store in database
    postgres = PostgresAdapter()
    await postgres.connect()

    try:
        # Ensure project record exists (FK requirement for code_embeddings)
        project_name = job.repo_url.rstrip("/").split("/")[-1] if job.repo_url else "unknown"
        await postgres.execute(
            """
            INSERT INTO analysis_jobs (id, repo_url, status)
            VALUES ($1, $2, $3)
            ON CONFLICT (id) DO NOTHING
            """,
            job.id,
            job.repo_url,
            "completed",
        )
        await postgres.execute(
            """
            INSERT INTO projects (id, job_id, repo_url, name, language, framework, total_files, total_loc)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (id) DO NOTHING
            """,
            job.id,
            job.id,
            job.repo_url,
            project_name,
            project_model.language or "unknown",
            project_model.framework or "unknown",
            project_model.total_files,
            project_model.total_loc,
        )

        indexer = EmbeddingIndexer(postgres=postgres)
        count = await indexer.index_chunks(
            project_id=job.id,
            chunks=chunks,
            embeddings=embeddings,
        )
        logger.info("Indexed %d embeddings for RAG — job_id=%s", count, job.id)
    finally:
        await postgres.close()


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


# ---------------------------------------------------------------------------
# POST /analyze/retry — Retry only failed agents
# ---------------------------------------------------------------------------

# Map of agent names to their constructors
AGENT_REGISTRY: dict[str, type] = {
    "repository_agent": RepositoryAgent,
    "architecture_agent": ArchitectureAgent,
    "quality_agent": QualityAgent,
    "security_agent": SecurityAgent,
    "documentation_agent": DocumentationAgent,
    "modernization_agent": ModernizationAgent,
    "kiro_agent": KiroAgent,
}


async def _run_retry_pipeline(
    job: AnalysisJob, failed_agents: list[str], webhook_url: str
) -> None:
    """Re-execute only the specified failed agents using existing job context.

    Rebuilds the PipelineContext from the job's stored results, re-clones the
    repo if needed (for agents like security that need repo_path), and runs
    only the requested agents.
    """
    from src.adapters.git_adapter import GitAdapter

    settings = get_settings()

    job.status = JobStatus.ANALYZING
    job.error_message = None

    # Rebuild PipelineContext from existing job data
    from src.agents.base import PipelineContext

    context = PipelineContext(job_id=job.id, repo_url=job.repo_url)
    context.project_model = job.project
    context.architecture_report = job.architecture_report
    context.quality_report = job.quality_report
    context.security_report = job.security_report
    context.documentation_bundle = job.documentation_bundle
    context.modernization_plan = job.modernization_plan
    context.kiro_spec = job.kiro_spec

    # Re-clone repo if any agent needs repo_path (security_agent needs it)
    needs_repo = any(a in failed_agents for a in ["repository_agent", "security_agent"])
    if needs_repo and job.repo_url:
        git_adapter = GitAdapter()
        clone_dest = Path(settings.clone_temp_dir) / str(job.id)
        if not clone_dest.exists():
            logger.info("Re-cloning repo for retry — job_id=%s", job.id)
            await git_adapter.clone(job.repo_url, clone_dest)
        context.repo_path = str(clone_dest)

    # Filter to only the failed agents requested, in execution order
    agents_to_run = []
    for agent_name in failed_agents:
        if agent_name in AGENT_REGISTRY:
            agents_to_run.append(AGENT_REGISTRY[agent_name]())

    agents_to_run.sort(key=lambda a: a.execution_order)

    # Remove old failed results for these agents
    job.agent_results = [
        r for r in job.agent_results if r.agent_name not in failed_agents
    ]

    # Create webhook adapter
    webhook_adapter = WebhookAdapter(
        webhook_url=webhook_url,
        webhook_secret=settings.webhook_secret,
    )

    logger.info(
        "Retry pipeline started — job_id=%s, agents=%s",
        job.id,
        [a.name for a in agents_to_run],
    )

    for agent in agents_to_run:
        job.current_agent = agent.name

        if not agent.can_execute(context):
            logger.info("Retry: agent skipped (can_execute=False) — agent=%s", agent.name)
            continue

        logger.info("Retry: agent starting — agent=%s, job_id=%s", agent.name, job.id)

        try:
            output = await agent.execute(context)

            # Apply output to context
            for key, value in output.context_updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)

            from src.domain.models.agent_result import AgentResult, AgentStatus

            result = AgentResult(
                agent_name=agent.name,
                status=AgentStatus.COMPLETED,
                execution_order=agent.execution_order,
                output=output.data,
            )
            context.agent_results.append(result)
            job.agent_results.append(result)

            logger.info("Retry: agent completed — agent=%s", agent.name)

        except Exception as exc:  # noqa: BLE001
            from src.domain.models.agent_result import AgentResult, AgentStatus

            result = AgentResult(
                agent_name=agent.name,
                status=AgentStatus.FAILED,
                execution_order=agent.execution_order,
                error_message=str(exc),
            )
            context.agent_results.append(result)
            job.agent_results.append(result)

            logger.warning(
                "Retry: agent failed — agent=%s, error=%s", agent.name, str(exc)
            )

    # Update job with new results
    job.status = JobStatus.COMPLETED
    job.current_agent = None
    if context.architecture_report:
        job.architecture_report = context.architecture_report
    if context.quality_report:
        job.quality_report = context.quality_report
    if context.security_report:
        job.security_report = context.security_report
    if context.documentation_bundle:
        job.documentation_bundle = context.documentation_bundle
    if context.modernization_plan:
        job.modernization_plan = context.modernization_plan
    if context.kiro_spec:
        job.kiro_spec = context.kiro_spec

    logger.info("Retry pipeline completed — job_id=%s", job.id)

    # Send webhook
    try:
        await webhook_adapter.notify_completion({
            "jobId": str(job.id),
            "status": "completed",
            "projectId": str(job.project.id) if job.project else None,
            "agentsStatus": {r.agent_name: r.status.value for r in job.agent_results},
        })
    except Exception as exc:  # noqa: BLE001
        logger.error("Retry webhook failed — job_id=%s, error=%s", job.id, str(exc))


@router.post(
    "/retry",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RetryResponse,
    summary="Retry failed agents for an existing analysis",
)
async def retry_failed_agents(
    request: RetryRequest,
    background_tasks: BackgroundTasks,
) -> RetryResponse:
    """Re-run only the failed agents from a previous analysis.

    Uses the existing job context (project model, reports) and only
    executes the specified agents. Returns 202 immediately.
    """
    job = jobs.get(request.job_id)
    if job is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail=f"Job {request.job_id} not found in memory. Only recent jobs can be retried.",
        )

    # Validate requested agents exist
    valid_agents = [a for a in request.failed_agents if a in AGENT_REGISTRY]
    if not valid_agents:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail=f"No valid agents to retry. Available: {list(AGENT_REGISTRY.keys())}",
        )

    background_tasks.add_task(_run_retry_pipeline, job, valid_agents, request.webhook_url)

    logger.info(
        "Retry accepted — job_id=%s, agents=%s",
        request.job_id,
        valid_agents,
    )

    return RetryResponse(
        job_id=request.job_id,
        status="retrying",
        retrying_agents=valid_agents,
    )
