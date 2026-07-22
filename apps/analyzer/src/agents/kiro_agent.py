"""Kiro_Agent — generates a Kiro-compatible spec document from analysis results.

Execution order: 7. Requires project_model + architecture_report + modernization_plan.
Produces: kiro_spec as a structured markdown string following Kiro spec format.

Degradation levels (from design doc):
- Full: modernization_plan + architecture_report → complete spec
- Partial: only architecture_report → spec without proposed architecture, generic tasks
- Minimal: only project_model → module listing, no concrete tasks
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

MAX_INPUT_CHARS = 5000


def _truncate(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """Truncate text to max_chars, appending ellipsis if trimmed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


class KiroAgent(BaseAgent):
    """Generates a Kiro-compatible spec document from the accumulated pipeline analysis."""

    def __init__(self, bedrock: Optional[BedrockAdapter] = None) -> None:
        self._bedrock = bedrock or BedrockAdapter()

    @property
    def name(self) -> str:
        return "kiro_agent"

    @property
    def execution_order(self) -> int:
        return 7

    def can_execute(self, context: PipelineContext) -> bool:
        # Kiro agent needs at least project_model to produce anything
        return context.project_model is not None

    async def execute(self, context: PipelineContext) -> AgentOutput:
        """Generate a Kiro spec from accumulated analysis context."""
        assert context.project_model is not None

        try:
            summary = self._build_context_summary(context)
            degradation_level = self._determine_level(context)
            system_prompt = self._build_system_prompt(degradation_level)
            user_prompt = self._build_user_prompt(summary, degradation_level)

            raw_response = await self._bedrock.invoke_claude(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=4096,
            )

            kiro_spec = self._clean_markdown(raw_response)
            is_partial = degradation_level != "full"

            return AgentOutput(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                data={"kiro_spec": kiro_spec, "is_partial": is_partial, "level": degradation_level},
                context_updates={"kiro_spec": kiro_spec},
            )

        except BedrockInvocationError as exc:
            logger.error("Kiro agent failed: %s", exc.message)
            raise AgentExecutionError(self.name, exc.message) from exc
        except Exception as exc:
            logger.error("Kiro agent unexpected error: %s", str(exc))
            raise AgentExecutionError(self.name, str(exc)) from exc

    def _determine_level(self, context: PipelineContext) -> str:
        """Determine spec degradation level based on available context."""
        if context.modernization_plan and context.architecture_report:
            return "full"
        if context.architecture_report:
            return "partial"
        return "minimal"

    def _build_context_summary(self, context: PipelineContext) -> str:
        """Consolidate available analysis data for Claude."""
        project = context.project_model
        assert project is not None

        lines: list[str] = []

        # Project basics
        lines.append(f"Project: {project.name}")
        lines.append(f"Language: {project.language or 'unknown'}")
        lines.append(f"Framework: {project.framework or 'unknown'}")
        lines.append(f"Total files: {project.total_files}")
        lines.append(f"Total LOC: {project.total_loc}")
        lines.append("")

        # Architecture report
        arch = context.architecture_report
        if arch:
            lines.append("## Architecture:")
            if arch.get("patterns"):
                lines.append(f"  Patterns: {', '.join(arch['patterns'][:5])}")
            if arch.get("layers"):
                lines.append("  Layers:")
                for layer in arch["layers"][:8]:
                    if isinstance(layer, dict):
                        lines.append(f"    - {layer.get('name', '?')}: {layer.get('responsibility', '')[:60]}")
                    else:
                        lines.append(f"    - {str(layer)[:80]}")
            if arch.get("summary"):
                lines.append(f"  Summary: {str(arch['summary'])[:300]}")
            if arch.get("violations"):
                lines.append(f"  Violations: {len(arch['violations'])}")
            if arch.get("recommendations"):
                lines.append("  Recommendations:")
                for rec in arch["recommendations"][:5]:
                    lines.append(f"    - {str(rec)[:100]}")
            lines.append("")

        # Modernization plan
        mod_plan = context.modernization_plan
        if mod_plan:
            lines.append("## Modernization Plan:")
            if mod_plan.get("summary"):
                lines.append(f"  Strategy: {str(mod_plan['summary'])[:300]}")
            if mod_plan.get("migration_steps"):
                lines.append("  Migration steps:")
                for step in mod_plan["migration_steps"][:8]:
                    if isinstance(step, dict):
                        title = step.get("title", "?")
                        effort = step.get("estimated_effort", "?")
                        lines.append(f"    - {title} (effort: {effort})")
                    else:
                        lines.append(f"    - {str(step)[:80]}")
            if mod_plan.get("quick_wins"):
                lines.append("  Quick wins:")
                for qw in mod_plan["quick_wins"][:5]:
                    if isinstance(qw, dict):
                        lines.append(f"    - {qw.get('action', str(qw))[:80]}")
                    else:
                        lines.append(f"    - {str(qw)[:80]}")
            if mod_plan.get("risk_assessment"):
                risk = mod_plan["risk_assessment"]
                if isinstance(risk, dict):
                    lines.append(f"  Overall risk: {risk.get('overall_risk', 'unknown')}")
            lines.append("")

        # Module structure (always available since project_model is required)
        modules = [n for n in project.nodes if n.node_type in (NodeType.MODULE, NodeType.PACKAGE)]
        if modules:
            lines.append("## Modules:")
            for mod in modules[:15]:
                lines.append(f"  - {mod.name} (LOC: {mod.loc})")
            if len(modules) > 15:
                lines.append(f"  ... and {len(modules) - 15} more")

        return _truncate("\n".join(lines))

    def _build_system_prompt(self, level: str) -> str:
        base = (
            "You are a technical writer generating a Kiro-compatible specification document. "
            "The output MUST be valid Markdown with exactly three top-level sections: "
            "# Requirements, # Design, and # Tasks.\n\n"
            "Format rules:\n"
            "- Requirements section: numbered list (REQ-1, REQ-2, etc.) of derived requirements\n"
            "- Design section: describe current architecture and (if available) proposed architecture\n"
            "- Tasks section: checkbox list (- [ ] TASK-1: description) of implementation tasks\n\n"
            "Return ONLY the markdown document. No JSON, no code fences wrapping the whole output."
        )

        if level == "full":
            base += (
                "\n\nYou have full context (architecture + modernization plan). "
                "Generate a complete spec with:\n"
                "- Requirements derived from modernization recommendations\n"
                "- Design section with both Current Architecture and Proposed Architecture subsections\n"
                "- Tasks derived from migration steps in priority order with effort estimates"
            )
        elif level == "partial":
            base += (
                "\n\nYou have architecture data but NO modernization plan. "
                "Generate a partial spec:\n"
                "- Requirements based on architecture violations and quality issues\n"
                "- Design section with Current Architecture only (no Proposed section)\n"
                "- Tasks as generic improvement items based on detected issues"
            )
        else:
            base += (
                "\n\nYou have ONLY basic project structure (minimal data). "
                "Generate a minimal spec:\n"
                "- Requirements: list module organization requirements\n"
                "- Design section: list detected modules and files only\n"
                "- Tasks: no concrete tasks (add placeholder noting insufficient analysis data)"
            )

        return base

    def _build_user_prompt(self, summary: str, level: str) -> str:
        level_label = {"full": "complete", "partial": "partial", "minimal": "minimal"}
        return (
            f"Generate a {level_label.get(level, 'complete')} Kiro specification document "
            f"based on the following analysis data:\n\n{summary}"
        )

    def _clean_markdown(self, raw: str) -> str:
        """Clean up Claude's response to ensure it's pure markdown."""
        cleaned = raw.strip()

        # Remove wrapping code fences if Claude added them
        if cleaned.startswith("```markdown"):
            cleaned = cleaned[len("```markdown"):].strip()
        elif cleaned.startswith("```md"):
            cleaned = cleaned[len("```md"):].strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:].strip()

        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        # Ensure it starts with a heading
        if not cleaned.startswith("#"):
            # Prepend default heading if missing
            cleaned = "# Requirements\n\n" + cleaned

        return cleaned
