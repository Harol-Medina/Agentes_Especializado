"""Tree-sitter based AST parser for Java, TypeScript, and JavaScript.

Uses tree-sitter v0.23+ API with language-specific packages.
Extracts classes, functions, methods, interfaces, and import statements.
"""

from __future__ import annotations

import logging
from pathlib import Path

import tree_sitter_java
import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Parser, Node

from src.graph.models import ParsedEntity, ParsedFile

logger = logging.getLogger(__name__)

# File extensions → language mapping
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".java": "java",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
}

# Languages initialized with tree-sitter v0.23+ API
_LANGUAGES: dict[str, Language] = {
    "java": Language(tree_sitter_java.language()),
    "typescript": Language(tree_sitter_typescript.language_typescript()),
    "javascript": Language(tree_sitter_javascript.language()),
}

# Node types to extract per language
_CLASS_TYPES: dict[str, set[str]] = {
    "java": {"class_declaration", "interface_declaration", "enum_declaration"},
    "typescript": {
        "class_declaration",
        "interface_declaration",
        "type_alias_declaration",
    },
    "javascript": {"class_declaration"},
}

_FUNCTION_TYPES: dict[str, set[str]] = {
    "java": {"method_declaration", "constructor_declaration"},
    "typescript": {
        "function_declaration",
        "method_definition",
        "arrow_function",
        "function",
    },
    "javascript": {
        "function_declaration",
        "method_definition",
        "arrow_function",
        "function",
    },
}

_IMPORT_TYPES: dict[str, set[str]] = {
    "java": {"import_declaration"},
    "typescript": {"import_statement"},
    "javascript": {"import_statement"},
}


class TreeSitterParser:
    """Parses source files using tree-sitter to extract code entities and imports."""

    def __init__(self) -> None:
        self._parsers: dict[str, Parser] = {}
        for lang_name, language in _LANGUAGES.items():
            parser = Parser(language)
            self._parsers[lang_name] = parser

    def parse_file(self, file_path: Path, language: str | None = None) -> ParsedFile | None:
        """Parse a single source file and extract entities/imports.

        Args:
            file_path: Path to the source file.
            language: Override language detection (if None, uses file extension).

        Returns:
            ParsedFile with extracted entities and imports, or None if the file
            cannot be parsed (unsupported language, read error, etc.).
        """
        if language is None:
            language = self._detect_language(file_path)

        if language is None or language not in self._parsers:
            return None

        try:
            source_bytes = file_path.read_bytes()
        except OSError as exc:
            logger.warning("Cannot read file %s: %s", file_path, exc)
            return None

        parser = self._parsers[language]
        tree = parser.parse(source_bytes)

        if tree is None or tree.root_node is None:
            return None

        root = tree.root_node

        entities = self._extract_entities(root, str(file_path), language)
        imports = self._extract_imports(root, language, source_bytes)
        loc = self._count_loc(source_bytes)

        return ParsedFile(
            file_path=str(file_path),
            language=language,
            entities=entities,
            imports=imports,
            loc=loc,
        )

    def _detect_language(self, file_path: Path) -> str | None:
        """Detect language from file extension."""
        return EXTENSION_LANGUAGE_MAP.get(file_path.suffix.lower())

    def _extract_entities(
        self, root: Node, file_path: str, language: str
    ) -> list[ParsedEntity]:
        """Walk the AST and extract class/function/method/interface entities."""
        entities: list[ParsedEntity] = []
        class_types = _CLASS_TYPES.get(language, set())
        function_types = _FUNCTION_TYPES.get(language, set())

        self._walk_node(root, entities, file_path, language, class_types, function_types)
        return entities

    def _walk_node(
        self,
        node: Node,
        entities: list[ParsedEntity],
        file_path: str,
        language: str,
        class_types: set[str],
        function_types: set[str],
        parent_class: str | None = None,
    ) -> None:
        """Recursively walk AST nodes and collect entities."""
        node_type = node.type

        if node_type in class_types:
            name = self._get_node_name(node, language)
            if name:
                entity_type = "interface" if "interface" in node_type else "class"
                entities.append(
                    ParsedEntity(
                        name=name,
                        entity_type=entity_type,
                        file_path=file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        metadata={"parent_class": parent_class} if parent_class else {},
                    )
                )
                # Recurse into class body for methods
                for child in node.children:
                    self._walk_node(
                        child,
                        entities,
                        file_path,
                        language,
                        class_types,
                        function_types,
                        parent_class=name,
                    )
                return  # Don't double-process children

        if node_type in function_types:
            name = self._get_function_name(node, language)
            if name:
                entity_type = "method" if parent_class else "function"
                entities.append(
                    ParsedEntity(
                        name=name,
                        entity_type=entity_type,
                        file_path=file_path,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        metadata={"parent_class": parent_class} if parent_class else {},
                    )
                )
                return  # Don't recurse into function bodies for nested functions

        # Recurse into children for top-level and intermediate nodes
        for child in node.children:
            self._walk_node(
                child, entities, file_path, language, class_types, function_types, parent_class
            )

    def _get_node_name(self, node: Node, language: str) -> str | None:
        """Extract name from a class/interface declaration node."""
        for child in node.children:
            if child.type == "identifier" or child.type == "type_identifier":
                return child.text.decode("utf-8") if child.text else None
        return None

    def _get_function_name(self, node: Node, language: str) -> str | None:
        """Extract name from a function/method declaration node.

        For arrow functions assigned to variables (const foo = () => {}),
        this requires looking at the parent (variable_declarator).
        """
        # Direct name child (function_declaration, method_definition)
        for child in node.children:
            if child.type in ("identifier", "property_identifier"):
                return child.text.decode("utf-8") if child.text else None

        # Arrow functions — name is in parent variable_declarator
        if node.type == "arrow_function" and node.parent is not None:
            parent = node.parent
            if parent.type == "variable_declarator":
                for child in parent.children:
                    if child.type == "identifier":
                        return child.text.decode("utf-8") if child.text else None

        return None

    def _extract_imports(
        self, root: Node, language: str, source_bytes: bytes
    ) -> list[str]:
        """Extract import statements from the AST."""
        imports: list[str] = []
        import_types = _IMPORT_TYPES.get(language, set())

        for child in root.children:
            if child.type in import_types:
                import_text = self._get_import_path(child, language, source_bytes)
                if import_text:
                    imports.append(import_text)

        return imports

    def _get_import_path(
        self, node: Node, language: str, source_bytes: bytes
    ) -> str | None:
        """Extract the import path/module from an import node."""
        if language == "java":
            # Java: import com.example.Foo; → "com.example.Foo"
            # The scoped_identifier or identifier child has the full path
            for child in node.children:
                if child.type in ("scoped_identifier", "identifier"):
                    return child.text.decode("utf-8") if child.text else None
            # Fallback: extract the full text minus 'import' and ';'
            text = node.text.decode("utf-8").strip() if node.text else ""
            text = text.removeprefix("import").removesuffix(";").strip()
            if text.startswith("static "):
                text = text.removeprefix("static ").strip()
            return text if text else None

        # TypeScript/JavaScript: import ... from 'module' → "module"
        for child in node.children:
            if child.type == "string" or child.type == "string_fragment":
                raw = child.text.decode("utf-8") if child.text else ""
                return raw.strip("'\"")

        # Look for the source in nested children
        source_node = self._find_child_type(node, "string")
        if source_node and source_node.text:
            return source_node.text.decode("utf-8").strip("'\"")

        return None

    def _find_child_type(self, node: Node, target_type: str) -> Node | None:
        """Find the first descendant of a given type (BFS)."""
        queue = list(node.children)
        while queue:
            current = queue.pop(0)
            if current.type == target_type:
                return current
            queue.extend(current.children)
        return None

    def _count_loc(self, source_bytes: bytes) -> int:
        """Count non-empty lines as a LOC approximation."""
        try:
            text = source_bytes.decode("utf-8", errors="replace")
        except Exception:
            return 0
        return sum(1 for line in text.splitlines() if line.strip())
