"""Language and framework detection from repository file structure.

Implements marker-based detection for Java, TypeScript, and JavaScript
with framework identification based on dependency manifests.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LanguageDetector:
    """Detects primary language and framework from repository file structure."""

    # Marker files that identify a language
    LANGUAGE_MARKERS: dict[str, list[str]] = {
        "java": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "typescript": ["tsconfig.json"],
        "javascript": ["package.json"],
    }

    # Framework markers within dependency manifests
    FRAMEWORK_MARKERS: dict[str, dict[str, list[str]]] = {
        "java": {
            "spring-boot": ["spring-boot-starter", "org.springframework.boot"],
            "quarkus": ["quarkus-", "io.quarkus"],
            "jakarta-ee": ["jakarta."],
        },
        "typescript": {
            "next": ["next"],
            "angular": ["@angular/core"],
            "react": ["react", "react-dom"],
            "vue": ["vue"],
            "nestjs": ["@nestjs/core"],
        },
        "javascript": {
            "express": ["express"],
            "next": ["next"],
            "angular": ["@angular/core"],
            "react": ["react", "react-dom"],
            "vue": ["vue"],
            "nestjs": ["@nestjs/core"],
        },
    }

    def detect(self, repo_path: str | Path) -> tuple[str, str]:
        """Detect the primary language and framework of a repository.

        Detection priority:
        1. Java (pom.xml / build.gradle) → check for Spring Boot, Quarkus, Jakarta
        2. TypeScript (tsconfig.json) → check package.json for Next, Angular, React, etc.
        3. JavaScript (package.json without tsconfig.json) → same framework checks

        Args:
            repo_path: Path to the root of the cloned repository.

        Returns:
            Tuple of (language, framework). Both default to "unknown" if
            detection fails.
        """
        repo = Path(repo_path)

        # --- Java detection ---
        if self._has_marker(repo, "java"):
            framework = self._detect_java_framework(repo)
            return ("java", framework)

        # --- TypeScript detection (tsconfig.json present) ---
        if self._has_marker(repo, "typescript"):
            framework = self._detect_js_framework(repo)
            return ("typescript", framework)

        # --- JavaScript detection (package.json without tsconfig) ---
        if self._has_marker(repo, "javascript"):
            framework = self._detect_js_framework(repo)
            return ("javascript", framework)

        return ("unknown", "unknown")

    def _has_marker(self, repo: Path, language: str) -> bool:
        """Check if any marker file for the given language exists in the repo root."""
        markers = self.LANGUAGE_MARKERS.get(language, [])
        for marker in markers:
            if (repo / marker).exists():
                return True
        return False

    def _detect_java_framework(self, repo: Path) -> str:
        """Detect Java framework by inspecting build file dependencies."""
        content = ""

        # Read pom.xml
        pom_path = repo / "pom.xml"
        if pom_path.exists():
            try:
                content = pom_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass

        # Read build.gradle / build.gradle.kts
        for gradle_file in ("build.gradle", "build.gradle.kts"):
            gradle_path = repo / gradle_file
            if gradle_path.exists():
                try:
                    content += "\n" + gradle_path.read_text(
                        encoding="utf-8", errors="replace"
                    )
                except OSError:
                    pass

        if not content:
            return "unknown"

        # Check framework markers against content
        for framework, markers in self.FRAMEWORK_MARKERS["java"].items():
            for marker in markers:
                if marker in content:
                    return framework

        return "unknown"

    def _detect_js_framework(self, repo: Path) -> str:
        """Detect JS/TS framework by inspecting package.json dependencies."""
        package_json_path = repo / "package.json"
        if not package_json_path.exists():
            # Also check for next.config.* or angular.json as standalone markers
            if (repo / "angular.json").exists():
                return "angular"
            for ext in ("js", "mjs", "ts"):
                if (repo / f"next.config.{ext}").exists():
                    return "next"
            return "unknown"

        try:
            data = json.loads(
                package_json_path.read_text(encoding="utf-8", errors="replace")
            )
        except (json.JSONDecodeError, OSError):
            return "unknown"

        # Merge dependencies and devDependencies
        deps: dict[str, str] = {}
        deps.update(data.get("dependencies", {}))
        deps.update(data.get("devDependencies", {}))

        dep_names = set(deps.keys())

        # Determine the correct language key for framework markers
        # TypeScript if tsconfig.json exists, else JavaScript
        lang_key = "typescript" if (repo / "tsconfig.json").exists() else "javascript"
        framework_markers = self.FRAMEWORK_MARKERS.get(lang_key, {})

        # Check in priority order (more specific first)
        for framework, markers in framework_markers.items():
            if all(m in dep_names for m in markers):
                return framework

        return "unknown"
