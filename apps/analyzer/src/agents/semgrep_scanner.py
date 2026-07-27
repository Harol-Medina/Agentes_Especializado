"""Semgrep Scanner — static analysis security scanning with OWASP rulesets.

Runs Semgrep CLI against the cloned repository with language-specific rulesets.
Parses JSON output into structured SecurityFinding objects categorized by severity.

Requirement: V2-5.1, V2-5.2

Note: Semgrep must be installed in the runtime environment (Docker or local).
      pip install semgrep  (or it's included in the Analyzer Dockerfile).
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Ruleset mapping by language ─────────────────────────────────────────────

LANGUAGE_RULESETS: dict[str, list[str]] = {
    "java": ["p/owasp-java", "p/java"],
    "typescript": ["p/owasp-javascript", "p/typescript"],
    "javascript": ["p/owasp-javascript", "p/javascript"],
    "python": ["p/owasp-python", "p/python"],
    "php": ["p/owasp-php", "p/php"],
    "go": ["p/owasp-go", "p/golang"],
}

# Fallback if language not mapped
DEFAULT_RULESETS = ["p/owasp-top-ten", "p/security-audit"]


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class SemgrepFinding:
    """A single security finding from Semgrep."""

    rule_id: str
    message: str
    severity: str  # "ERROR" | "WARNING" | "INFO" → mapped to critical/high/medium/low
    file_path: str
    start_line: int
    end_line: int
    category: str
    cwe: list[str] = field(default_factory=list)
    owasp: list[str] = field(default_factory=list)
    fix_suggestion: str = ""

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "message": self.message,
            "severity": self.severity,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "category": self.category,
            "cwe": self.cwe,
            "owasp": self.owasp,
            "fix_suggestion": self.fix_suggestion,
        }


@dataclass
class SemgrepReport:
    """Aggregated Semgrep scan results."""

    findings: list[SemgrepFinding] = field(default_factory=list)
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    scan_status: str = "success"
    error_message: str = ""
    rulesets_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "scan_status": self.scan_status,
            "error_message": self.error_message,
            "rulesets_used": self.rulesets_used,
        }


# ─── Severity mapping ─────────────────────────────────────────────────────────

def _map_severity(semgrep_severity: str) -> str:
    """Map Semgrep severity levels to our standard levels."""
    mapping = {
        "ERROR": "critical",
        "WARNING": "high",
        "INFO": "medium",
    }
    return mapping.get(semgrep_severity.upper(), "low")


# ─── Scanner ──────────────────────────────────────────────────────────────────

class SemgrepScanner:
    """Runs Semgrep with OWASP rulesets on a cloned repository.

    Usage:
        scanner = SemgrepScanner()
        report = await scanner.scan("/tmp/repos/job-123", "java")
    """

    def __init__(self, timeout_seconds: int = 300) -> None:
        """
        Args:
            timeout_seconds: Maximum time for Semgrep to run (default 5 min).
        """
        self._timeout = timeout_seconds

    async def scan(self, repo_path: str, language: str) -> SemgrepReport:
        """Run Semgrep against the repository and parse results.

        Args:
            repo_path: Path to the cloned repository.
            language: Detected language (java, typescript, etc.).

        Returns:
            SemgrepReport with categorized findings.
        """
        # Determine rulesets
        rulesets = LANGUAGE_RULESETS.get(language.lower(), DEFAULT_RULESETS)

        # Check if semgrep is available
        if not await self._is_semgrep_available():
            logger.warning("Semgrep not installed — returning empty report")
            return SemgrepReport(
                scan_status="skipped",
                error_message="Semgrep is not installed. Install with: pip install semgrep",
                rulesets_used=rulesets,
            )

        # Build command
        config_args = []
        for ruleset in rulesets:
            config_args.extend(["--config", ruleset])

        cmd = [
            "semgrep",
            "scan",
            "--json",
            "--quiet",
            "--no-git-ignore",
            "--max-target-bytes", "1000000",  # Skip files > 1MB
            *config_args,
            repo_path,
        ]

        logger.info(
            "Running Semgrep scan — path=%s, language=%s, rulesets=%s",
            repo_path, language, rulesets,
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self._timeout,
            )

            # Semgrep returns exit code 1 when findings exist (not an error)
            if process.returncode not in (0, 1):
                error_msg = stderr.decode("utf-8", errors="replace")[:500]
                logger.error("Semgrep failed (exit %d): %s", process.returncode, error_msg)
                return SemgrepReport(
                    scan_status="error",
                    error_message=f"Semgrep exited with code {process.returncode}: {error_msg}",
                    rulesets_used=rulesets,
                )

            # Parse JSON output
            raw_output = stdout.decode("utf-8", errors="replace")
            return self._parse_output(raw_output, rulesets, repo_path)

        except asyncio.TimeoutError:
            logger.error("Semgrep scan timed out after %ds", self._timeout)
            return SemgrepReport(
                scan_status="timeout",
                error_message=f"Scan timed out after {self._timeout} seconds",
                rulesets_used=rulesets,
            )
        except FileNotFoundError:
            logger.error("Semgrep binary not found")
            return SemgrepReport(
                scan_status="skipped",
                error_message="Semgrep binary not found in PATH",
                rulesets_used=rulesets,
            )
        except Exception as exc:
            logger.error("Semgrep scan error: %s", str(exc))
            return SemgrepReport(
                scan_status="error",
                error_message=str(exc)[:500],
                rulesets_used=rulesets,
            )

    def _parse_output(self, raw_json: str, rulesets: list[str], repo_path: str) -> SemgrepReport:
        """Parse Semgrep JSON output into structured findings."""
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Semgrep JSON output")
            return SemgrepReport(
                scan_status="error",
                error_message="Failed to parse Semgrep output as JSON",
                rulesets_used=rulesets,
            )

        results = data.get("results", [])
        findings: list[SemgrepFinding] = []

        for result in results:
            # Extract metadata
            extra = result.get("extra", {})
            metadata = extra.get("metadata", {})

            # Build relative file path
            file_path = result.get("path", "")
            if file_path.startswith(repo_path):
                file_path = file_path[len(repo_path):].lstrip("/\\")

            # Map severity
            severity = _map_severity(extra.get("severity", "INFO"))

            # Extract CWE and OWASP tags
            cwe = metadata.get("cwe", [])
            if isinstance(cwe, str):
                cwe = [cwe]
            owasp = metadata.get("owasp", [])
            if isinstance(owasp, str):
                owasp = [owasp]

            # Determine category from metadata
            category = metadata.get("category", "security")
            if "injection" in (extra.get("message", "") + result.get("check_id", "")).lower():
                category = "injection"
            elif "auth" in result.get("check_id", "").lower():
                category = "authentication"

            finding = SemgrepFinding(
                rule_id=result.get("check_id", "unknown"),
                message=extra.get("message", result.get("check_id", "")),
                severity=severity,
                file_path=file_path,
                start_line=result.get("start", {}).get("line", 0),
                end_line=result.get("end", {}).get("line", 0),
                category=category,
                cwe=cwe,
                owasp=owasp,
                fix_suggestion=extra.get("fix", metadata.get("fix", "")),
            )
            findings.append(finding)

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        findings.sort(key=lambda f: severity_order.get(f.severity, 4))

        # Count by severity
        report = SemgrepReport(
            findings=findings,
            total_findings=len(findings),
            critical_count=sum(1 for f in findings if f.severity == "critical"),
            high_count=sum(1 for f in findings if f.severity == "high"),
            medium_count=sum(1 for f in findings if f.severity == "medium"),
            low_count=sum(1 for f in findings if f.severity == "low"),
            scan_status="success",
            rulesets_used=rulesets,
        )

        logger.info(
            "Semgrep scan complete — findings=%d (critical=%d, high=%d, medium=%d, low=%d)",
            report.total_findings,
            report.critical_count,
            report.high_count,
            report.medium_count,
            report.low_count,
        )

        return report

    async def _is_semgrep_available(self) -> bool:
        """Check if semgrep is installed and available in PATH."""
        try:
            process = await asyncio.create_subprocess_exec(
                "semgrep", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(process.communicate(), timeout=10)
            return process.returncode == 0
        except (FileNotFoundError, asyncio.TimeoutError):
            return False
