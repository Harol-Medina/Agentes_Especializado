"""Unit tests for AgentPipeline orchestrator."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.agents.base import (
    AgentExecutionError,
    AgentOutput,
    BaseAgent,
    PipelineContext,
)
from src.agents.pipeline import AgentPipeline, PipelineTerminatedError
from src.domain.models.agent_result import AgentStatus


# ---------------------------------------------------------------------------
# Helpers — concrete agent stubs
# ---------------------------------------------------------------------------


class StubAgent(BaseAgent):
    """Configurable stub agent for testing."""

    def __init__(
        self,
        name: str,
        order: int,
        *,
        output_data: dict | None = None,
        context_updates: dict | None = None,
        should_fail: bool = False,
        fail_message: str = "test failure",
        can_run: bool = True,
    ):
        self._name = name
        self._order = order
        self._output_data = output_data or {}
        self._context_updates = context_updates or {}
        self._should_fail = should_fail
        self._fail_message = fail_message
        self._can_run = can_run

    @property
    def name(self) -> str:
        return self._name

    @property
    def execution_order(self) -> int:
        return self._order

    async def execute(self, context: PipelineContext) -> AgentOutput:
        if self._should_fail:
            raise AgentExecutionError(self._name, self._fail_message)
        return AgentOutput(
            agent_name=self._name,
            status=AgentStatus.COMPLETED,
            data=self._output_data,
            context_updates=self._context_updates,
        )

    def can_execute(self, context: PipelineContext) -> bool:
        return self._can_run


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def webhook_adapter():
    """Mock webhook adapter with async notify_completion."""
    adapter = MagicMock()
    adapter.notify_completion = AsyncMock()
    return adapter


@pytest.fixture
def job_id():
    return uuid4()


@pytest.fixture
def repo_url():
    return "https://github.com/owner/repo"


# ---------------------------------------------------------------------------
# Tests: Successful pipeline execution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_executes_agents_in_order(webhook_adapter, job_id, repo_url):
    """Agents should execute in ascending execution_order."""
    execution_log: list[str] = []

    class LoggingAgent(StubAgent):
        async def execute(self, context: PipelineContext) -> AgentOutput:
            execution_log.append(self._name)
            return await super().execute(context)

    agents = [
        LoggingAgent("kiro_agent", 7),
        LoggingAgent("repository_agent", 1, can_run=True),
        LoggingAgent("architecture_agent", 2),
    ]
    # Override can_execute for repo agent (doesn't need project_model)
    agents[1].can_execute = lambda ctx: True

    pipeline = AgentPipeline(agents, webhook_adapter)
    # Set project_model so non-repo agents can run
    ctx = await _run_with_project_model(pipeline, job_id, repo_url, agents)

    assert execution_log == ["repository_agent", "architecture_agent", "kiro_agent"]


@pytest.mark.asyncio
async def test_pipeline_accumulates_context(webhook_adapter, job_id, repo_url):
    """Each agent's context_updates should be visible to subsequent agents."""
    repo_agent = StubAgent(
        "repository_agent",
        1,
        context_updates={"repo_path": "/tmp/repos/test"},
    )
    repo_agent.can_execute = lambda ctx: True

    arch_agent = StubAgent(
        "architecture_agent",
        2,
        context_updates={"architecture_report": {"patterns": ["mvc"]}},
    )
    # arch agent uses default can_execute which needs project_model
    # We'll set it to always run for simplicity
    arch_agent.can_execute = lambda ctx: True

    pipeline = AgentPipeline([repo_agent, arch_agent], webhook_adapter)
    context = await pipeline.execute(job_id, repo_url)

    assert context.repo_path == "/tmp/repos/test"
    assert context.architecture_report == {"patterns": ["mvc"]}


@pytest.mark.asyncio
async def test_pipeline_sends_webhook_on_completion(webhook_adapter, job_id, repo_url):
    """Webhook should be called with correct payload on successful completion."""
    agent = StubAgent("repository_agent", 1)
    agent.can_execute = lambda ctx: True

    pipeline = AgentPipeline([agent], webhook_adapter)
    await pipeline.execute(job_id, repo_url)

    webhook_adapter.notify_completion.assert_called_once()
    payload = webhook_adapter.notify_completion.call_args[0][0]

    assert payload["jobId"] == str(job_id)
    assert payload["status"] == "completed"
    assert payload["agentsStatus"]["repository_agent"] == "completed"


@pytest.mark.asyncio
async def test_pipeline_records_agent_results(webhook_adapter, job_id, repo_url):
    """All agent results should be recorded in the context."""
    agents = [
        StubAgent("repository_agent", 1),
        StubAgent("architecture_agent", 2),
    ]
    agents[0].can_execute = lambda ctx: True
    agents[1].can_execute = lambda ctx: True

    pipeline = AgentPipeline(agents, webhook_adapter)
    context = await pipeline.execute(job_id, repo_url)

    assert len(context.agent_results) == 2
    assert context.agent_results[0].agent_name == "repository_agent"
    assert context.agent_results[0].status == AgentStatus.COMPLETED
    assert context.agent_results[1].agent_name == "architecture_agent"
    assert context.agent_results[1].status == AgentStatus.COMPLETED


# ---------------------------------------------------------------------------
# Tests: Graceful degradation — non-critical agent failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_continues_on_non_critical_failure(webhook_adapter, job_id, repo_url):
    """Non-critical agent failure should not stop the pipeline."""
    agents = [
        StubAgent("repository_agent", 1),
        StubAgent("quality_agent", 3, should_fail=True, fail_message="quality error"),
        StubAgent("security_agent", 4),
    ]
    for a in agents:
        a.can_execute = lambda ctx: True

    pipeline = AgentPipeline(agents, webhook_adapter)
    context = await pipeline.execute(job_id, repo_url)

    statuses = {r.agent_name: r.status for r in context.agent_results}
    assert statuses["repository_agent"] == AgentStatus.COMPLETED
    assert statuses["quality_agent"] == AgentStatus.FAILED
    assert statuses["security_agent"] == AgentStatus.COMPLETED


@pytest.mark.asyncio
async def test_failed_agent_has_error_message(webhook_adapter, job_id, repo_url):
    """Failed agents should record the error message."""
    agent = StubAgent("quality_agent", 3, should_fail=True, fail_message="oops")
    agent.can_execute = lambda ctx: True

    repo_agent = StubAgent("repository_agent", 1)
    repo_agent.can_execute = lambda ctx: True

    pipeline = AgentPipeline([repo_agent, agent], webhook_adapter)
    context = await pipeline.execute(job_id, repo_url)

    quality_result = next(r for r in context.agent_results if r.agent_name == "quality_agent")
    assert quality_result.status == AgentStatus.FAILED
    assert "oops" in quality_result.error_message


# ---------------------------------------------------------------------------
# Tests: Critical failure — Repository_Agent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_terminates_on_repository_agent_failure(
    webhook_adapter, job_id, repo_url
):
    """If repository_agent fails, pipeline should raise PipelineTerminatedError."""
    agents = [
        StubAgent(
            "repository_agent", 1, should_fail=True, fail_message="clone failed"
        ),
        StubAgent("architecture_agent", 2),
    ]
    agents[0].can_execute = lambda ctx: True
    agents[1].can_execute = lambda ctx: True

    pipeline = AgentPipeline(agents, webhook_adapter)

    with pytest.raises(PipelineTerminatedError) as exc_info:
        await pipeline.execute(job_id, repo_url)

    assert "clone failed" in exc_info.value.message


@pytest.mark.asyncio
async def test_remaining_agents_skipped_on_critical_failure(
    webhook_adapter, job_id, repo_url
):
    """Agents after repository_agent should be marked SKIPPED on critical failure."""
    agents = [
        StubAgent("repository_agent", 1, should_fail=True),
        StubAgent("architecture_agent", 2),
        StubAgent("quality_agent", 3),
    ]
    agents[0].can_execute = lambda ctx: True

    pipeline = AgentPipeline(agents, webhook_adapter)

    with pytest.raises(PipelineTerminatedError):
        await pipeline.execute(job_id, repo_url)

    # Webhook should still be called with status=failed
    webhook_adapter.notify_completion.assert_called_once()
    payload = webhook_adapter.notify_completion.call_args[0][0]
    assert payload["status"] == "failed"
    assert payload["agentsStatus"]["repository_agent"] == "failed"
    assert payload["agentsStatus"]["architecture_agent"] == "skipped"
    assert payload["agentsStatus"]["quality_agent"] == "skipped"


# ---------------------------------------------------------------------------
# Tests: Skipped agents (can_execute returns False)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_skipped_when_cannot_execute(webhook_adapter, job_id, repo_url):
    """Agents that return can_execute=False should be marked SKIPPED."""
    agents = [
        StubAgent("repository_agent", 1),
        StubAgent("architecture_agent", 2, can_run=False),
    ]
    agents[0].can_execute = lambda ctx: True

    pipeline = AgentPipeline(agents, webhook_adapter)
    context = await pipeline.execute(job_id, repo_url)

    arch_result = next(r for r in context.agent_results if r.agent_name == "architecture_agent")
    assert arch_result.status == AgentStatus.SKIPPED


# ---------------------------------------------------------------------------
# Tests: Webhook failure is non-fatal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_failure_does_not_crash_pipeline(job_id, repo_url):
    """If webhook notification fails, pipeline still returns successfully."""
    webhook = MagicMock()
    webhook.notify_completion = AsyncMock(side_effect=ConnectionError("network down"))

    agent = StubAgent("repository_agent", 1)
    agent.can_execute = lambda ctx: True

    pipeline = AgentPipeline([agent], webhook)
    # Should not raise
    context = await pipeline.execute(job_id, repo_url)

    assert context.agent_results[0].status == AgentStatus.COMPLETED


# ---------------------------------------------------------------------------
# Tests: Timing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_results_have_timestamps(webhook_adapter, job_id, repo_url):
    """Completed agents should have started_at and completed_at set."""
    agent = StubAgent("repository_agent", 1)
    agent.can_execute = lambda ctx: True

    pipeline = AgentPipeline([agent], webhook_adapter)
    context = await pipeline.execute(job_id, repo_url)

    result = context.agent_results[0]
    assert result.started_at is not None
    assert result.completed_at is not None
    assert result.completed_at >= result.started_at


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _run_with_project_model(
    pipeline: AgentPipeline, job_id, repo_url, agents
) -> PipelineContext:
    """Run pipeline — the first agent sets a fake project_model so others can execute."""
    from src.domain.models.project_model import ProjectModel

    # Patch repository_agent to inject project_model
    original_execute = agents[1].__class__.execute

    async def patched_execute(self, context):
        context.project_model = ProjectModel(name="test", repo_url=repo_url)
        return AgentOutput(
            agent_name=self._name,
            status=AgentStatus.COMPLETED,
            data={},
            context_updates={"project_model": context.project_model},
        )

    agents[1].execute = lambda ctx: patched_execute(agents[1], ctx)
    return await pipeline.execute(job_id, repo_url)
