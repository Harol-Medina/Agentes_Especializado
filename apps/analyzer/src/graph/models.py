"""Internal dataclasses for the parsing/graph pipeline.

These are intermediate structures produced by the Tree-sitter parser and
consumed by the GraphBuilder to construct the final ProjectModel.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedEntity:
    """A single code entity extracted from an AST (class, function, method, interface)."""

    name: str
    entity_type: str  # "class" | "function" | "method" | "interface"
    file_path: str
    start_line: int
    end_line: int
    metadata: dict = field(default_factory=dict)
    # metadata may include: parent_class, parameters, return_type, modifiers, etc.


@dataclass
class ParsedFile:
    """Aggregated parse results for a single source file."""

    file_path: str
    language: str  # "java" | "typescript" | "javascript"
    entities: list[ParsedEntity] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)  # Fully-qualified import strings
    loc: int = 0  # Lines of code (non-blank, non-comment approximation)
