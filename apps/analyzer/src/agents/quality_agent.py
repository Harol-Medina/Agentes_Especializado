"""Quality_Agent — code metrics and smell detection via Claude Sonnet.

Execution order: 3. Requires project_model from Repository_Agent.
Produces: quality_report with metrics, code smells, and improvement suggestions.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from src.adapters.bedrock_adapter import BedrockAdapter, BedrockInvocationError
from src.agents.base import AgentOutput, BaseAgent, PipelineContext, AgentExecutionError
from src.domain.models.agent_result import AgentStatus
from src.domain.models.project_model import NodeType

logger = logging.getLogger(__name__)

MAX_INPUT_CHARS = 3000


def _truncate(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """Truncate text to max_chars, appending ellipsis if trimmed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


class QualityAgent(BaseAgent):
    """Computes code quality metrics and detects code smells via Claude analysis."""

    def __init__(self, bedrock: Optional[BedrockAdapter] = None) -> None:
        self._bedrock = bedrock or BedrockAdapter()

    @property
    def name(self) -> str:
        return "quality_agent"

    @property
    def execution_order(self) -> int:
        return 3

    def can_execute(self, context: PipelineContext) -> bool:
        return context.project_model is not None

    async def execute(self, context: PipelineContext) -> AgentOutput:
        """Compute metrics and ask Claude for code smell analysis."""
        project = context.project_model
        assert project is not None

        try:
            metrics = self._compute_metrics(context)
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(metrics)

            raw_response = await self._bedrock.invoke_claude(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=4096,
            )

            report = self._parse_response(raw_response, metrics)

            return AgentOutput(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                data=report,
                context_updates={"quality_report": report},
            )

        except BedrockInvocationError as exc:
            logger.error("Quality agent failed: %s", exc.message)
            raise AgentExecutionError(self.name, exc.message) from exc
        except Exception as exc:
            logger.error("Quality agent unexpected error: %s", str(exc))
            raise AgentExecutionError(self.name, str(exc)) from exc

    def _compute_metrics(self, context: PipelineContext) -> dict:
        """Compute raw quality metrics from the project model."""
        project = context.project_model
        assert project is not None

        # Complexity metrics
        functions = [n for n in project.nodes if n.node_type == NodeType.FUNCTION]
        complexities = [n.complexity for n in functions] if functions else [0]
        avg_complexity = sum(complexities) / len(complexities) if complexities else 0
        max_complexity = max(complexities) if complexities else 0
        high_complexity_funcs = [n for n in functions if n.complexity > 10]

        # File size metrics
        files = [n for n in project.nodes if n.node_type == NodeType.FILE]
        file_locs = [n.loc for n in files] if files else [0]
        avg_file_loc = sum(file_locs) / len(file_locs) if file_locs else 0
        large_files = [n for n in files if n.loc > 500]

        # Coupling metrics (afferent/efferent)
        node_ids = {n.id for n in project.nodes}
        incoming: dict[str, int] = {}
        outgoing: dict[str, int] = {}
        for edge in project.edges:
            src_name = next((n.name for n in project.nodes if n.id == edge.source_node_id), None)
            tgt_name = next((n.name for n in project.nodes if n.id == edge.target_node_id), None)
            if src_name:
                outgoing[src_name] = outgoing.get(src_name, 0) + 1
            if tgt_name:
                incoming[tgt_name] = incoming.get(tgt_name, 0) + 1

        # Top coupled modules
        top_coupled = sorted(
            incoming.items(), key=lambda x: x[1], reverse=True
        )[:10]

        return {
            "total_files": len(files),
            "total_functions": len(functions),
            "total_loc": project.total_loc,
            "avg_complexity": round(avg_complexity, 2),
            "max_complexity": max_complexity,
            "high_complexity_count": len(high_complexity_funcs),
            "avg_file_loc": round(avg_file_loc, 1),
            "large_file_count": len(large_files),
            "top_coupled_modules": top_coupled,
            "high_complexity_functions": [
                {"name": f.name, "complexity": f.complexity, "file": f.file_path}
                for f in high_complexity_funcs[:10]
            ],
            "large_files": [
                {"name": f.name, "loc": f.loc, "file": f.file_path}
                for f in large_files[:10]
            ],
        }

    def _build_system_prompt(self) -> str:
        return (
            "You are a senior code quality analyst. Based on the metrics and file data provided, "
            "produce a JSON report with the following keys:\n"
            '- "code_smells": list of objects {name, description, severity, affected_files} for detected smells\n'
            '- "maintainability_score": integer 1-100 (100 = excellent)\n'
            '- "tech_debt_indicators": list of strings describing technical debt signals\n'
            '- "hotspots": list of objects {file, reason} for files needing immediate attention\n'
            '- "recommendations": list of actionable improvement suggestions\n'
            '- "summary": a brief 2-3 sentence quality assessment\n\n'
            "Return ONLY valid JSON. No markdown fences, no explanation text outside the JSON."
        )

    def _build_user_prompt(self, metrics: dict) -> str:
        lines: list[str] = []
        lines.append("Analyze the following code quality metrics and identify code smells:\n")
        lines.append(f"Total files: {metrics['total_files']}")
        lines.append(f"Total functions: {metrics['total_functions']}")
        lines.append(f"Total LOC: {metrics['total_loc']}")
        lines.append(f"Average cyclomatic complexity: {metrics['avg_complexity']}")
        lines.append(f"Max complexity: {metrics['max_complexity']}")
        lines.append(f"Functions with complexity > 10: {metrics['high_complexity_count']}")
        lines.append(f"Average file LOC: {metrics['avg_file_loc']}")
        lines.append(f"Files with > 500 LOC: {metrics['large_file_count']}")
        lines.append("")

        if metrics["high_complexity_functions"]:
            lines.append("## High complexity functions:")
            for f in metrics["high_complexity_functions"]:
                lines.append(f"  - {f['name']} (complexity: {f['complexity']}, file: {f['file']})")
            lines.append("")

        if metrics["large_files"]:
            lines.append("## Large files:")
            for f in metrics["large_files"]:
                lines.append(f"  - {f['name']} ({f['loc']} LOC, path: {f['file']})")
            lines.append("")

        if metrics["top_coupled_modules"]:
            lines.append("## Most coupled modules (by incoming dependencies):")
            for name, count in metrics["top_coupled_modules"]:
                lines.append(f"  - {name}: {count} incoming")

        return _truncate("\n".join(lines))

    def _parse_response(self, raw: str, computed_metrics: dict) -> dict:
        """Parse Claude's JSON response and merge with computed metrics."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            analysis = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Quality agent: Failed to parse JSON, using raw text as summary")
            analysis = {
                "code_smells": [],
                "maintainability_score": 50,
                "tech_debt_indicators": [],
                "hotspots": [],
                "recommendations": [],
                "summary": cleaned[:500],
            }

        # Ensure expected keys
        analysis.setdefault("code_smells", [])
        analysis.setdefault("maintainability_score", 50)
        analysis.setdefault("tech_debt_indicators", [])
        analysis.setdefault("hotspots", [])
        analysis.setdefault("recommendations", [])
        analysis.setdefault("summary", "")

        # Merge computed metrics into the report
        report = {
            "metrics": computed_metrics,
            "analysis": analysis,
        }

        return report
