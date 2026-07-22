"""Repository Agent — first agent in the pipeline (execution_order=1).

Responsible for:
1. Cloning the target repository via GitAdapter (shallow, depth=1).
2. Detecting language and framework via LanguageDetector.
3. Parsing source files via TreeSitterParser.
4. Building the ProjectModel graph via GraphBuilder.
5. Returning context updates: repo_path and project_model.

This is the CRITICAL agent: if it fails, the entire pipeline terminates.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.adapters.git_adapter import GitAdapter
from src.agents.base import (
    AgentExecutionError,
    AgentOutput,
    BaseAgent,
    PipelineContext,
)
from src.domain.models.agent_result import AgentStatus
from src.graph.builder import GraphBuilder
from src.graph.models import ParsedFile
from src.parsing.language_detector import LanguageDetector
from src.parsing.tree_sitter_parser import TreeSitterParser

logger = logging.getLogger(__name__)

# Source file extensions we attempt to parse
PARSEABLE_EXTENSIONS: set[str] = {
    ".java",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
}


class RepositoryAgent(BaseAgent):
    """Clones, detects, parses, and builds the project graph.

    Always runs first (execution_order=1) and always can execute.
    Its failure terminates the pipeline.
    """

    @property
    def name(self) -> str:
        return "repository_agent"

    @property
    def execution_order(self) -> int:
        return 1

    def can_execute(self, context: PipelineContext) -> bool:
        """Repository agent always executes — it is the first in the chain."""
        return True

    async def execute(self, context: PipelineContext) -> AgentOutput:
        """Execute the repository analysis pipeline.

        Steps:
            1. Clone the repository.
            2. Detect language and framework.
            3. Parse source files with tree-sitter.
            4. Build the ProjectModel graph.

        Returns:
            AgentOutput with context_updates containing repo_path and project_model.

        Raises:
            AgentExecutionError: If cloning or critical parsing fails.
        """
        job_id = str(context.job_id)
        repo_url = context.repo_url

        logger.info(
            "RepositoryAgent starting — job_id=%s, repo_url=%s", job_id, repo_url
        )

        # --- Step 1: Clone ---
        git_adapter = GitAdapter()
        repo_path = git_adapter.clone(repo_url, job_id)

        logger.info("Repository cloned at %s", repo_path)

        try:
            # --- Step 2: Detect language and framework ---
            detector = LanguageDetector()
            language, framework = detector.detect(repo_path)

            logger.info(
                "Language detection — language=%s, framework=%s", language, framework
            )

            # --- Step 3: Parse source files ---
            parser = TreeSitterParser()
            source_files = git_adapter.list_source_files(repo_path)
            parsed_files = self._parse_source_files(parser, source_files, repo_path)

            logger.info(
                "Parsing complete — total_source_files=%d, parsed=%d",
                len(source_files),
                len(parsed_files),
            )

            if not parsed_files and language == "unknown":
                raise AgentExecutionError(
                    agent_name=self.name,
                    message=(
                        f"No parseable source files found in repository '{repo_url}'. "
                        "Supported languages: Java, TypeScript, JavaScript."
                    ),
                )

            # --- Step 4: Build ProjectModel graph ---
            builder = GraphBuilder()
            project_model = builder.build(
                parsed_files=parsed_files,
                language=language,
                framework=framework,
                repo_url=repo_url,
                repo_path=str(repo_path),
            )

            logger.info(
                "Graph built — nodes=%d, edges=%d, total_loc=%d",
                len(project_model.nodes),
                len(project_model.edges),
                project_model.total_loc,
            )

            return AgentOutput(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                data={
                    "language": language,
                    "framework": framework,
                    "total_files": project_model.total_files,
                    "total_loc": project_model.total_loc,
                    "total_nodes": len(project_model.nodes),
                    "total_edges": len(project_model.edges),
                },
                context_updates={
                    "repo_path": str(repo_path),
                    "project_model": project_model,
                },
            )

        except AgentExecutionError:
            # Re-raise agent errors (already formatted)
            raise
        except Exception as exc:
            raise AgentExecutionError(
                agent_name=self.name,
                message=f"Unexpected error during repository analysis: {exc}",
            ) from exc

    def _parse_source_files(
        self,
        parser: TreeSitterParser,
        source_files: list[Path],
        repo_path: Path,
    ) -> list[ParsedFile]:
        """Parse all source files that have parseable extensions.

        Files that fail to parse are logged and skipped (non-fatal).
        """
        parsed: list[ParsedFile] = []
        skipped = 0

        for file_path in source_files:
            if file_path.suffix.lower() not in PARSEABLE_EXTENSIONS:
                continue

            result = parser.parse_file(file_path)
            if result is not None:
                parsed.append(result)
            else:
                skipped += 1

        if skipped > 0:
            logger.warning(
                "Skipped %d files that could not be parsed (parse errors or read issues)",
                skipped,
            )

        return parsed
