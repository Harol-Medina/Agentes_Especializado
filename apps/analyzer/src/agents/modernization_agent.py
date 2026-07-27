"""Modernization_Agent — tech debt analysis and migration planning via Claude Sonnet.

Execution order: 6. Requires project_model + architecture_report + quality_report + security_report.
Produces: modernization_plan with migration steps, priority order, effort estimates, risk assessment.
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

MAX_INPUT_CHARS = 4000


def _truncate(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """Truncate text to max_chars, appending ellipsis if trimmed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


class ModernizationAgent(BaseAgent):
    """Analyzes tech debt, outdated patterns, and generates a prioritized modernization plan."""

    def __init__(self, bedrock: Optional[BedrockAdapter] = None) -> None:
        self._bedrock = bedrock or BedrockAdapter()

    @property
    def name(self) -> str:
        return "modernization_agent"

    @property
    def execution_order(self) -> int:
        return 6

    def can_execute(self, context: PipelineContext) -> bool:
        return (
            context.project_model is not None
            and context.architecture_report is not None
        )

    async def execute(self, context: PipelineContext) -> AgentOutput:
        """Build context from prior agents and ask Claude for a modernization plan."""
        assert context.project_model is not None
        assert context.architecture_report is not None

        try:
            summary = self._build_context_summary(context)
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(summary)

            raw_response = await self._bedrock.invoke_claude(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=4096,
            )

            plan = self._parse_response(raw_response)

            return AgentOutput(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                data=plan,
                context_updates={"modernization_plan": plan},
            )

        except BedrockInvocationError as exc:
            logger.error("Modernization agent failed: %s", exc.message)
            raise AgentExecutionError(self.name, exc.message) from exc
        except Exception as exc:
            logger.error("Modernization agent unexpected error: %s", str(exc))
            raise AgentExecutionError(self.name, str(exc)) from exc

    def _build_context_summary(self, context: PipelineContext) -> str:
        """Consolidate data from prior agents into a concise summary for Claude."""
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

        # Architecture report summary
        arch = context.architecture_report
        if arch:
            lines.append("## Architecture Analysis:")
            if arch.get("patterns"):
                lines.append(f"  Patterns detected: {', '.join(arch['patterns'][:5])}")
            if arch.get("summary"):
                lines.append(f"  Summary: {str(arch['summary'])[:300]}")
            if arch.get("violations"):
                lines.append(f"  Violations found: {len(arch['violations'])}")
                for v in arch["violations"][:5]:
                    desc = v.get("description", str(v)) if isinstance(v, dict) else str(v)
                    lines.append(f"    - {desc[:100]}")
            if arch.get("recommendations"):
                lines.append("  Recommendations:")
                for rec in arch["recommendations"][:5]:
                    lines.append(f"    - {str(rec)[:100]}")
            lines.append("")

        # Quality report summary
        quality = context.quality_report
        if quality:
            lines.append("## Quality Metrics:")
            metrics = quality.get("metrics", {})
            analysis = quality.get("analysis", {})
            if metrics:
                lines.append(f"  Avg complexity: {metrics.get('avg_complexity', 'N/A')}")
                lines.append(f"  Max complexity: {metrics.get('max_complexity', 'N/A')}")
                lines.append(f"  High complexity functions: {metrics.get('high_complexity_count', 0)}")
                lines.append(f"  Large files (>500 LOC): {metrics.get('large_file_count', 0)}")
            if analysis.get("maintainability_score"):
                lines.append(f"  Maintainability score: {analysis['maintainability_score']}/100")
            if analysis.get("tech_debt_indicators"):
                lines.append("  Tech debt indicators:")
                for indicator in analysis["tech_debt_indicators"][:5]:
                    lines.append(f"    - {str(indicator)[:100]}")
            if analysis.get("code_smells"):
                lines.append(f"  Code smells detected: {len(analysis['code_smells'])}")
                for smell in analysis["code_smells"][:5]:
                    name = smell.get("name", str(smell)) if isinstance(smell, dict) else str(smell)
                    lines.append(f"    - {name[:80]}")
            lines.append("")

        # Security report summary
        security = context.security_report
        if security:
            lines.append("## Security Findings:")
            vulns = security.get("vulnerabilities", [])
            if vulns:
                lines.append(f"  Total vulnerabilities: {len(vulns)}")
                for v in vulns[:5]:
                    desc = v.get("description", str(v)) if isinstance(v, dict) else str(v)
                    sev = v.get("severity", "unknown") if isinstance(v, dict) else ""
                    lines.append(f"    - [{sev}] {str(desc)[:80]}")
            if security.get("recommendations"):
                lines.append("  Security recommendations:")
                for rec in security["recommendations"][:3]:
                    lines.append(f"    - {str(rec)[:100]}")
            lines.append("")

        # Module structure
        modules = [n for n in project.nodes if n.node_type in (NodeType.MODULE, NodeType.PACKAGE)]
        if modules:
            lines.append("## Module Structure:")
            for mod in modules[:20]:
                lines.append(f"  - {mod.name} (LOC: {mod.loc}, complexity: {mod.complexity})")
            if len(modules) > 20:
                lines.append(f"  ... and {len(modules) - 20} more modules")

        return _truncate("\n".join(lines))

    def _build_system_prompt(self) -> str:
        return (
            "You are a senior software modernization consultant specializing in legacy code migration "
            "and technical debt reduction. Based on the project analysis provided, produce a JSON "
            "modernization plan with the following keys:\n"
            '- "migration_steps": list of objects {title, description, target_modules, estimated_effort, dependencies} '
            "where estimated_effort is one of: low, medium, high, very_high\n"
            '- "priority_order": list of step titles in recommended execution order\n'
            '- "risk_assessment": object {overall_risk, risk_factors, mitigation_strategies} '
            "where overall_risk is one of: low, medium, high, critical\n"
            '- "tech_debt_items": list of objects {description, category, severity, effort_to_fix}\n'
            '- "recommended_patterns": list of objects {pattern, rationale, applicable_modules}\n'
            '- "quick_wins": list of objects {action, impact, effort} for low-effort high-impact improvements\n'
            '- "roadmap": list of objects {sprint, actions} where sprint is an integer (1-6) and actions is a list of '
            "objects {action, justification, estimated_hours, category}. "
            "category is one of: dead_code, security, dependencies, decoupling, refactoring, testing. "
            "Priority order: dead_code_removal → security_fixes → dependency_updates → module_decoupling → architecture_refactoring → testing\n"
            '- "summary": a brief 3-4 sentence modernization strategy overview\n\n'
            "Return ONLY valid JSON. No markdown fences, no explanation text outside the JSON."
        )

    def _build_user_prompt(self, summary: str) -> str:
        return (
            "Analyze the following project data including architecture, quality metrics, and security findings. "
            "Produce a comprehensive modernization plan that addresses tech debt, outdated patterns, "
            "and migration opportunities. Prioritize by impact and feasibility:\n\n"
            f"{summary}"
        )

    def _parse_response(self, raw: str) -> dict:
        """Parse Claude's JSON response, with fallback for malformed output."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            plan = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Modernization agent: Failed to parse JSON, using raw text as summary")
            plan = {
                "migration_steps": [],
                "priority_order": [],
                "risk_assessment": {"overall_risk": "unknown", "risk_factors": [], "mitigation_strategies": []},
                "tech_debt_items": [],
                "recommended_patterns": [],
                "quick_wins": [],
                "summary": cleaned[:500],
            }

        # Ensure expected keys exist
        plan.setdefault("migration_steps", [])
        plan.setdefault("priority_order", [])
        plan.setdefault("risk_assessment", {"overall_risk": "unknown", "risk_factors": [], "mitigation_strategies": []})
        plan.setdefault("tech_debt_items", [])
        plan.setdefault("recommended_patterns", [])
        plan.setdefault("quick_wins", [])
        plan.setdefault("roadmap", [])
        plan.setdefault("summary", "")

        # Ensure roadmap has proper structure if empty
        if not plan["roadmap"]:
            plan["roadmap"] = self._generate_fallback_roadmap(plan)

        return plan

    def _generate_fallback_roadmap(self, plan: dict) -> list[dict]:
        """Generate a basic roadmap from migration_steps if Claude didn't produce one."""
        roadmap: list[dict] = []
        steps = plan.get("migration_steps", [])

        if not steps:
            return []

        # Distribute steps across 4 sprints
        sprint_size = max(1, len(steps) // 4)
        for i, step in enumerate(steps):
            sprint_num = min(4, (i // sprint_size) + 1)
            title = step.get("title", f"Step {i+1}") if isinstance(step, dict) else str(step)
            effort = step.get("estimated_effort", "medium") if isinstance(step, dict) else "medium"

            # Find or create sprint entry
            sprint_entry = next((s for s in roadmap if s["sprint"] == sprint_num), None)
            if sprint_entry is None:
                sprint_entry = {"sprint": sprint_num, "actions": []}
                roadmap.append(sprint_entry)

            sprint_entry["actions"].append({
                "action": title,
                "justification": step.get("description", "") if isinstance(step, dict) else "",
                "estimated_hours": {"low": 4, "medium": 8, "high": 16, "very_high": 32}.get(effort, 8),
                "category": "refactoring",
            })

        return roadmap
