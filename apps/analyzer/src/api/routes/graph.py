"""GET /graph/{project_id} — Serve graph data with optional filters.

Internal endpoint used by the Analyzer's own pipeline components (e.g.
re-ranking during RAG).  The Backend reads graph data directly from
PostgreSQL; this endpoint is not part of the public API surface.

Full implementation in task 9.2 (graph.py route + filter support).
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query

from src.api.schemas import GraphResponse, GraphStats

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

    All active filters are applied simultaneously (AND semantics).
    """
    # TODO (task 9.2): query PostgreSQL for nodes/edges with SQL filters
    return GraphResponse(
        project_id=project_id,
        nodes=[],
        edges=[],
        stats=GraphStats(
            total_nodes=0,
            total_edges=0,
            filtered_nodes=0,
            filtered_edges=0,
        ),
    )
