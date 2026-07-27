"""Dead Code Detector — graph-based detection of unreferenced code.

Uses the ProjectModel graph to identify:
- Files not imported by any other file
- Classes not instantiated or extended
- Functions/methods without external references
- Exported components never imported

Assigns confidence levels:
- HIGH: zero incoming references (definitely unused)
- MEDIUM: only referenced in test files
- LOW: dynamic usage possible (framework annotations, reflection)

Requirement: V2-4.1, V2-4.2
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from src.domain.models.project_model import (
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeType,
    ProjectModel,
)

logger = logging.getLogger(__name__)


class Confidence(str, Enum):
    """Confidence level for dead code candidates."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DeadCodeCandidate:
    """A single dead code finding."""
    node_id: str
    node_type: str
    name: str
    file_path: str
    confidence: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "file_path": self.file_path,
            "confidence": self.confidence,
            "reason": self.reason,
        }


# Framework annotations that auto-wire classes (not imported explicitly)
FRAMEWORK_ANNOTATIONS = {
    # Java Spring
    "@Component", "@Service", "@Repository", "@Controller",
    "@RestController", "@Configuration", "@Bean", "@Entity",
    "@Autowired", "@EventListener",
    # Angular
    "@Injectable", "@Component", "@NgModule", "@Pipe", "@Directive",
    # NestJS
    "@Module", "@Injectable", "@Controller",
}

# Test-related path patterns
TEST_PATTERNS = {"test", "tests", "spec", "__tests__", "testing", "Test."}


class DeadCodeDetector:
    """Detects unreferenced code using the ProjectModel dependency graph.

    Algorithm:
    1. Build an incoming-edges map for all nodes.
    2. For each node, count incoming edges (references from other code).
    3. Nodes with zero incoming edges are dead code candidates.
    4. Apply confidence levels based on context.
    5. Filter out framework-special-case nodes (annotations).
    """

    def detect(self, project_model: ProjectModel) -> list[dict]:
        """Run dead code detection on the project model.

        Args:
            project_model: The fully-built project model with nodes and edges.

        Returns:
            List of DeadCodeCandidate dicts sorted by confidence (high first).
        """
        if not project_model.nodes:
            return []

        # Build incoming reference map: node_id → list of source nodes
        incoming_map: dict[str, list[str]] = {
            str(n.id): [] for n in project_model.nodes
        }

        for edge in project_model.edges:
            target_id = str(edge.target_node_id)
            source_id = str(edge.source_node_id)
            if target_id in incoming_map:
                incoming_map[target_id].append(source_id)

        # Build node lookup
        node_map: dict[str, GraphNode] = {
            str(n.id): n for n in project_model.nodes
        }

        candidates: list[DeadCodeCandidate] = []

        for node in project_model.nodes:
            node_id = str(node.id)
            incoming_refs = incoming_map.get(node_id, [])

            # Skip entry points and config files
            if self._is_entry_point(node):
                continue

            # Zero references — potential dead code
            if len(incoming_refs) == 0:
                confidence = self._assess_confidence(node, incoming_refs, node_map)
                reason = self._build_reason(node, incoming_refs, node_map)

                candidates.append(DeadCodeCandidate(
                    node_id=node_id,
                    node_type=node.node_type.value if hasattr(node.node_type, 'value') else str(node.node_type),
                    name=node.name,
                    file_path=node.file_path or "",
                    confidence=confidence.value,
                    reason=reason,
                ))

            # Only referenced from test files — medium confidence
            elif self._only_test_references(incoming_refs, node_map):
                candidates.append(DeadCodeCandidate(
                    node_id=node_id,
                    node_type=node.node_type.value if hasattr(node.node_type, 'value') else str(node.node_type),
                    name=node.name,
                    file_path=node.file_path or "",
                    confidence=Confidence.MEDIUM.value,
                    reason="Only referenced from test files — may be dead production code",
                ))

        # Sort: high confidence first, then by name
        candidates.sort(key=lambda c: (
            0 if c.confidence == "high" else 1 if c.confidence == "medium" else 2,
            c.name,
        ))

        logger.info(
            "Dead code detection complete — %d candidates found (high=%d, medium=%d, low=%d)",
            len(candidates),
            sum(1 for c in candidates if c.confidence == "high"),
            sum(1 for c in candidates if c.confidence == "medium"),
            sum(1 for c in candidates if c.confidence == "low"),
        )

        return [c.to_dict() for c in candidates]

    def _is_entry_point(self, node: GraphNode) -> bool:
        """Check if a node is an application entry point (should have no incoming refs)."""
        name_lower = node.name.lower()
        file_lower = (node.file_path or "").lower()

        # Main entry points
        if name_lower in ("main", "app", "application", "index", "server"):
            return True

        # Config/setup files
        if any(p in file_lower for p in (
            "config", "application.yml", "application.properties",
            "pom.xml", "build.gradle", "package.json", "tsconfig",
            "__init__", "setup.py", "settings",
        )):
            return True

        # Test files (don't flag tests as dead code)
        if any(p in file_lower for p in TEST_PATTERNS):
            return True

        return False

    def _assess_confidence(
        self,
        node: GraphNode,
        incoming_refs: list[str],
        node_map: dict[str, GraphNode],
    ) -> Confidence:
        """Determine confidence level for a zero-reference node."""
        metadata = node.metadata or {}

        # Check for framework annotations → LOW confidence (auto-wired)
        modifiers = str(metadata.get("modifiers", ""))
        annotations = str(metadata.get("annotations", ""))
        combined = modifiers + " " + annotations

        if any(ann in combined for ann in FRAMEWORK_ANNOTATIONS):
            return Confidence.LOW

        # Classes and modules with no references → HIGH
        node_type = node.node_type.value if hasattr(node.node_type, 'value') else str(node.node_type)
        if node_type in ("class", "module", "file"):
            return Confidence.HIGH

        # Functions/methods → HIGH (unless they're overrides or interface implementations)
        if node_type in ("function", "method"):
            # Check for override patterns
            if metadata.get("is_override") or metadata.get("is_interface_impl"):
                return Confidence.LOW
            return Confidence.HIGH

        return Confidence.MEDIUM

    def _only_test_references(
        self,
        incoming_refs: list[str],
        node_map: dict[str, GraphNode],
    ) -> bool:
        """Check if all incoming references come from test files."""
        if not incoming_refs:
            return False

        for ref_id in incoming_refs:
            ref_node = node_map.get(ref_id)
            if ref_node is None:
                continue
            ref_file = (ref_node.file_path or "").lower()
            if not any(p in ref_file for p in TEST_PATTERNS):
                return False  # At least one non-test reference

        return True

    def _build_reason(
        self,
        node: GraphNode,
        incoming_refs: list[str],
        node_map: dict[str, GraphNode],
    ) -> str:
        """Generate a human-readable reason for the dead code finding."""
        node_type = node.node_type.value if hasattr(node.node_type, 'value') else str(node.node_type)

        if node_type == "file":
            return "File is not imported by any other file in the project"
        elif node_type == "class":
            return "Class is never instantiated, extended, or referenced"
        elif node_type in ("function", "method"):
            return "Function/method has no external callers"
        elif node_type == "module":
            return "Module has no incoming dependencies"
        else:
            return "No incoming references found in the dependency graph"
