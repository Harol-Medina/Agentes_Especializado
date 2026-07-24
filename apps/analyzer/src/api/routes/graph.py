"""GET /graph/{job_id} — Serve graph data with optional filters.

Returns the dependency graph (nodes and edges) built during the
repository analysis phase. Supports filtering by module, edge type,
and depth.

The job_id parameter accepts the analysis job UUID. The frontend uses
the jobId as the projectId for graph queries.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from src.api.job_store import jobs
from src.api.schemas import GraphEdgeSchema, GraphNodeSchema, GraphResponse, GraphStats
from src.domain.models.analysis_job import JobStatus

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get(
    "/{project_id}",
    response_model=GraphResponse,
    summary="Retrieve project dependency graph",
)
async def get_graph(
    project_id: UUID,
    module: Optional[str] = Query(default=None, description="Filter by module name"),
    edge_type: Optional[str] = Query(
        default=None,
        alias="edgeType",
        description="Filter edges by type (import | inheritance | usage | composition)",
    ),
    depth: Optional[int] = Query(
        default=None,
        ge=1,
        description="Maximum traversal depth from the filtered module",
    ),
) -> GraphResponse:
    """Return nodes and edges for *project_id*, optionally filtered.

    Uses the job_id as the project identifier to look up the in-memory
    graph data built by the RepositoryAgent.
    """
    # Look up the job by ID (frontend sends jobId as projectId)
    job = jobs.get(project_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )

    if job.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Analysis for {project_id} has not completed yet (status: {job.status.value})",
        )

    project = job.project
    if project is None:
        return GraphResponse(
            project_id=project_id,
            nodes=[],
            edges=[],
            stats=GraphStats(),
        )

    # Convert domain models to API schemas
    nodes = [
        GraphNodeSchema(
            id=node.id,
            type=node.node_type.value,
            name=node.name,
            qualified_name=node.qualified_name,
            file_path=node.file_path,
            loc=node.loc,
            complexity=node.complexity,
            metadata=node.metadata,
        )
        for node in project.nodes
    ]

    edges = [
        GraphEdgeSchema(
            id=edge.id,
            source=edge.source_node_id,
            target=edge.target_node_id,
            type=edge.edge_type.value,
            metadata=edge.metadata,
        )
        for edge in project.edges
    ]

    # Apply filters
    filtered_nodes = nodes
    filtered_edges = edges

    if module:
        # Filter nodes by module/file path containing the module name
        filtered_nodes = [
            n for n in nodes
            if (n.file_path and module.lower() in n.file_path.lower())
            or (n.qualified_name and module.lower() in n.qualified_name.lower())
            or module.lower() in n.name.lower()
        ]
        # Filter edges to only include those between filtered nodes
        node_ids = {n.id for n in filtered_nodes}
        filtered_edges = [
            e for e in edges
            if e.source in node_ids or e.target in node_ids
        ]

    if edge_type:
        filtered_edges = [
            e for e in filtered_edges
            if e.type == edge_type
        ]

    return GraphResponse(
        project_id=project_id,
        nodes=filtered_nodes,
        edges=filtered_edges,
        stats=GraphStats(
            total_nodes=len(nodes),
            total_edges=len(edges),
            filtered_nodes=len(filtered_nodes),
            filtered_edges=len(filtered_edges),
        ),
    )
