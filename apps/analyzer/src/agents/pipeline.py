"""AgentPipeline orchestrator — sequential execution with graceful degradation.

Implements requirements 6.1, 6.2, 6.3, 13.1, 13.2:
- Agents execute sequentially in defined order (1–7).
- Each agent receives accumulated context from all previous agents.
- Repository_Agent failure terminates the pipeline.
- Any other agent failure is recorded and the pipeline continues.
- On completion, a webhook notifies the Backend.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from src.agents.base import (
    AgentExecutionError,
    AgentOutput,
    BaseAgent,
    PipelineContext,
)
from src.domain.models.agent_result import AgentResult, AgentStatus
from src.domain.models.analysis_job import JobStatus

logger = logging.getLogger(__name__)


class PipelineTerminatedError(Exception):
    """Raised when a critical agent (Repository_Agent) fails, halting the pipeline."""

    def __init__(self, message: str, job_id: UUID | None = None) -> None:
        self.message = message
        self.job_id = job_id
        super().__init__(message)


class AgentPipeline:
    """Orchestrates sequential execution of agents with graceful degradation.

    - Agents run in ascending ``execution_order``.
    - Each agent receives accumulated context from all previous agents.
    - If **Repository_Agent** (execution_order == 1) fails → pipeline terminates.
    - If any subsequent agent fails → mark FAILED, continue with remaining.
    - Agents that cannot execute (``can_execute`` returns False) → mark SKIPPED.
    - On completion (full or partial), sends a webhook notification to Backend.
    """

    # The agent name whose failure terminates the pipeline.
    CRITICAL_AGENT: str = "repository_agent"

    def __init__(self, agents: list[BaseAgent], webhook_adapter: Any) -> None:
        """
        Args:
            agents: List of concrete agent instances to execute.
            webhook_adapter: Adapter responsible for notifying the Backend on completion.
        """
        self._agents = sorted(agents, key=lambda a: a.execution_order)
        self._webhook = webhook_adapter
        self._on_agent_complete = None
        self._on_agent_start = None
        self._cancel_check = None

    def set_on_agent_complete(self, callback) -> None:
        """Set a callback invoked after each agent completes.

        The callback receives (agent_name: str, context: PipelineContext).
        Used to update the job store incrementally for progressive results.
        """
        self._on_agent_complete = callback

    def set_on_agent_start(self, callback) -> None:
        """Set a callback invoked before each agent starts executing.

        The callback receives (agent_name: str, context: PipelineContext).
        Used to update the job's current_agent for real-time progress tracking.
        """
        self._on_agent_start = callback

    def set_cancel_check(self, check_fn) -> None:
        """Set a function that returns True if the pipeline should stop.

        Checked before each agent execution. The function takes no arguments
        and returns a boolean.
        """
        self._cancel_check = check_fn

    async def execute(self, job_id: UUID, repo_url: str) -> PipelineContext:
        """Execute the full agent pipeline.

        Returns:
            The final PipelineContext with accumulated results.

        Raises:
            PipelineTerminatedError: If the critical agent (Repository_Agent) fails.
        """
        context = PipelineContext(job_id=job_id, repo_url=repo_url)
        job_status: JobStatus = JobStatus.ANALYZING

        logger.info(
            "Pipeline started — job_id=%s, repo_url=%s, agents=%d",
            job_id,
            repo_url,
            len(self._agents),
        )

        for agent in self._agents:
            # --- Cancellation check ---
            if self._cancel_check is not None and self._cancel_check():
                logger.info(
                    "Pipeline cancelled before agent=%s, job_id=%s",
                    agent.name,
                    job_id,
                )
                # Mark remaining agents as SKIPPED
                for remaining_agent in self._agents:
                    if remaining_agent.execution_order >= agent.execution_order:
                        already_recorded = any(
                            r.agent_name == remaining_agent.name
                            for r in context.agent_results
                        )
                        if not already_recorded:
                            skip_result = AgentResult(
                                agent_name=remaining_agent.name,
                                status=AgentStatus.SKIPPED,
                                execution_order=remaining_agent.execution_order,
                            )
                            context.agent_results.append(skip_result)

                job_status = JobStatus.FAILED  # Will be overridden to CANCELLED by caller
                await self._notify_webhook(context, job_status)
                raise PipelineTerminatedError(
                    "Pipeline cancelled by user request",
                    job_id=job_id,
                )

            # --- Pre-execution check ---
            if not agent.can_execute(context):
                self._mark_skipped(context, agent)
                continue

            # --- Execute agent ---
            result = AgentResult(
                agent_name=agent.name,
                status=AgentStatus.RUNNING,
                execution_order=agent.execution_order,
                started_at=datetime.now(timezone.utc),
            )

            # Notify start callback for real-time progress
            if self._on_agent_start is not None:
                try:
                    self._on_agent_start(agent.name, context)
                except Exception:  # noqa: BLE001
                    pass

            logger.info(
                "Agent starting — agent=%s, order=%d, job_id=%s",
                agent.name,
                agent.execution_order,
                job_id,
            )

            try:
                output = await agent.execute(context)
                self._apply_output(context, result, output)

            except AgentExecutionError as exc:
                if agent.name == self.CRITICAL_AGENT:
                    # Critical failure — terminate the pipeline
                    self._mark_failed(context, result, str(exc))
                    job_status = JobStatus.FAILED

                    logger.error(
                        "Critical agent failed — terminating pipeline. "
                        "agent=%s, job_id=%s, error=%s",
                        agent.name,
                        job_id,
                        exc.message,
                    )

                    # Mark remaining agents as SKIPPED
                    self._skip_remaining(context, agent)

                    # Notify backend about the failure
                    await self._notify_webhook(context, job_status)

                    raise PipelineTerminatedError(
                        f"Repository agent failed: {exc.message}",
                        job_id=job_id,
                    ) from exc

                # Non-critical failure — record and continue
                self._mark_failed(context, result, str(exc))
                logger.warning(
                    "Agent failed (non-critical) — continuing pipeline. "
                    "agent=%s, job_id=%s, error=%s",
                    agent.name,
                    job_id,
                    str(exc),
                )

            except Exception as exc:  # noqa: BLE001
                # Unexpected errors treated same as AgentExecutionError
                if agent.name == self.CRITICAL_AGENT:
                    self._mark_failed(context, result, str(exc))
                    job_status = JobStatus.FAILED

                    logger.error(
                        "Critical agent raised unexpected error — terminating. "
                        "agent=%s, job_id=%s, error=%s",
                        agent.name,
                        job_id,
                        str(exc),
                    )

                    self._skip_remaining(context, agent)
                    await self._notify_webhook(context, job_status)

                    raise PipelineTerminatedError(
                        f"Repository agent failed unexpectedly: {exc}",
                        job_id=job_id,
                    ) from exc

                self._mark_failed(context, result, str(exc))
                logger.warning(
                    "Agent raised unexpected error (non-critical) — continuing. "
                    "agent=%s, job_id=%s, error=%s",
                    agent.name,
                    job_id,
                    str(exc),
                )

        # --- Pipeline finished successfully (full or partial) ---
        job_status = JobStatus.COMPLETED
        logger.info("Pipeline completed — job_id=%s", job_id)

        await self._notify_webhook(context, job_status)
        return context

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _apply_output(
        self,
        context: PipelineContext,
        result: AgentResult,
        output: AgentOutput,
    ) -> None:
        """Merge agent output into pipeline context and record success."""
        result.status = AgentStatus.COMPLETED
        result.completed_at = datetime.now(timezone.utc)
        result.output = output.data

        # Merge context_updates into PipelineContext fields
        for key, value in output.context_updates.items():
            if hasattr(context, key):
                setattr(context, key, value)

        context.agent_results.append(result)

        logger.info(
            "Agent completed — agent=%s, context_keys_updated=%s",
            output.agent_name,
            list(output.context_updates.keys()),
        )

        # Notify the callback for progressive results
        if self._on_agent_complete is not None:
            try:
                self._on_agent_complete(output.agent_name, context)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "on_agent_complete callback failed — agent=%s, error=%s",
                    output.agent_name,
                    str(exc),
                )

    def _mark_skipped(self, context: PipelineContext, agent: BaseAgent) -> None:
        """Record an agent as SKIPPED (can_execute returned False)."""
        result = AgentResult(
            agent_name=agent.name,
            status=AgentStatus.SKIPPED,
            execution_order=agent.execution_order,
        )
        context.agent_results.append(result)

        logger.info(
            "Agent skipped — agent=%s (can_execute=False)",
            agent.name,
        )

    def _mark_failed(
        self,
        context: PipelineContext,
        result: AgentResult,
        error_message: str,
    ) -> None:
        """Record an agent as FAILED."""
        result.status = AgentStatus.FAILED
        result.completed_at = datetime.now(timezone.utc)
        result.error_message = error_message
        context.agent_results.append(result)

    def _skip_remaining(self, context: PipelineContext, failed_agent: BaseAgent) -> None:
        """Mark all agents after the failed critical agent as SKIPPED."""
        for agent in self._agents:
            if agent.execution_order > failed_agent.execution_order:
                # Only skip if not already recorded
                already_recorded = any(
                    r.agent_name == agent.name for r in context.agent_results
                )
                if not already_recorded:
                    result = AgentResult(
                        agent_name=agent.name,
                        status=AgentStatus.SKIPPED,
                        execution_order=agent.execution_order,
                    )
                    context.agent_results.append(result)

    async def _notify_webhook(
        self,
        context: PipelineContext,
        job_status: JobStatus,
    ) -> None:
        """Send completion webhook to the Backend.

        Payload:
            {
                "jobId": "uuid",
                "status": "completed" | "failed",
                "projectId": "uuid" | null,
                "agentsStatus": {"agent_name": "completed"|"failed"|"skipped", ...}
            }
        """
        agents_status: dict[str, str] = {
            r.agent_name: r.status.value for r in context.agent_results
        }

        project_id: str | None = None
        if context.project_model is not None:
            project_id = str(context.project_model.id)

        payload = {
            "jobId": str(context.job_id),
            "status": job_status.value,
            "projectId": project_id,
            "agentsStatus": agents_status,
        }

        try:
            # webhook_adapter.notify_completion is expected to accept the payload dict.
            # The full implementation (HMAC signing, retries) lives in task 4.8.
            if hasattr(self._webhook, "notify_completion"):
                await self._webhook.notify_completion(payload)
            logger.info(
                "Webhook notification sent — job_id=%s, status=%s",
                context.job_id,
                job_status.value,
            )
        except Exception as exc:  # noqa: BLE001
            # Webhook failure is non-fatal (requirement: retry 3x then log)
            logger.error(
                "Webhook notification failed — job_id=%s, error=%s",
                context.job_id,
                str(exc),
            )
