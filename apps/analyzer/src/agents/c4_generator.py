"""C4 Diagram Generator — produces Mermaid syntax for Context, Container, and Component diagrams.

Generates three levels of C4 architecture diagrams from the ProjectModel and ArchitectureReport:
- Context: system + external actors/systems
- Container: apps, databases, external services
- Component: modules within each container

Output is Mermaid flowchart syntax ready for frontend rendering.

Requirement: V2-9.1
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from src.domain.models.project_model import NodeType, ProjectModel

logger = logging.getLogger(__name__)


@dataclass
class C4Diagrams:
    """Collection of C4 diagrams in Mermaid syntax."""
    context: str = ""
    container: str = ""
    component: str = ""

    def to_dict(self) -> dict:
        return {
            "context": self.context,
            "container": self.container,
            "component": self.component,
        }


class C4Generator:
    """Generates C4 architecture diagrams from project analysis data.

    Uses the ProjectModel graph and ArchitectureReport to infer:
    - External actors and systems (Context level)
    - Internal containers/services (Container level)
    - Module components within each container (Component level)
    """

    def generate(
        self,
        project_model: ProjectModel,
        architecture_report: dict | None = None,
    ) -> C4Diagrams:
        """Generate all three C4 diagram levels.

        Args:
            project_model: The analyzed project model with nodes and edges.
            architecture_report: Optional architecture analysis data.

        Returns:
            C4Diagrams with Mermaid syntax for each level.
        """
        diagrams = C4Diagrams(
            context=self._generate_context(project_model, architecture_report),
            container=self._generate_container(project_model, architecture_report),
            component=self._generate_component(project_model, architecture_report),
        )

        logger.info(
            "C4 diagrams generated — context=%d chars, container=%d chars, component=%d chars",
            len(diagrams.context),
            len(diagrams.container),
            len(diagrams.component),
        )

        return diagrams

    def _generate_context(self, project: ProjectModel, arch: dict | None) -> str:
        """Generate C4 Context diagram — system + external actors."""
        project_name = project.name or "System"
        language = project.language or "Unknown"
        framework = project.framework or ""

        # Identify external dependencies as external systems
        external_deps = [
            n for n in project.nodes
            if n.metadata.get("is_external")
        ]

        # Group external deps by category
        databases = []
        apis = []
        libraries = []

        for dep in external_deps:
            name = dep.name.lower()
            if any(db in name for db in ("postgres", "mysql", "mongo", "redis", "database", "sql")):
                databases.append(dep.name)
            elif any(api in name for api in ("http", "rest", "grpc", "api", "client", "service")):
                apis.append(dep.name)
            else:
                libraries.append(dep.name)

        lines = [
            "graph TB",
            f'    User["👤 User/Developer"]',
            f'    System["{project_name}<br/>{language} {framework}"]',
        ]

        # Add external systems
        if databases:
            lines.append(f'    DB[("🗄️ Database<br/>{", ".join(databases[:3])}")]')
            lines.append('    System --> DB')
        if apis:
            lines.append(f'    ExtAPI["🌐 External APIs<br/>{", ".join(apis[:3])}"]')
            lines.append('    System --> ExtAPI')

        lines.append('    User --> System')

        # Style
        lines.append('')
        lines.append('    classDef system fill:#F59E0B,stroke:#F59E0B,color:#080D18')
        lines.append('    classDef external fill:#1E2A3A,stroke:#1E2D45,color:#E2E8F0')
        lines.append('    classDef user fill:#06B6D4,stroke:#06B6D4,color:#080D18')
        lines.append('    class System system')
        lines.append('    class User user')
        lines.append('    class DB,ExtAPI external')

        return "\n".join(lines)

    def _generate_container(self, project: ProjectModel, arch: dict | None) -> str:
        """Generate C4 Container diagram — apps, stores, services."""
        project_name = project.name or "System"
        language = project.language or "Unknown"
        framework = project.framework or ""

        # Detect container-like structures from modules/packages
        modules = [n for n in project.nodes if n.node_type in (NodeType.MODULE, NodeType.PACKAGE)]

        # Try to infer containers from architecture report layers
        layers: list[dict] = []
        if arch and arch.get("layers"):
            layers = arch["layers"] if isinstance(arch["layers"], list) else []

        lines = [
            "graph TB",
            f'    subgraph boundary["{project_name}"]',
        ]

        if layers:
            # Use architecture layers as containers
            for i, layer in enumerate(layers[:6]):
                name = layer.get("name", f"Layer {i+1}") if isinstance(layer, dict) else str(layer)
                safe_id = f"L{i}"
                responsibility = layer.get("responsibility", "") if isinstance(layer, dict) else ""
                lines.append(f'        {safe_id}["{name}<br/><small>{responsibility[:40]}</small>"]')
        elif modules:
            # Fall back to top-level modules
            for i, mod in enumerate(modules[:8]):
                safe_id = f"M{i}"
                lines.append(f'        {safe_id}["{mod.name}<br/><small>{mod.loc} LOC</small>"]')

        lines.append('    end')
        lines.append('')

        # External dependencies
        lines.append(f'    User["👤 User"] --> boundary')

        # DB if detected
        external_deps = [n.name for n in project.nodes if n.metadata.get("is_external")]
        db_deps = [d for d in external_deps if any(k in d.lower() for k in ("postgres", "mysql", "mongo", "redis"))]
        if db_deps:
            lines.append(f'    boundary --> DB[("🗄️ {db_deps[0]}")]')

        # Styles
        lines.append('')
        lines.append('    classDef container fill:#0F1624,stroke:#1E2D45,color:#E2E8F0')
        lines.append('    classDef user fill:#06B6D4,stroke:#06B6D4,color:#080D18')
        lines.append('    class User user')

        return "\n".join(lines)

    def _generate_component(self, project: ProjectModel, arch: dict | None) -> str:
        """Generate C4 Component diagram — modules within each container."""
        # Get all modules and their relationships
        modules = [n for n in project.nodes if n.node_type in (NodeType.MODULE, NodeType.PACKAGE)]
        classes = [n for n in project.nodes if n.node_type == NodeType.CLASS]

        if not modules and not classes:
            return "graph TB\n    Empty[\"No components detected\"]"

        lines = ["graph LR"]

        # Group classes by module (based on file path)
        module_classes: dict[str, list[str]] = {}
        for cls in classes[:30]:  # Limit to avoid huge diagrams
            # Infer module from file path
            module_name = "root"
            if cls.file_path:
                parts = cls.file_path.replace("\\", "/").split("/")
                # Find meaningful directory (skip src/, main/, java/, etc.)
                meaningful = [p for p in parts if p not in ("src", "main", "java", "com", "lib", "app")]
                if len(meaningful) >= 2:
                    module_name = meaningful[-2]  # Parent directory
                elif meaningful:
                    module_name = meaningful[0]

            if module_name not in module_classes:
                module_classes[module_name] = []
            module_classes[module_name].append(cls.name)

        # Generate subgraphs for each module
        for i, (mod_name, cls_list) in enumerate(list(module_classes.items())[:6]):
            safe_mod_id = f"mod{i}"
            lines.append(f'    subgraph {safe_mod_id}["{mod_name}"]')
            for j, cls_name in enumerate(cls_list[:5]):
                safe_cls_id = f"C{i}_{j}"
                lines.append(f'        {safe_cls_id}["{cls_name}"]')
            if len(cls_list) > 5:
                lines.append(f'        more{i}["... +{len(cls_list)-5} more"]')
            lines.append('    end')

        # Add some edges between modules based on the graph edges
        edge_pairs: set[tuple[str, str]] = set()
        for edge in project.edges[:20]:
            src_node = next((n for n in project.nodes if n.id == edge.source_node_id), None)
            tgt_node = next((n for n in project.nodes if n.id == edge.target_node_id), None)
            if src_node and tgt_node and src_node.file_path and tgt_node.file_path:
                src_mod = self._extract_module(src_node.file_path)
                tgt_mod = self._extract_module(tgt_node.file_path)
                if src_mod != tgt_mod:
                    edge_pairs.add((src_mod, tgt_mod))

        # Map module names to subgraph IDs
        mod_names = list(module_classes.keys())[:6]
        for src_mod, tgt_mod in list(edge_pairs)[:10]:
            if src_mod in mod_names and tgt_mod in mod_names:
                src_idx = mod_names.index(src_mod)
                tgt_idx = mod_names.index(tgt_mod)
                lines.append(f'    mod{src_idx} --> mod{tgt_idx}')

        # Styles
        lines.append('')
        lines.append('    classDef component fill:#0F1624,stroke:#1E2D45,color:#E2E8F0')

        return "\n".join(lines)

    @staticmethod
    def _extract_module(file_path: str) -> str:
        """Extract module name from file path."""
        parts = file_path.replace("\\", "/").split("/")
        meaningful = [p for p in parts if p not in ("src", "main", "java", "com", "lib", "app")]
        if len(meaningful) >= 2:
            return meaningful[-2]
        return meaningful[0] if meaningful else "root"
