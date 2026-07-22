"""Git clone adapter using GitPython.

Provides shallow cloning of public GitHub repositories with size/file-count
validation and exclusion of non-source directories.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from src.agents.base import AgentExecutionError
from src.config import get_settings

logger = logging.getLogger(__name__)

# Directories to exclude from file traversal (not from cloning itself).
EXCLUDED_DIRS: set[str] = {
    ".git",
    "node_modules",
    "__pycache__",
    "target",
    "build",
    "dist",
    ".next",
    ".gradle",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
    "env",
}


class GitAdapter:
    """Clones a public GitHub repository and validates constraints."""

    def __init__(self, base_dir: str | None = None) -> None:
        settings = get_settings()
        self._base_dir = Path(base_dir or settings.temp_repo_dir)
        self._max_file_count = settings.max_file_count
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def clone(self, repo_url: str, job_id: str) -> Path:
        """Clone a repository (shallow, depth=1) into a job-specific directory.

        Args:
            repo_url: Full HTTPS URL to the GitHub repository.
            job_id: Unique job identifier used as directory name.

        Returns:
            Path to the cloned repository root.

        Raises:
            AgentExecutionError: On clone failure or validation failure.
        """
        dest = self._base_dir / job_id

        # Clean up if previous attempt left artifacts
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)

        logger.info("Cloning repository — url=%s, dest=%s", repo_url, dest)

        try:
            Repo.clone_from(
                repo_url,
                str(dest),
                depth=1,
                single_branch=True,
            )
        except (GitCommandError, InvalidGitRepositoryError, OSError) as exc:
            raise AgentExecutionError(
                agent_name="repository_agent",
                message=f"Failed to clone repository '{repo_url}': {exc}",
            ) from exc

        # Validate file count
        file_count = self._count_source_files(dest)
        if file_count > self._max_file_count:
            shutil.rmtree(dest, ignore_errors=True)
            raise AgentExecutionError(
                agent_name="repository_agent",
                message=(
                    f"Repository exceeds max file count: {file_count} > "
                    f"{self._max_file_count}"
                ),
            )

        logger.info(
            "Clone complete — files=%d, path=%s",
            file_count,
            dest,
        )
        return dest

    def cleanup(self, repo_path: Path) -> None:
        """Remove a previously cloned repository directory."""
        if repo_path.exists():
            shutil.rmtree(repo_path, ignore_errors=True)
            logger.info("Cleaned up repo at %s", repo_path)

    def list_source_files(self, repo_path: Path) -> list[Path]:
        """List all source files in the repo, excluding non-source directories.

        Returns:
            List of Path objects pointing to source files.
        """
        source_files: list[Path] = []
        for root, dirs, files in os.walk(repo_path):
            # Prune excluded directories in-place
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]

            for filename in files:
                source_files.append(Path(root) / filename)

        return source_files

    def _count_source_files(self, repo_path: Path) -> int:
        """Count source files (excluding ignored directories)."""
        count = 0
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
            count += len(files)
        return count
