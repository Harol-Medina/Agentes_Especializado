"""RAG response generator — generates answers using retrieved context + Claude Sonnet.

Takes retrieved code chunks and a user question, builds a contextual prompt,
and invokes Claude via BedrockAdapter to produce a natural language answer.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from src.adapters.bedrock_adapter import BedrockAdapter
from src.rag.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_TEMPLATE = (
    "You are a knowledgeable code assistant for the project '{project_name}'. "
    "Answer the user's question based ONLY on the provided code context below. "
    "If the context does not contain enough information to answer, say so clearly. "
    "Reference specific files and functions when possible. "
    "Be concise and technical."
)

_CONTEXT_HEADER = "=== Code Context ===\n\n"
_CHUNK_TEMPLATE = (
    "--- [{chunk_type}] {file_path}"
    "{function_info} (similarity: {similarity:.2f}) ---\n"
    "{chunk_text}\n\n"
)


class RAGGenerator:
    """Generates answers using retrieved context + Claude Sonnet.

    Builds a system prompt with project context, formats retrieved chunks
    as user context, and invokes Claude to produce the answer.
    """

    def __init__(self, bedrock: BedrockAdapter) -> None:
        """Initialize with a BedrockAdapter instance.

        Args:
            bedrock: BedrockAdapter configured for Claude Sonnet invocation.
        """
        self._bedrock = bedrock

    async def generate(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        project_name: str,
    ) -> str:
        """Generate a response using retrieved context and Claude.

        1. Build system prompt with project name.
        2. Build user prompt with question + formatted chunks.
        3. Call Claude via BedrockAdapter.
        4. Return the response text.

        Args:
            question: The user's natural language question.
            chunks: Retrieved code chunks with relevance scores.
            project_name: Name of the project for context.

        Returns:
            Generated response text from Claude.
        """
        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(project_name=project_name)
        user_prompt = self._build_user_prompt(question, chunks)

        logger.info(
            "Generating RAG response for project '%s' with %d chunks",
            project_name,
            len(chunks),
        )

        response = await self._bedrock.invoke_claude(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2048,
        )

        return response

    async def generate_stream(
        self,
        question: str,
        chunks: list[RetrievedChunk],
        project_name: str,
    ) -> AsyncGenerator[str, None]:
        """SSE-friendly streaming version of generate.

        For MVP, yields the full response in one chunk. Streaming Bedrock
        integration is planned for a future task.

        Args:
            question: The user's natural language question.
            chunks: Retrieved code chunks with relevance scores.
            project_name: Name of the project for context.

        Yields:
            Response text (full response in one yield for MVP).
        """
        response = await self.generate(question, chunks, project_name)
        yield response

    def _build_user_prompt(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> str:
        """Build the user prompt with context chunks and question.

        Args:
            question: The user's question.
            chunks: Retrieved code chunks.

        Returns:
            Formatted user prompt string.
        """
        parts: list[str] = [_CONTEXT_HEADER]

        for chunk in chunks:
            function_info = ""
            if chunk.function_name:
                function_info = f" :: {chunk.function_name}"
            elif chunk.module_name:
                function_info = f" :: {chunk.module_name}"

            parts.append(
                _CHUNK_TEMPLATE.format(
                    chunk_type=chunk.chunk_type,
                    file_path=chunk.file_path,
                    function_info=function_info,
                    similarity=chunk.similarity,
                    chunk_text=chunk.chunk_text,
                )
            )

        parts.append(f"=== Question ===\n\n{question}")

        return "".join(parts)
