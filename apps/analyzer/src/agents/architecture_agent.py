"""Architecture_Agent — pattern detection and layer analysis via Claude Sonnet.

Execution order: 2. Requires project_model from Repository_Agent.
Produces: architecture_report with detected patterns, layers, and violations.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from src.adapters.bedrock_adapter import BedrockAdapter, BedrockInvocationError
from src.agents.base import AgentOutput, BaseAgent, PipelineContext, AgentExecutionError
from src.domain.models.agent_result import AgentStatus
from src.domain.models.project_model import NodeType, EdgeType

logger = logging.getLogger(__name__)

MAX_INPUT_CHARS = 3000


def _truncate(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """Truncate text to max_chars, appending ellipsis if trimmed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


class ArchitectureAgent(BaseAgent):
    """Analyzes project structure to detect architectural patterns, layers, and violations."""

    def __init__(self, bedrock: Optional[BedrockAdapter] = None) -> None:
        self._bedrock = bedrock or BedrockAdapter()

    @property
    def name(self) -> str:
        return "architecture_agent"

    @property
    def execution_order(self) -> int:
        return 2

    def can_execute(self, context: PipelineContext) -> bool:
        return context.project_model is not None

    async def execute(self, context: PipelineContext) -> AgentOutput:
        """Summarize modules/deps and ask Claude for patterns, layers, violations."""
        project = context.project_model
        assert project is not None

        try:
            summary = self._build_project_summary(context)
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(summary)

            raw_response = await self._bedrock.invoke_claude(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=4096,
            )

            report = self._parse_response(raw_response)

            return AgentOutput(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                data=report,
                context_updates={"architecture_report": report},
            )

        except BedrockInvocationError as exc:
            logger.error("Architecture agent failed: %s", exc.message)
            raise AgentExecutionError(self.name, exc.message) from exc
        except Exception as exc:
            logger.error("Architecture agent unexpected error: %s", str(exc))
            raise AgentExecutionError(self.name, str(exc)) from exc

    def _build_project_summary(self, context: PipelineContext) -> str:
        """Build a concise text summary of the project structure for Claude."""
        project = context.project_model
        assert project is not None

        lines: list[str] = []
        lines.append(f"Project: {project.name}")
        lines.append(f"Language: {project.language or 'unknown'}")
        lines.append(f"Framework: {project.framework or 'unknown'}")
        lines.append(f"Total files: {project.total_files}")
        lines.append(f"Total LOC: {project.total_loc}")
        lines.append("")

        # Modules/packages
        modules = [n for n in project.nodes if n.node_type in (NodeType.MODULE, NodeType.PACKAGE)]
        if modules:
            lines.append("## Modules/Packages:")
            for mod in modules[:30]:
                lines.append(f"  - {mod.name} (LOC: {mod.loc}, complexity: {mod.complexity})")
            if len(modules) > 30:
                lines.append(f"  ... and {len(modules) - 30} more modules")
            lines.append("")

        # Classes
        classes = [n for n in project.nodes if n.node_type == NodeType.CLASS]
        if classes:
            lines.append("## Classes:")
            for cls in classes[:40]:
                path_info = f" [{cls.file_path}]" if cls.file_path else ""
                lines.append(f"  - {cls.name}{path_info} (LOC: {cls.loc})")
            if len(classes) > 40:
                lines.append(f"  ... and {len(classes) - 40} more classes")
            lines.append("")

        # Dependencies summary
        edge_counts: dict[str, int] = {}
        for edge in project.edges:
            edge_counts[edge.edge_type.value] = edge_counts.get(edge.edge_type.value, 0) + 1
        if edge_counts:
            lines.append("## Dependency summary:")
            for etype, count in edge_counts.items():
                lines.append(f"  - {etype}: {count} edges")
            lines.append("")

        # Sample imports (first 20)
        import_edges = [e for e in project.edges if e.edge_type == EdgeType.IMPORT][:20]
        if import_edges:
            lines.append("## Sample import relationships:")
            node_map = {n.id: n.name for n in project.nodes}
            for edge in import_edges:
                src = node_map.get(edge.source_node_id, "?")
                tgt = node_map.get(edge.target_node_id, "?")
                lines.append(f"  {src} -> {tgt}")

        return _truncate("\n".join(lines))

    def _build_system_prompt(self) -> str:
        return (
            "You are a senior software architect specializing in code analysis. "
            "Analyze the project structure and produce a JSON report with the following keys:\n"
            '- "patterns": list of architectural patterns detected (e.g., MVC, Hexagonal, Layered, Microservices)\n'
            '- "layers": list of objects {name, responsibility, modules} for each architectural layer\n'
            '- "violations": list of objects {description, severity, affected_modules} for architecture violations\n'
            '- "summary": a brief 2-3 sentence summary of the overall architecture\n'
            '- "recommendations": list of improvement suggestions\n\n'
            "Return ONLY valid JSON. No markdown fences, no explanation text outside the JSON."
        )

    def _build_user_prompt(self, summary: str) -> str:
        return (
            "Analyze the following project structure and dependencies. "
            "Identify architectural patterns, layers, and any violations or anti-patterns:\n\n"
            f"{summary}"
        )

    def _parse_response(self, raw: str) -> dict:
        """Parse Claude's JSON response, with fallback for malformed output."""
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last lines (fences)
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            report = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Architecture agent: Failed to parse JSON, using raw text as summary")
            report = {
                "patterns": [],
                "layers": [],
                "violations": [],
                "summary": cleaned[:500],
                "recommendations": [],
            }

        # Ensure expected keys exist
        report.setdefault("patterns", [])
        report.setdefault("layers", [])
        report.setdefault("violations", [])
        report.setdefault("summary", "")
        report.setdefault("recommendations", [])

        return report
