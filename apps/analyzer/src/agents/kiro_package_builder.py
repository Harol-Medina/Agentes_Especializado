"""Kiro Package Builder — generates a complete .kiro/ directory structure as a zip.

Produces a downloadable zip containing:
  specs/modernization/
    requirements.md
    design.md
    tasks.md
  hooks/
    post-modernization.json

Requirement: V2-10.1, V2-10.2
"""

from __future__ import annotations

import io
import json
import logging
import zipfile
from typing import Optional

logger = logging.getLogger(__name__)


class KiroPackageBuilder:
    """Builds a complete .kiro package from analysis results.

    The package contains a full spec structure (requirements, design, tasks)
    plus suggested hooks for post-modernization automation.
    """

    def build(
        self,
        project_name: str,
        kiro_spec: Optional[str],
        architecture_report: Optional[dict],
        modernization_plan: Optional[dict],
        quality_report: Optional[dict],
        security_report: Optional[dict],
    ) -> bytes:
        """Build the .kiro package zip from analysis data.

        Args:
            project_name: Name of the analyzed project.
            kiro_spec: Full Kiro spec markdown (from KiroAgent).
            architecture_report: Architecture analysis data.
            modernization_plan: Modernization plan with roadmap.
            quality_report: Quality metrics and dead code.
            security_report: Security findings.

        Returns:
            Bytes of the zip file.
        """
        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Generate the three spec files
            requirements_md = self._build_requirements(
                project_name, architecture_report, quality_report, security_report
            )
            design_md = self._build_design(
                project_name, architecture_report, modernization_plan
            )
            tasks_md = self._build_tasks(
                project_name, modernization_plan, quality_report, security_report
            )

            # Write spec files
            zf.writestr("specs/modernization/requirements.md", requirements_md)
            zf.writestr("specs/modernization/design.md", design_md)
            zf.writestr("specs/modernization/tasks.md", tasks_md)

            # Write hooks
            hooks_json = self._build_hooks(project_name)
            zf.writestr("hooks/post-modernization.json", hooks_json)

            # Include original kiro_spec if available
            if kiro_spec:
                zf.writestr("specs/modernization/original-spec.md", kiro_spec)

        logger.info("Kiro package built — project=%s, size=%d bytes", project_name, buffer.tell())
        return buffer.getvalue()

    def _build_requirements(
        self,
        project_name: str,
        arch: Optional[dict],
        quality: Optional[dict],
        security: Optional[dict],
    ) -> str:
        """Generate requirements.md from analysis data."""
        lines = [
            f"# Requirements: Modernización de {project_name}",
            "",
            "## Introduction",
            "",
            f"Requisitos de modernización derivados del análisis automático de `{project_name}`.",
            "Generado por Software Archaeologist.",
            "",
            "## Requirements",
            "",
        ]

        req_num = 1

        # Architecture-derived requirements
        if arch:
            violations = arch.get("violations", [])
            if violations:
                lines.append("### Arquitectura")
                lines.append("")
                for v in violations[:5]:
                    desc = v.get("description", str(v)) if isinstance(v, dict) else str(v)
                    lines.append(f"- REQ-{req_num}: Resolver violación arquitectónica — {desc[:100]}")
                    req_num += 1
                lines.append("")

            recommendations = arch.get("recommendations", [])
            if recommendations:
                for rec in recommendations[:5]:
                    lines.append(f"- REQ-{req_num}: {str(rec)[:100]}")
                    req_num += 1
                lines.append("")

        # Quality-derived requirements
        if quality:
            analysis = quality.get("analysis", {})
            smells = analysis.get("code_smells", [])
            if smells:
                lines.append("### Calidad de Código")
                lines.append("")
                for smell in smells[:5]:
                    name = smell.get("name", str(smell)) if isinstance(smell, dict) else str(smell)
                    lines.append(f"- REQ-{req_num}: Corregir code smell — {name[:80]}")
                    req_num += 1
                lines.append("")

            dead_code = quality.get("dead_code", [])
            if dead_code:
                lines.append(f"- REQ-{req_num}: Eliminar {len(dead_code)} candidatos de código muerto detectados")
                req_num += 1
                lines.append("")

        # Security-derived requirements
        if security:
            vulns = security.get("vulnerabilities", [])
            if vulns:
                lines.append("### Seguridad")
                lines.append("")
                critical_high = [v for v in vulns if isinstance(v, dict) and v.get("severity") in ("critical", "high")]
                if critical_high:
                    for v in critical_high[:5]:
                        lines.append(f"- REQ-{req_num}: [Seguridad] {v.get('title', v.get('description', ''))[:80]}")
                        req_num += 1
                else:
                    lines.append(f"- REQ-{req_num}: Revisar y resolver {len(vulns)} hallazgos de seguridad")
                    req_num += 1
                lines.append("")

        if req_num == 1:
            lines.append("- REQ-1: Realizar análisis completo del proyecto para derivar requisitos concretos")
            lines.append("")

        return "\n".join(lines)

    def _build_design(
        self,
        project_name: str,
        arch: Optional[dict],
        mod_plan: Optional[dict],
    ) -> str:
        """Generate design.md from architecture analysis."""
        lines = [
            f"# Design: Modernización de {project_name}",
            "",
            "## Arquitectura Actual",
            "",
        ]

        if arch:
            if arch.get("summary"):
                lines.append(str(arch["summary"]))
                lines.append("")

            patterns = arch.get("patterns", [])
            if patterns:
                lines.append("### Patrones Detectados")
                lines.append("")
                for p in patterns[:8]:
                    lines.append(f"- {p if isinstance(p, str) else p.get('name', str(p))}")
                lines.append("")

            layers = arch.get("layers", [])
            if layers:
                lines.append("### Capas")
                lines.append("")
                for layer in layers[:8]:
                    if isinstance(layer, dict):
                        lines.append(f"- **{layer.get('name', '?')}**: {layer.get('responsibility', '')}")
                    else:
                        lines.append(f"- {str(layer)}")
                lines.append("")
        else:
            lines.append("Análisis de arquitectura no disponible.")
            lines.append("")

        # Proposed architecture
        lines.append("## Arquitectura Propuesta")
        lines.append("")

        if mod_plan:
            if mod_plan.get("recommended_patterns"):
                lines.append("### Patrones Recomendados")
                lines.append("")
                for pat in mod_plan["recommended_patterns"][:5]:
                    if isinstance(pat, dict):
                        lines.append(f"- **{pat.get('pattern', '?')}**: {pat.get('rationale', '')}")
                    else:
                        lines.append(f"- {str(pat)}")
                lines.append("")

            if mod_plan.get("summary"):
                lines.append("### Estrategia")
                lines.append("")
                lines.append(str(mod_plan["summary"]))
                lines.append("")
        else:
            lines.append("Plan de modernización no disponible — ejecutar análisis completo.")
            lines.append("")

        return "\n".join(lines)

    def _build_tasks(
        self,
        project_name: str,
        mod_plan: Optional[dict],
        quality: Optional[dict],
        security: Optional[dict],
    ) -> str:
        """Generate tasks.md from modernization roadmap."""
        lines = [
            f"# Tasks: Modernización de {project_name}",
            "",
            "## Tasks",
            "",
        ]

        task_num = 1

        # From roadmap (sprint-organized)
        if mod_plan and mod_plan.get("roadmap"):
            roadmap = mod_plan["roadmap"]
            for sprint in roadmap:
                sprint_num = sprint.get("sprint", "?")
                actions = sprint.get("actions", [])
                lines.append(f"### Sprint {sprint_num}")
                lines.append("")
                for action in actions:
                    act_name = action.get("action", "") if isinstance(action, dict) else str(action)
                    hours = action.get("estimated_hours", "?") if isinstance(action, dict) else "?"
                    lines.append(f"- [ ] TASK-{task_num}: {act_name} (~{hours}h)")
                    task_num += 1
                lines.append("")

        # From migration_steps if no roadmap
        elif mod_plan and mod_plan.get("migration_steps"):
            for step in mod_plan["migration_steps"]:
                if isinstance(step, dict):
                    title = step.get("title", str(step))
                    effort = step.get("estimated_effort", "?")
                    lines.append(f"- [ ] TASK-{task_num}: {title} (effort: {effort})")
                else:
                    lines.append(f"- [ ] TASK-{task_num}: {str(step)[:100]}")
                task_num += 1
            lines.append("")

        # Dead code tasks
        if quality and quality.get("dead_code"):
            dead_code = quality["dead_code"]
            high_confidence = [d for d in dead_code if d.get("confidence") == "high"]
            if high_confidence:
                lines.append("### Código Muerto (Alta Confianza)")
                lines.append("")
                for dc in high_confidence[:10]:
                    lines.append(f"- [ ] TASK-{task_num}: Eliminar `{dc.get('name', '?')}` — {dc.get('reason', '')[:60]}")
                    task_num += 1
                lines.append("")

        # Security tasks
        if security and security.get("vulnerabilities"):
            vulns = security["vulnerabilities"]
            critical = [v for v in vulns if isinstance(v, dict) and v.get("severity") in ("critical", "high")]
            if critical:
                lines.append("### Seguridad (Crítica/Alta)")
                lines.append("")
                for v in critical[:5]:
                    lines.append(f"- [ ] TASK-{task_num}: [Seguridad] {v.get('title', v.get('description', ''))[:80]}")
                    task_num += 1
                lines.append("")

        if task_num == 1:
            lines.append("- [ ] TASK-1: Ejecutar análisis completo para generar tareas concretas")
            lines.append("")

        return "\n".join(lines)

    def _build_hooks(self, project_name: str) -> str:
        """Generate hooks JSON for post-modernization automation."""
        hooks = {
            "version": "v1",
            "hooks": [
                {
                    "name": "Lint Modernized Code",
                    "trigger": "PostFileSave",
                    "matcher": "\\.(java|ts|tsx|js|py)$",
                    "action": {
                        "type": "command",
                        "command": "npm run lint -- --fix ${file}",
                    },
                },
                {
                    "name": "Run Tests After Task",
                    "trigger": "PostTaskExec",
                    "action": {
                        "type": "command",
                        "command": "npm test -- --run",
                    },
                },
            ],
        }
        return json.dumps(hooks, indent=2)
