"""POST /query — RAG chat endpoint with Server-Sent Events streaming.

Accepts a natural language question about an analysed project and streams
the generated answer back as SSE events. Uses pgvector cosine similarity
for retrieval and Claude Sonnet for response generation.

Security layers (in order):
1. Rate limiting (20 req/min per IP)
2. Input validation (max length, character sanitization)
3. Prompt injection detection (local regex patterns)
4. Bedrock Guardrail (AWS-side content filtering + PII blocking)
5. Output validation via Guardrail before streaming to user
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, StreamingResponse

from src.adapters.bedrock_adapter import BedrockAdapter
from src.adapters.postgres_adapter import PostgresAdapter
from src.api.schemas import QueryRequest
from src.rag.embeddings import TitanEmbeddingsClient
from src.rag.generator import RAGGenerator
from src.rag.retriever import RAGRetriever
from src.security.audit_log import SecurityEvent, log_security_event
from src.security.bedrock_guardrail import BedrockGuardrail
from src.security.prompt_guard import PromptGuard, ThreatLevel
from src.security.rate_limiter import query_rate_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])

# Security components (initialized once)
_prompt_guard = PromptGuard(max_prompt_length=5000, block_on_level=ThreatLevel.HIGH)
_bedrock_guardrail = BedrockGuardrail()


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request, considering X-Forwarded-For from nginx."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _sse_stream(
    request: QueryRequest,
    postgres: PostgresAdapter,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for a RAG query.

    Flow:
    1. Retrieve relevant chunks via RAGRetriever.
    2. If no chunks pass threshold, yield 'no_context' event.
    3. Generate response via RAGGenerator.
    4. Validate output via Bedrock Guardrail.
    5. Yield SSE events with response tokens.
    6. Yield 'done' event at end.
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
    project_name = str(request.project_id)

    full_response = ""
    async for token in generator.generate_stream(
        question=request.question,
        chunks=chunks,
        project_name=project_name,
    ):
        full_response += token

    # 4. Validate output via Bedrock Guardrail
    output_result = await _bedrock_guardrail.validate_output(full_response)

    if output_result.blocked:
        log_security_event(
            SecurityEvent.GUARDRAIL_BLOCKED_OUTPUT,
            prompt_preview=request.question,
            guardrail_reason=output_result.reason,
        )
        safe_msg = (
            "The generated response was filtered by our safety system. "
            "Please rephrase your question to focus on code structure, "
            "architecture, or technical aspects of the project."
        )
        yield f"event: token\ndata: {json.dumps({'content': safe_msg})}\n\n"
    else:
        # Stream the validated response
        yield f"event: token\ndata: {json.dumps({'content': output_result.output_text})}\n\n"

    # 5. Done event
    yield "event: done\ndata: {}\n\n"


@router.post(
    "",
    summary="RAG query with SSE streaming (security-filtered)",
    response_class=StreamingResponse,
    response_model=None,
    status_code=status.HTTP_200_OK,
)
async def rag_query(request: QueryRequest, http_request: Request) -> StreamingResponse | JSONResponse:
    """Stream a RAG-generated answer for the given question.

    POST /query — accepts {project_id, question, max_chunks}.
    Returns SSE stream with events: context, token, no_context, done.

    Security pipeline:
    1. Rate limiting by client IP
    2. Local prompt injection detection (PromptGuard)
    3. Bedrock Guardrail validation (content + PII + topics)
    4. Output validation before streaming to user
    """
    client_ip = _get_client_ip(http_request)

    # ─── Layer 1: Rate limiting ──────────────────────────────────────────────
    rate_result = query_rate_limiter.check(client_ip)
    if not rate_result.allowed:
        log_security_event(
            SecurityEvent.RATE_LIMITED,
            client_ip=client_ip,
            prompt_preview=request.question,
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "RATE_LIMITED",
                "message": "Too many requests. Please wait before trying again.",
                "retry_after_seconds": int(rate_result.reset_in_seconds),
            },
            headers={"Retry-After": str(int(rate_result.reset_in_seconds))},
        )

    # ─── Layer 2: Local prompt injection detection ───────────────────────────
    assessment = _prompt_guard.analyze(request.question)

    if assessment.blocked:
        log_security_event(
            SecurityEvent.PROMPT_BLOCKED,
            client_ip=client_ip,
            prompt_preview=request.question,
            matched_patterns=assessment.matched_patterns,
            threat_level=assessment.level.value,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "CONTENT_BLOCKED",
                "message": (
                    "Your request was blocked by our safety filters. "
                    "This tool is designed for code analysis questions only."
                ),
            },
        )

    if assessment.level != ThreatLevel.NONE:
        log_security_event(
            SecurityEvent.PROMPT_SUSPICIOUS,
            client_ip=client_ip,
            prompt_preview=request.question,
            matched_patterns=assessment.matched_patterns,
            threat_level=assessment.level.value,
        )

    # Use sanitized input for downstream processing
    sanitized_question = assessment.sanitized_input or request.question

    # ─── Layer 3: Bedrock Guardrail (AWS-side validation) ────────────────────
    guardrail_result = await _bedrock_guardrail.validate_input(sanitized_question)

    if guardrail_result.blocked:
        log_security_event(
            SecurityEvent.GUARDRAIL_BLOCKED_INPUT,
            client_ip=client_ip,
            prompt_preview=request.question,
            guardrail_reason=guardrail_result.reason,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "CONTENT_BLOCKED",
                "message": (
                    "Your request was blocked because it violates our content policy. "
                    "This tool is designed exclusively for code analysis questions."
                ),
            },
        )

    # ─── Layer 4: Process the validated request ──────────────────────────────
    # Override the question with sanitized version
    request.question = sanitized_question

    # Create a PostgresAdapter for this request
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
            "X-RateLimit-Remaining": str(rate_result.remaining),
        },
    )
