"""GET /report/{job_id} — Return consolidated analysis report.

Transforms the raw agent outputs into the format expected by the frontend:
{
  projectName, language, framework, modules, dependencies,
  components, metrics, agentsStatus, incompleteSections
}
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from src.api.job_store import jobs
from src.domain.models.analysis_job import JobStatus

router = APIRouter(prefix="/report", tags=["report"])

_ACTIVE_STATUSES = {
    JobStatus.CLONING,
    JobStatus.ANALYZING,
    JobStatus.COMPLETED,
    JobStatus.FAILED,
}


@router.get(
    "/{job_id}",
    summary="Get consolidated analysis report",
    status_code=status.HTTP_200_OK,
)
async def get_report(job_id: UUID) -> dict:
    """Return the analysis report for a job, formatted for the frontend.

    Returns partial results while the pipeline is running.
    """
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )

    if job.status not in _ACTIVE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job {job_id} is in status '{job.status.value}' — no results available yet.",
        )

    # Extract project info from the model (available after repository_agent)
    project = job.project
    language_name = project.language if project else "unknown"
    framework_name = project.framework if project else "unknown"
    total_loc = project.total_loc if project else 0
    total_files = project.total_files if project else 0

    # Derive project name from repo URL
    project_name = job.repo_url.rstrip("/").split("/")[-1] if job.repo_url else "Unknown"

    # Build modules from architecture report layers
    arch = job.architecture_report or {}
    modules = []
    for layer in arch.get("layers", []):
        modules.append({
            "name": layer.get("name", ""),
            "responsibility": layer.get("responsibility", ""),
            "loc": 0,  # LOC per module not tracked individually
        })

    # Build dependencies from architecture patterns or project graph
    external_deps = []
    internal_deps = []
    if arch.get("patterns"):
        for pattern in arch.get("patterns", []):
            if isinstance(pattern, dict):
                internal_deps.append({
                    "from": pattern.get("name", ""),
                    "to": pattern.get("description", ""),
                    "type": "pattern",
                })

    # Build components from architecture layers/modules
    components = []
    for layer in arch.get("layers", []):
        mods = layer.get("modules", "")
        if isinstance(mods, str):
            for mod_name in mods.split()[:5]:  # First 5 per layer
                components.append({
                    "name": mod_name,
                    "module": layer.get("name", ""),
                    "responsibility": layer.get("responsibility", ""),
                })

    # Build metrics
    quality = job.quality_report or {}
    quality_metrics = quality.get("metrics", {})
    module_count = len(modules) if modules else (quality_metrics.get("module_count", 0))
    max_depth = quality_metrics.get("max_dependency_depth", quality_metrics.get("maxDependencyDepth", 0))

    # Build agent status map
    agents_status = {}
    incomplete_sections = []
    agent_names = [
        "architecture_agent",
        "quality_agent",
        "security_agent",
        "documentation_agent",
        "modernization_agent",
    ]
    for agent_name in agent_names:
        # Check if this agent has results
        agent_result = next(
            (r for r in job.agent_results if r.agent_name == agent_name),
            None,
        )
        if agent_result is not None:
            agents_status[agent_name] = agent_result.status.value
        else:
            agents_status[agent_name] = "pending"
            incomplete_sections.append(agent_name)

    return {
        "projectName": project_name,
        "language": {"name": language_name or "unknown", "version": ""},
        "framework": {"name": framework_name or "unknown", "version": ""},
        "modules": modules,
        "dependencies": {
            "internal": internal_deps,
            "external": external_deps,
        },
        "components": components,
        "metrics": {
            "totalLoc": total_loc,
            "moduleCount": module_count,
            "maxDependencyDepth": max_depth,
        },
        "agentsStatus": agents_status,
        "incompleteSections": incomplete_sections,
        # Also include raw reports for advanced views
        "rawReports": {
            "architecture": arch,
            "quality": quality,
            "security": job.security_report or {},
            "documentation": job.documentation_bundle or {},
            "modernization": job.modernization_plan or {},
        },
    }
