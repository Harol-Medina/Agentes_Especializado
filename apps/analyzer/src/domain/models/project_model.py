"""Graph nodes, edges, and project metadata domain models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class NodeType(str, Enum):
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    MODULE = "module"
    PACKAGE = "package"


class EdgeType(str, Enum):
    IMPORT = "import"
    INHERITANCE = "inheritance"
    USAGE = "usage"
    COMPOSITION = "composition"


@dataclass
class GraphNode:
    """A node in the project dependency graph."""

    id: UUID = field(default_factory=uuid4)
    node_type: NodeType = NodeType.FILE
    name: str = ""
    qualified_name: Optional[str] = None
    file_path: Optional[str] = None
    loc: int = 0
    complexity: int = 1
    last_modified: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    """A directed edge in the project dependency graph."""

    id: UUID = field(default_factory=uuid4)
    source_node_id: UUID = field(default_factory=uuid4)
    target_node_id: UUID = field(default_factory=uuid4)
    edge_type: EdgeType = EdgeType.IMPORT
    metadata: dict = field(default_factory=dict)


@dataclass
class ProjectModel:
    """
    In-memory representation of an analysed project.

    Holds the complete directed graph (nodes + edges) plus aggregate
    statistics computed during the Repository_Agent phase.
    """

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    repo_url: str = ""
    language: Optional[str] = None
    framework: Optional[str] = None
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    total_files: int = 0
    total_loc: int = 0
