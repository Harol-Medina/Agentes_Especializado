"""Security_Agent — vulnerability assessment via Claude Sonnet.

Execution order: 4. Requires project_model from Repository_Agent.
Produces: security_report with vulnerabilities, risk assessment, and recommendations.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from src.adapters.bedrock_adapter import BedrockAdapter, BedrockInvocationError
from src.agents.base import AgentOutput, BaseAgent, PipelineContext, AgentExecutionError
from src.agents.semgrep_scanner import SemgrepScanner
from src.domain.models.agent_result import AgentStatus
from src.domain.models.project_model import NodeType

logger = logging.getLogger(__name__)

MAX_INPUT_CHARS = 3000


def _truncate(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """Truncate text to max_chars, appending ellipsis if trimmed."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


class SecurityAgent(BaseAgent):
    """Scans project for security vulnerabilities and produces a risk assessment."""

    def __init__(self, bedrock: Optional[BedrockAdapter] = None) -> None:
        self._bedrock = bedrock or BedrockAdapter()

    @property
    def name(self) -> str:
        return "security_agent"

    @property
    def execution_order(self) -> int:
        return 4

    def can_execute(self, context: PipelineContext) -> bool:
        return context.project_model is not None

    async def execute(self, context: PipelineContext) -> AgentOutput:
        """Run Semgrep scan + Claude vulnerability assessment."""
        project = context.project_model
        assert project is not None

        try:
            # Run Semgrep static analysis (if available)
            semgrep_report: dict = {}
            if context.repo_path:
                scanner = SemgrepScanner()
                scan_result = await scanner.scan(
                    repo_path=str(context.repo_path),
                    language=project.language or "java",
                )
                semgrep_report = scan_result.to_dict()

            # Claude-based vulnerability assessment
            security_context = self._build_security_context(context)
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(security_context)

            raw_response = await self._bedrock.invoke_claude(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=4096,
            )

            report = self._parse_response(raw_response)

            # Merge Semgrep findings into report
            if semgrep_report:
                report["semgrep"] = semgrep_report

            return AgentOutput(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                data=report,
                context_updates={"security_report": report},
            )

        except BedrockInvocationError as exc:
            logger.error("Security agent failed: %s", exc.message)
            raise AgentExecutionError(self.name, exc.message) from exc
        except Exception as exc:
            logger.error("Security agent unexpected error: %s", str(exc))
            raise AgentExecutionError(self.name, str(exc)) from exc

    def _build_security_context(self, context: PipelineContext) -> str:
        """Build security-relevant context from project model."""
        project = context.project_model
        assert project is not None

        lines: list[str] = []
        lines.append(f"Project: {project.name}")
        lines.append(f"Language: {project.language or 'unknown'}")
        lines.append(f"Framework: {project.framework or 'unknown'}")
        lines.append(f"Total files: {project.total_files}")
        lines.append("")

        # Extract external dependencies from metadata
        external_deps: list[str] = []
        for node in project.nodes:
            if node.metadata.get("is_external"):
                external_deps.append(node.name)
            # Also check for dependency info in metadata
            deps = node.metadata.get("dependencies", [])
            if isinstance(deps, list):
                external_deps.extend(deps)

        if external_deps:
            lines.append("## External Dependencies:")
            for dep in sorted(set(external_deps))[:50]:
                lines.append(f"  - {dep}")
            lines.append("")

        # Security-sensitive file patterns
        sensitive_patterns = [
            "auth", "security", "crypto", "token", "session",
            "password", "secret", "key", "cert", "ssl", "tls",
            "oauth", "jwt", "login", "permission", "acl",
        ]

        files = [n for n in project.nodes if n.node_type == NodeType.FILE]
        sensitive_files: list[str] = []
        for f in files:
            name_lower = (f.name or "").lower()
            path_lower = (f.file_path or "").lower()
            for pattern in sensitive_patterns:
                if pattern in name_lower or pattern in path_lower:
                    sensitive_files.append(f.file_path or f.name)
                    break

        if sensitive_files:
            lines.append("## Security-sensitive files detected:")
            for sf in sensitive_files[:30]:
                lines.append(f"  - {sf}")
            lines.append("")

        # Config/env files
        config_patterns = [
            ".env", "config", "settings", "application.yml",
            "application.properties", "docker-compose",
        ]
        config_files: list[str] = []
        for f in files:
            name_lower = (f.name or "").lower()
            for pattern in config_patterns:
                if pattern in name_lower:
                    config_files.append(f.file_path or f.name)
                    break

        if config_files:
            lines.append("## Configuration files:")
            for cf in config_files[:20]:
                lines.append(f"  - {cf}")

        return _truncate("\n".join(lines))

    def _build_system_prompt(self) -> str:
        return (
            "You are a senior application security engineer. Based on the project information provided, "
            "produce a JSON security assessment with the following keys:\n"
            '- "vulnerabilities": list of objects {title, description, severity, category, affected_files}\n'
            '  severity: "critical" | "high" | "medium" | "low"\n'
            '  category: "dependency" | "authentication" | "injection" | "configuration" | "data_exposure" | "other"\n'
            '- "risk_score": integer 1-100 (100 = highest risk)\n'
            '- "dependency_risks": list of objects {package, issue, recommendation}\n'
            '- "security_posture": brief assessment of overall security posture\n'
            '- "recommendations": list of prioritized actionable security improvements\n'
            '- "summary": a brief 2-3 sentence security assessment\n\n'
            "Focus on: known vulnerable dependency patterns, insecure configurations, "
            "missing security controls, authentication/authorization gaps, and data exposure risks.\n\n"
            "Return ONLY valid JSON. No markdown fences, no explanation text outside the JSON."
        )

    def _build_user_prompt(self, security_context: str) -> str:
        return (
            "Perform a security assessment on the following project. "
            "Identify potential vulnerabilities, dependency risks, and security gaps:\n\n"
            f"{security_context}"
        )

    def _parse_response(self, raw: str) -> dict:
        """Parse Claude's JSON response for security report."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            report = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Security agent: Failed to parse JSON, using raw text as summary")
            report = {
                "vulnerabilities": [],
                "risk_score": 50,
                "dependency_risks": [],
                "security_posture": "Unable to fully assess — response parsing failed.",
                "recommendations": [],
                "summary": cleaned[:500],
            }

        # Ensure expected keys
        report.setdefault("vulnerabilities", [])
        report.setdefault("risk_score", 50)
        report.setdefault("dependency_risks", [])
        report.setdefault("security_posture", "")
        report.setdefault("recommendations", [])
        report.setdefault("summary", "")

        return report
