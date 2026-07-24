"""End-to-end test: full pipeline against spring-petclinic.

This script exercises the complete agent pipeline (7 agents) against
https://github.com/spring-projects/spring-petclinic without requiring
Docker. It validates:
  1. Git clone (RepositoryAgent)
  2. Language/framework detection (Java/Spring Boot)
  3. Tree-sitter parsing (Java files)
  4. Graph construction
  5. Architecture analysis via Bedrock Claude
  6. Quality analysis via Bedrock Claude
  7. Security analysis via Bedrock Claude
  8. Documentation generation via Bedrock Claude
  9. Modernization planning via Bedrock Claude
  10. Kiro spec generation via Bedrock Claude

Requirements:
  - Python 3.11+
  - pip install -r requirements.txt
  - Valid AWS credentials in environment (or .data/.env)
  - Git installed

Usage:
  cd apps/analyzer
  set DATABASE_URL=postgresql+asyncpg://x:x@localhost:5432/x
  set WEBHOOK_SECRET=test_secret
  set AWS_ACCESS_KEY_ID=<your-access-key-id>
  set AWS_SECRET_ACCESS_KEY=<your-secret-access-key>
  set BEDROCK_MODEL_ID=anthropic.claude-sonnet-4-5-20250929-v1:0
  set BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
  python test_e2e_petclinic.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Set minimal env vars if not present (for standalone run)
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("WEBHOOK_SECRET", "e2e_test_secret")

from src.agents.architecture_agent import ArchitectureAgent
from src.agents.base import AgentOutput, PipelineContext
from src.agents.documentation_agent import DocumentationAgent
from src.agents.kiro_agent import KiroAgent
from src.agents.modernization_agent import ModernizationAgent
from src.agents.quality_agent import QualityAgent
from src.agents.repository_agent import RepositoryAgent
from src.agents.security_agent import SecurityAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("e2e_test")

REPO_URL = "https://github.com/spring-projects/spring-petclinic"
JOB_ID = uuid4()


def print_separator(title: str) -> None:
    logger.info("=" * 60)
    logger.info(f"  {title}")
    logger.info("=" * 60)


def print_result(agent_name: str, output: AgentOutput, elapsed: float) -> None:
    logger.info(f"  Agent: {agent_name}")
    logger.info(f"  Status: {output.status.value}")
    logger.info(f"  Elapsed: {elapsed:.1f}s")
    logger.info(f"  Data keys: {list(output.data.keys())}")
    logger.info(f"  Context updates: {list(output.context_updates.keys())}")
    # Print a summary of data (first 500 chars)
    data_str = json.dumps(output.data, indent=2, default=str)
    if len(data_str) > 800:
        data_str = data_str[:800] + "\n  ... [truncated]"
    logger.info(f"  Data preview:\n{data_str}")
    logger.info("")


async def run_e2e() -> None:
    """Run the full E2E pipeline against spring-petclinic."""
    start_total = time.time()

    context = PipelineContext(job_id=JOB_ID, repo_url=REPO_URL)

    # ===================================================================
    # Agent 1: RepositoryAgent (clone + parse + graph)
    # ===================================================================
    print_separator("Agent 1: RepositoryAgent")
    agent = RepositoryAgent()
    start = time.time()

    try:
        output = await agent.execute(context)
        elapsed = time.time() - start
        print_result("repository_agent", output, elapsed)

        # Apply context updates
        for key, value in output.context_updates.items():
            if hasattr(context, key):
                setattr(context, key, value)

        logger.info(f"  Project: {context.project_model.name}")
        logger.info(f"  Language: {context.project_model.language}")
        logger.info(f"  Framework: {context.project_model.framework}")
        logger.info(f"  Files: {context.project_model.total_files}")
        logger.info(f"  LOC: {context.project_model.total_loc}")
        logger.info(f"  Nodes: {len(context.project_model.nodes)}")
        logger.info(f"  Edges: {len(context.project_model.edges)}")

    except Exception as exc:
        logger.error(f"  FAILED: {exc}")
        logger.error("  Cannot continue without RepositoryAgent. Aborting.")
        return

    # ===================================================================
    # Agent 2: ArchitectureAgent (Bedrock Claude)
    # ===================================================================
    print_separator("Agent 2: ArchitectureAgent")
    agent = ArchitectureAgent()

    if not agent.can_execute(context):
        logger.warning("  SKIPPED: can_execute=False")
    else:
        start = time.time()
        try:
            output = await agent.execute(context)
            elapsed = time.time() - start
            print_result("architecture_agent", output, elapsed)
            for key, value in output.context_updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
        except Exception as exc:
            logger.error(f"  FAILED (non-critical): {exc}")

    # ===================================================================
    # Agent 3: QualityAgent (Bedrock Claude)
    # ===================================================================
    print_separator("Agent 3: QualityAgent")
    agent = QualityAgent()

    if not agent.can_execute(context):
        logger.warning("  SKIPPED: can_execute=False")
    else:
        start = time.time()
        try:
            output = await agent.execute(context)
            elapsed = time.time() - start
            print_result("quality_agent", output, elapsed)
            for key, value in output.context_updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
        except Exception as exc:
            logger.error(f"  FAILED (non-critical): {exc}")

    # ===================================================================
    # Agent 4: SecurityAgent (Bedrock Claude)
    # ===================================================================
    print_separator("Agent 4: SecurityAgent")
    agent = SecurityAgent()

    if not agent.can_execute(context):
        logger.warning("  SKIPPED: can_execute=False")
    else:
        start = time.time()
        try:
            output = await agent.execute(context)
            elapsed = time.time() - start
            print_result("security_agent", output, elapsed)
            for key, value in output.context_updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
        except Exception as exc:
            logger.error(f"  FAILED (non-critical): {exc}")

    # ===================================================================
    # Agent 5: DocumentationAgent (Bedrock Claude)
    # ===================================================================
    print_separator("Agent 5: DocumentationAgent")
    agent = DocumentationAgent()

    if not agent.can_execute(context):
        logger.warning("  SKIPPED: can_execute=False (needs architecture_report)")
    else:
        start = time.time()
        try:
            output = await agent.execute(context)
            elapsed = time.time() - start
            print_result("documentation_agent", output, elapsed)
            for key, value in output.context_updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
        except Exception as exc:
            logger.error(f"  FAILED (non-critical): {exc}")

    # ===================================================================
    # Agent 6: ModernizationAgent (Bedrock Claude)
    # ===================================================================
    print_separator("Agent 6: ModernizationAgent")
    agent = ModernizationAgent()

    if not agent.can_execute(context):
        logger.warning("  SKIPPED: can_execute=False (needs architecture_report)")
    else:
        start = time.time()
        try:
            output = await agent.execute(context)
            elapsed = time.time() - start
            print_result("modernization_agent", output, elapsed)
            for key, value in output.context_updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
        except Exception as exc:
            logger.error(f"  FAILED (non-critical): {exc}")

    # ===================================================================
    # Agent 7: KiroAgent (Bedrock Claude)
    # ===================================================================
    print_separator("Agent 7: KiroAgent")
    agent = KiroAgent()

    if not agent.can_execute(context):
        logger.warning("  SKIPPED: can_execute=False")
    else:
        start = time.time()
        try:
            output = await agent.execute(context)
            elapsed = time.time() - start
            print_result("kiro_agent", output, elapsed)
            for key, value in output.context_updates.items():
                if hasattr(context, key):
                    setattr(context, key, value)
        except Exception as exc:
            logger.error(f"  FAILED (non-critical): {exc}")

    # ===================================================================
    # Summary
    # ===================================================================
    total_elapsed = time.time() - start_total
    print_separator("E2E SUMMARY")
    logger.info(f"  Repo: {REPO_URL}")
    logger.info(f"  Job ID: {JOB_ID}")
    logger.info(f"  Total elapsed: {total_elapsed:.1f}s")
    logger.info(f"  Project model: {'YES' if context.project_model else 'NO'}")
    logger.info(f"  Architecture report: {'YES' if context.architecture_report else 'NO'}")
    logger.info(f"  Quality report: {'YES' if context.quality_report else 'NO'}")
    logger.info(f"  Security report: {'YES' if context.security_report else 'NO'}")
    logger.info(f"  Documentation bundle: {'YES' if context.documentation_bundle else 'NO'}")
    logger.info(f"  Modernization plan: {'YES' if context.modernization_plan else 'NO'}")
    logger.info(f"  Kiro spec: {'YES' if context.kiro_spec else 'NO'}")

    # Save results to file
    results_path = Path(__file__).parent / "e2e_results.json"
    results = {
        "repo_url": REPO_URL,
        "job_id": str(JOB_ID),
        "total_elapsed_seconds": round(total_elapsed, 1),
        "project_model": {
            "name": context.project_model.name if context.project_model else None,
            "language": context.project_model.language if context.project_model else None,
            "framework": context.project_model.framework if context.project_model else None,
            "total_files": context.project_model.total_files if context.project_model else 0,
            "total_loc": context.project_model.total_loc if context.project_model else 0,
            "total_nodes": len(context.project_model.nodes) if context.project_model else 0,
            "total_edges": len(context.project_model.edges) if context.project_model else 0,
        },
        "architecture_report": context.architecture_report,
        "quality_report": context.quality_report,
        "security_report": context.security_report,
        "documentation_bundle": context.documentation_bundle,
        "modernization_plan": context.modernization_plan,
        "kiro_spec": context.kiro_spec,
    }
    results_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    logger.info(f"  Results saved to: {results_path}")

    # Cleanup cloned repo
    if context.repo_path and Path(context.repo_path).exists():
        shutil.rmtree(context.repo_path, ignore_errors=True)
        logger.info(f"  Cleaned up: {context.repo_path}")

    logger.info("")
    if context.kiro_spec:
        logger.info("  *** E2E TEST PASSED — Full pipeline completed ***")
    elif context.project_model:
        logger.info("  *** E2E PARTIAL — RepositoryAgent OK, some Bedrock agents may have failed ***")
    else:
        logger.info("  *** E2E FAILED ***")


if __name__ == "__main__":
    asyncio.run(run_e2e())
