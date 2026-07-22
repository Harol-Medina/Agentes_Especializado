"""Graph builder — constructs a ProjectModel from parsed AST data.

Creates nodes (packages, files, classes, functions) and edges (imports,
inheritance) with metadata (LOC, basic complexity).
"""

from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath
from typing import Optional
from uuid import uuid4

from src.domain.models.project_model import (
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeType,
    ProjectModel,
)
from src.graph.models import ParsedEntity, ParsedFile

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Constructs a ProjectModel graph from parsed AST data."""

    def build(
        self,
        parsed_files: list[ParsedFile],
        language: str,
        framework: str,
        repo_url: str = "",
        repo_path: str = "",
    ) -> ProjectModel:
        """Build the complete project graph.

        Steps:
        1. Create package nodes from directory structure.
        2. Create file nodes for all parsed source files.
        3. Create class/function nodes from parsed entities.
        4. Create edges from import statements and class hierarchies.
        5. Compute aggregate metadata.

        Args:
            parsed_files: List of parsed source files with entities/imports.
            language: Detected primary language.
            framework: Detected framework.
            repo_url: Original repository URL.
            repo_path: Local path where the repo was cloned.

        Returns:
            A fully populated ProjectModel.
        """
        model = ProjectModel(
            name=self._extract_project_name(repo_url, repo_path),
            repo_url=repo_url,
            language=language,
            framework=framework,
        )

        # Track nodes by qualified name for edge resolution
        node_by_name: dict[str, GraphNode] = {}
        file_nodes: dict[str, GraphNode] = {}

        # 1. Create package nodes from directory structure
        package_nodes = self._build_package_nodes(parsed_files, repo_path)
        for pkg_node in package_nodes.values():
            model.nodes.append(pkg_node)
            node_by_name[pkg_node.qualified_name or pkg_node.name] = pkg_node

        # 2. Create file nodes
        for pf in parsed_files:
            rel_path = self._relative_path(pf.file_path, repo_path)
            file_node = GraphNode(
                id=uuid4(),
                node_type=NodeType.FILE,
                name=Path(pf.file_path).name,
                qualified_name=rel_path,
                file_path=rel_path,
                loc=pf.loc,
                complexity=1,
            )
            model.nodes.append(file_node)
            file_nodes[rel_path] = file_node
            node_by_name[rel_path] = file_node

        # 3. Create entity nodes (classes, functions, methods, interfaces)
        for pf in parsed_files:
            rel_path = self._relative_path(pf.file_path, repo_path)
            for entity in pf.entities:
                entity_node = self._create_entity_node(entity, rel_path)
                model.nodes.append(entity_node)

                qualified = f"{rel_path}::{entity.name}"
                node_by_name[qualified] = entity_node
                # Also register by simple name for cross-file resolution
                if entity.name not in node_by_name:
                    node_by_name[entity.name] = entity_node

        # 4. Create edges from imports
        import_edges = self._build_import_edges(
            parsed_files, file_nodes, node_by_name, repo_path
        )
        model.edges.extend(import_edges)

        # 5. Create edges from inheritance (class extends/implements)
        inheritance_edges = self._build_inheritance_edges(parsed_files, node_by_name, repo_path)
        model.edges.extend(inheritance_edges)

        # 6. Aggregate metadata
        model.total_files = len(parsed_files)
        model.total_loc = sum(pf.loc for pf in parsed_files)

        logger.info(
            "Graph built — nodes=%d, edges=%d, files=%d, loc=%d",
            len(model.nodes),
            len(model.edges),
            model.total_files,
            model.total_loc,
        )

        return model

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_project_name(self, repo_url: str, repo_path: str) -> str:
        """Extract a human-friendly project name from URL or path."""
        if repo_url:
            # https://github.com/owner/repo → "repo"
            parts = repo_url.rstrip("/").split("/")
            if len(parts) >= 2:
                return parts[-1].removesuffix(".git")
        if repo_path:
            return Path(repo_path).name
        return "unknown-project"

    def _relative_path(self, file_path: str, repo_path: str) -> str:
        """Compute relative path from repo root."""
        if not repo_path:
            return file_path
        try:
            return str(PurePosixPath(Path(file_path).relative_to(Path(repo_path))))
        except ValueError:
            return file_path

    def _build_package_nodes(
        self, parsed_files: list[ParsedFile], repo_path: str
    ) -> dict[str, GraphNode]:
        """Create package/module nodes from directory structure."""
        packages: dict[str, GraphNode] = {}

        for pf in parsed_files:
            rel_path = self._relative_path(pf.file_path, repo_path)
            parts = PurePosixPath(rel_path).parts

            # Create nodes for each directory level (package grouping)
            for i in range(1, len(parts)):
                pkg_path = "/".join(parts[:i])
                if pkg_path not in packages:
                    packages[pkg_path] = GraphNode(
                        id=uuid4(),
                        node_type=NodeType.PACKAGE,
                        name=parts[i - 1],
                        qualified_name=pkg_path,
                        file_path=pkg_path,
                        loc=0,
                        complexity=1,
                    )

        return packages

    def _create_entity_node(self, entity: ParsedEntity, file_rel_path: str) -> GraphNode:
        """Create a GraphNode from a ParsedEntity."""
        # Map entity_type to NodeType
        type_map = {
            "class": NodeType.CLASS,
            "interface": NodeType.CLASS,
            "function": NodeType.FUNCTION,
            "method": NodeType.FUNCTION,
        }
        node_type = type_map.get(entity.entity_type, NodeType.FUNCTION)

        # Basic complexity: lines of code as proxy
        line_span = max(1, entity.end_line - entity.start_line + 1)
        complexity = self._estimate_complexity(line_span)

        return GraphNode(
            id=uuid4(),
            node_type=node_type,
            name=entity.name,
            qualified_name=f"{file_rel_path}::{entity.name}",
            file_path=file_rel_path,
            loc=line_span,
            complexity=complexity,
            metadata={
                "entity_type": entity.entity_type,
                "start_line": entity.start_line,
                "end_line": entity.end_line,
                **(entity.metadata or {}),
            },
        )

    def _estimate_complexity(self, line_span: int) -> int:
        """Estimate cyclomatic complexity from line count (rough heuristic).

        A proper implementation would count branches in the AST.
        For MVP, use a simple heuristic: ~1 decision per 10 lines.
        """
        return max(1, line_span // 10 + 1)

    def _build_import_edges(
        self,
        parsed_files: list[ParsedFile],
        file_nodes: dict[str, GraphNode],
        node_by_name: dict[str, GraphNode],
        repo_path: str,
    ) -> list[GraphEdge]:
        """Create import edges between files/entities."""
        edges: list[GraphEdge] = []

        for pf in parsed_files:
            source_rel = self._relative_path(pf.file_path, repo_path)
            source_node = file_nodes.get(source_rel)
            if source_node is None:
                continue

            for import_path in pf.imports:
                target_node = self._resolve_import(import_path, node_by_name)
                if target_node is not None and target_node.id != source_node.id:
                    edges.append(
                        GraphEdge(
                            id=uuid4(),
                            source_node_id=source_node.id,
                            target_node_id=target_node.id,
                            edge_type=EdgeType.IMPORT,
                            metadata={"import_path": import_path},
                        )
                    )

        return edges

    def _resolve_import(
        self, import_path: str, node_by_name: dict[str, GraphNode]
    ) -> Optional[GraphNode]:
        """Attempt to resolve an import path to an existing node.

        Tries several strategies:
        1. Direct match by qualified name.
        2. Match by last segment (class/module name).
        3. Match by converting package notation to path.
        """
        # Direct match
        if import_path in node_by_name:
            return node_by_name[import_path]

        # Last segment (e.g., "com.example.Foo" → "Foo")
        last_segment = import_path.rsplit(".", 1)[-1] if "." in import_path else import_path
        last_segment = last_segment.rsplit("/", 1)[-1] if "/" in last_segment else last_segment
        if last_segment in node_by_name:
            return node_by_name[last_segment]

        # Convert dotted path to slash path (Java: com.example.Foo → com/example/Foo)
        slash_path = import_path.replace(".", "/")
        if slash_path in node_by_name:
            return node_by_name[slash_path]

        return None

    def _build_inheritance_edges(
        self,
        parsed_files: list[ParsedFile],
        node_by_name: dict[str, GraphNode],
        repo_path: str,
    ) -> list[GraphEdge]:
        """Create inheritance edges from class extends/implements metadata.

        This requires parent_class information stored in entity metadata.
        For MVP, we detect simple same-file parent_class relationships.
        """
        edges: list[GraphEdge] = []

        for pf in parsed_files:
            rel_path = self._relative_path(pf.file_path, repo_path)
            for entity in pf.entities:
                if entity.entity_type in ("method",) and entity.metadata.get("parent_class"):
                    # Method belongs to a class → composition edge
                    parent_name = entity.metadata["parent_class"]
                    child_qualified = f"{rel_path}::{entity.name}"
                    parent_qualified = f"{rel_path}::{parent_name}"

                    child_node = node_by_name.get(child_qualified)
                    parent_node = node_by_name.get(parent_qualified)

                    if child_node and parent_node:
                        edges.append(
                            GraphEdge(
                                id=uuid4(),
                                source_node_id=parent_node.id,
                                target_node_id=child_node.id,
                                edge_type=EdgeType.COMPOSITION,
                                metadata={},
                            )
                        )

        return edges
