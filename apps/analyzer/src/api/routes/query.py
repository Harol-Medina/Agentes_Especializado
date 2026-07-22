"""POST /query — RAG chat endpoint with Server-Sent Events streaming.

Accepts a natural language question about an analysed project and streams
the generated answer back token-by-token.  Full implementation in task 7.3;
this stub validates the schema and returns a placeholder SSE response.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from src.api.schemas import QueryRequest

router = APIRouter(prefix="/query", tags=["query"])


async def _stub_sse_stream(project_id: str, question: str):
    """Placeholder SSE generator — replaced in task 7.3."""
    yield "event: no_context\n"
    yield f'data: {{"message": "RAG not yet implemented for project {project_id}"}}\n\n'


@router.post(
    "",
    summary="RAG chat query (SSE)",
    response_class=StreamingResponse,
)
async def rag_query(request: QueryRequest) -> StreamingResponse:
    """Stream a RAG-generated answer for the given question.

    Emits SSE events: ``context``, ``token``, ``heartbeat``,
    ``no_context``, and ``done``.
    """
    # TODO (task 7.3): implement real retrieval + generation pipeline
    return StreamingResponse(
        _stub_sse_stream(str(request.project_id), request.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
