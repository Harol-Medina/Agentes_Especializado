"""POST /query — RAG chat endpoint with Server-Sent Events streaming.

Accepts a natural language question about an analysed project and streams
the generated answer back as SSE events. Uses pgvector cosine similarity
for retrieval and Claude Sonnet for response generation.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from src.adapters.bedrock_adapter import BedrockAdapter
from src.adapters.postgres_adapter import PostgresAdapter
from src.api.schemas import QueryRequest
from src.rag.embeddings import TitanEmbeddingsClient
from src.rag.generator import RAGGenerator
from src.rag.retriever import RAGRetriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


async def _sse_stream(
    request: QueryRequest,
    postgres: PostgresAdapter,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for a RAG query.

    Flow:
    1. Retrieve relevant chunks via RAGRetriever.
    2. If no chunks pass threshold, yield 'no_context' event.
    3. Generate response via RAGGenerator.
    4. Yield SSE events with response tokens.
    5. Yield 'done' event at end.
    """
    # Initialize components
    embeddings = TitanEmbeddingsClient()
    retriever = RAGRetriever(postgres=postgres, embeddings=embeddings)
    bedrock = BedrockAdapter()
    generator = RAGGenerator(bedrock=bedrock)

    # 1. Retrieve relevant chunks
    chunks = await retriever.retrieve(
        project_id=request.project_id,
        question=request.question,
        max_chunks=request.max_chunks,
    )

    # 2. If no chunks pass threshold, emit no_context event
    if not chunks:
        no_context_msg = (
            "I don't have enough context about this project to answer "
            "your question. Please ensure the project has been fully "
            "analysed and try again with a more specific question."
        )
        yield f"event: no_context\ndata: {json.dumps({'message': no_context_msg})}\n\n"
        yield "event: done\ndata: {}\n\n"
        return

    # Emit context event with source files and scores
    context_info = [
        {"file": chunk.file_path, "score": round(chunk.similarity, 3)}
        for chunk in chunks
    ]
    yield f"event: context\ndata: {json.dumps({'chunks': context_info})}\n\n"

    # 3. Generate response via RAGGenerator (streaming)
    # Derive project name from the first chunk's file path or use project_id
    project_name = str(request.project_id)

    async for token in generator.generate_stream(
        question=request.question,
        chunks=chunks,
        project_name=project_name,
    ):
        yield f"event: token\ndata: {json.dumps({'content': token})}\n\n"

    # 4. Done event
    yield "event: done\ndata: {}\n\n"


@router.post(
    "",
    summary="RAG query with SSE streaming",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
)
async def rag_query(request: QueryRequest) -> StreamingResponse:
    """Stream a RAG-generated answer for the given question.

    POST /query — accepts {project_id, question, max_chunks}.
    Returns SSE stream with events: context, token, no_context, done.

    The endpoint creates its own PostgresAdapter connection for the duration
    of the request. In production, this would be injected via FastAPI dependencies.
    """
    # Create a PostgresAdapter for this request
    # In production, this is injected via DI (dependencies.py)
    postgres = PostgresAdapter()
    await postgres.connect()

    async def stream_with_cleanup() -> AsyncGenerator[str, None]:
        """Wrap the SSE stream with connection cleanup."""
        try:
            async for event in _sse_stream(request, postgres):
                yield event
        except Exception as e:
            logger.error("Error during RAG query streaming: %s", e)
            error_msg = "An error occurred while generating the response."
            yield f"event: error\ndata: {json.dumps({'message': error_msg})}\n\n"
            yield "event: done\ndata: {}\n\n"
        finally:
            await postgres.close()

    return StreamingResponse(
        stream_with_cleanup(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
