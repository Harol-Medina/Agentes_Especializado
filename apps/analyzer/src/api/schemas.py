"""Pydantic v2 request/response schemas for the Analyzer REST API.

These models define the wire format for every public endpoint.  They are
deliberately kept separate from the internal domain models so that API
contracts can evolve independently of the domain.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# POST /analyze
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    """Payload sent by the Backend to initiate a new analysis job."""

    repo_url: str = Field(
        ...,
        description="Public GitHub repository URL (https://github.com/{owner}/{repo})",
        examples=["https://github.com/spring-projects/spring-petclinic"],
    )
    job_id: UUID = Field(
        ...,
        description="Job UUID pre-created by the Backend; used to correlate results.",
    )
    webhook_url: str = Field(
        ...,
        description="Backend endpoint that receives the completion webhook.",
        examples=["http://backend:8080/api/webhooks/analysis-complete"],
    )


class AnalyzeResponse(BaseModel):
    """Immediate 202 response confirming the job was accepted."""

    job_id: UUID
    status: str = Field(default="pending", description="Initial job status.")
    estimated_duration: str = Field(
        default="5-15 minutes",
        description="Human-readable estimate of how long the analysis will take.",
    )


# ---------------------------------------------------------------------------
# GET /jobs/{job_id}
# ---------------------------------------------------------------------------


class AgentProgressItem(BaseModel):
    """Status snapshot for a single agent within a pipeline run."""

    name: str
    status: str  # pending | running | completed | failed | skipped
    execution_order: int


class JobProgress(BaseModel):
    """Aggregated progress info returned by the job-status endpoint."""

    completed_agents: list[str] = Field(default_factory=list)
    current_agent: Optional[str] = None
    pending_agents: list[str] = Field(default_factory=list)
    failed_agents: list[str] = Field(default_factory=list)
    agents: list[AgentProgressItem] = Field(default_factory=list)


class JobStatusResponse(BaseModel):
    """Full job status response including per-agent progress."""

    job_id: UUID
    status: str  # pending | cloning | analyzing | completed | failed
    current_agent: Optional[str] = None
    progress: JobProgress = Field(default_factory=JobProgress)
    error_message: Optional[str] = None


# ---------------------------------------------------------------------------
# POST /query  (RAG — SSE streaming)
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    """Payload for a RAG chat query."""

    model_config = {"populate_by_name": True}

    project_id: UUID = Field(..., alias="projectId", description="ID of the analysed project.")
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural language question about the codebase.",
    )
    max_chunks: int = Field(
        default=10,
        alias="maxChunks",
        ge=1,
        le=50,
        description="Maximum number of context chunks to retrieve.",
    )


# ---------------------------------------------------------------------------
# GET /graph/{project_id}
# ---------------------------------------------------------------------------


class GraphNodeSchema(BaseModel):
    """Wire representation of a graph node."""

    id: UUID
    type: str  # file | class | function | module | package
    name: str
    qualified_name: Optional[str] = None
    file_path: Optional[str] = None
    loc: int = 0
    complexity: int = 1
    is_external: bool = False
    metadata: dict = Field(default_factory=dict)


class GraphEdgeSchema(BaseModel):
    """Wire representation of a directed graph edge."""

    id: UUID
    source: UUID
    target: UUID
    type: str  # import | inheritance | usage | composition
    metadata: dict = Field(default_factory=dict)


class GraphStats(BaseModel):
    """Summary statistics for a graph response."""

    total_nodes: int = 0
    total_edges: int = 0
    filtered_nodes: int = 0
    filtered_edges: int = 0


class GraphResponse(BaseModel):
    """Full graph data response."""

    project_id: UUID
    nodes: list[GraphNodeSchema] = Field(default_factory=list)
    edges: list[GraphEdgeSchema] = Field(default_factory=list)
    stats: GraphStats = Field(default_factory=GraphStats)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Response for the GET /health endpoint."""

    status: str = "ok"
    service: str = "analyzer"
