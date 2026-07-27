"""Documentation_Agent — module documentation generation via Claude Sonnet.

Execution order: 5. Requires project_model and architecture_report.
Produces: documentation_bundle with module docs, API descriptions, and getting started guide.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from src.adapters.bedrock_adapter import BedrockAdapter, BedrockInvocationError
from src.agents.base import AgentOutput, BaseAgent, PipelineContext, AgentExecutionError
from src.agents.c4_generator import C4Generator
from src.domain.models.agent_result import AgentStatus
from src.domain.models.project_model import NodeType

logger = logging.getLogger(__name__)

MAX_INPUT_CHARS = 3000


def _truncate(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """Truncate text to max_chars, appending ellipsis if trimmed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


class DocumentationAgent(BaseAgent):
    """Generates module documentation based on project model and architecture report."""

    def __init__(self, bedrock: Optional[BedrockAdapter] = None) -> None:
        self._bedrock = bedrock or BedrockAdapter()

    @property
    def name(self) -> str:
        return "documentation_agent"

    @property
    def execution_order(self) -> int:
        return 5

    def can_execute(self, context: PipelineContext) -> bool:
        """Requires project_model and architecture_report."""
        return (
            context.project_model is not None
            and context.architecture_report is not None
        )

    async def execute(self, context: PipelineContext) -> AgentOutput:
        """Generate module documentation using project model and architecture report."""
        project = context.project_model
        assert project is not None
        assert context.architecture_report is not None

        try:
            doc_context = self._build_doc_context(context)
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(doc_context)

            raw_response = await self._bedrock.invoke_claude(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=4096,
            )

            bundle = self._parse_response(raw_response)

            # Generate C4 diagrams (no LLM needed — pure graph analysis)
            c4 = C4Generator()
            c4_diagrams = c4.generate(project, context.architecture_report)
            bundle["c4_diagrams"] = c4_diagrams.to_dict()

            return AgentOutput(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                data=bundle,
                context_updates={"documentation_bundle": bundle},
            )

        except BedrockInvocationError as exc:
            logger.error("Documentation agent failed: %s", exc.message)
            raise AgentExecutionError(self.name, exc.message) from exc
        except Exception as exc:
            logger.error("Documentation agent unexpected error: %s", str(exc))
            raise AgentExecutionError(self.name, str(exc)) from exc

    def _build_doc_context(self, context: PipelineContext) -> str:
        """Combine project model and architecture report into a documentation prompt."""
        project = context.project_model
        assert project is not None
        arch_report = context.architecture_report or {}

        lines: list[str] = []
        lines.append(f"Project: {project.name}")
        lines.append(f"Language: {project.language or 'unknown'}")
        lines.append(f"Framework: {project.framework or 'unknown'}")
        lines.append(f"Total files: {project.total_files}")
        lines.append(f"Total LOC: {project.total_loc}")
        lines.append("")

        # Architecture summary
        arch_summary = arch_report.get("summary", "")
        if arch_summary:
            lines.append(f"## Architecture Summary:")
            lines.append(arch_summary)
            lines.append("")

        # Detected patterns
        patterns = arch_report.get("patterns", [])
        if patterns:
            lines.append("## Detected Patterns:")
            for p in patterns[:10]:
                if isinstance(p, str):
                    lines.append(f"  - {p}")
                elif isinstance(p, dict):
                    lines.append(f"  - {p.get('name', p)}")
            lines.append("")

        # Layers
        layers = arch_report.get("layers", [])
        if layers:
            lines.append("## Architectural Layers:")
            for layer in layers[:10]:
                if isinstance(layer, dict):
                    name = layer.get("name", "Unknown")
                    resp = layer.get("responsibility", "")
                    modules = layer.get("modules", [])
                    lines.append(f"  - {name}: {resp}")
                    if modules:
                        mod_str = ", ".join(modules[:5])
                        lines.append(f"    Modules: {mod_str}")
                elif isinstance(layer, str):
                    lines.append(f"  - {layer}")
            lines.append("")

        # Modules with their classes
        modules = [n for n in project.nodes if n.node_type in (NodeType.MODULE, NodeType.PACKAGE)]
        if modules:
            lines.append("## Modules:")
            for mod in modules[:20]:
                lines.append(f"  - {mod.name} (LOC: {mod.loc})")
                # Find classes in this module
                module_classes = [
                    n for n in project.nodes
                    if n.node_type == NodeType.CLASS
                    and n.file_path
                    and mod.name in n.file_path
                ]
                for cls in module_classes[:5]:
                    lines.append(f"      class {cls.name} (LOC: {cls.loc})")
            lines.append("")

        # Key entry points
        functions = [n for n in project.nodes if n.node_type == NodeType.FUNCTION]
        entry_points = [
            f for f in functions
            if any(kw in (f.name or "").lower() for kw in ["main", "app", "run", "start", "handler"])
        ]
        if entry_points:
            lines.append("## Entry Points:")
            for ep in entry_points[:10]:
                lines.append(f"  - {ep.name} ({ep.file_path})")

        return _truncate("\n".join(lines))

    def _build_system_prompt(self) -> str:
        return (
            "You are a technical documentation specialist. Generate comprehensive project documentation "
            "as a JSON object with the following keys:\n"
            '- "project_overview": string with a high-level project description (2-3 paragraphs)\n'
            '- "modules": list of objects {name, description, key_classes, responsibilities}\n'
            '- "getting_started": string with setup/run instructions based on detected framework\n'
            '- "architecture_overview": string describing the overall architecture and design decisions\n'
            '- "api_surface": list of objects {endpoint_or_class, description, usage} for key public APIs\n'
            '- "key_concepts": list of objects {name, description} for domain concepts\n\n'
            "Write documentation that would be useful for a new developer joining the project.\n"
            "Return ONLY valid JSON. No markdown fences, no explanation text outside the JSON."
        )

    def _build_user_prompt(self, doc_context: str) -> str:
        return (
            "Generate comprehensive documentation for the following project. "
            "Focus on helping new developers understand the codebase structure, "
            "key modules, and how to get started:\n\n"
            f"{doc_context}"
        )

    def _parse_response(self, raw: str) -> dict:
        """Parse Claude's JSON response for documentation bundle."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            bundle = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Documentation agent: Failed to parse JSON, using raw text")
            bundle = {
                "project_overview": cleaned[:500],
                "modules": [],
                "getting_started": "",
                "architecture_overview": "",
                "api_surface": [],
                "key_concepts": [],
            }

        # Ensure expected keys
        bundle.setdefault("project_overview", "")
        bundle.setdefault("modules", [])
        bundle.setdefault("getting_started", "")
        bundle.setdefault("architecture_overview", "")
        bundle.setdefault("api_surface", [])
        bundle.setdefault("key_concepts", [])

        return bundle
