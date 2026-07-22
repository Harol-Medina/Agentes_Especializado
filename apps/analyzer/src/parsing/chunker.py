"""AST-aware code chunker.

Splits parsed source files into semantic chunks at function/method boundaries,
preserving context headers for each chunk. Suitable for embedding generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src.graph.models import ParsedFile, ParsedEntity


@dataclass
class CodeChunk:
    """A chunk of code with context for embedding and retrieval."""

    text: str
    chunk_type: str  # function | method | class | file
    file_path: str
    module_name: str
    function_name: Optional[str] = None
    start_line: int = 0
    end_line: int = 0
    metadata: dict = field(default_factory=dict)


# Thresholds
_MIN_CHUNK_SIZE = 200  # chars — below this, merge with adjacent
_MAX_CHUNK_SIZE = 4000  # chars — above this, split at logical boundaries


class ASTChunker:
    """Splits source code into semantic chunks using AST boundaries.

    Each function/method becomes one chunk with a context header.
    Small chunks (<200 chars) are merged with adjacent ones.
    Large chunks (>4000 chars) are split preserving context headers.
    """

    def chunk_parsed_files(self, parsed_files: list[ParsedFile]) -> list[CodeChunk]:
        """Chunk a list of parsed files into CodeChunks.

        Each function/method in each file becomes a separate chunk with a
        context header: ``// File: {path} | Class: {class}``

        Args:
            parsed_files: List of ParsedFile objects from the AST parser.

        Returns:
            List of CodeChunk objects ready for embedding.
        """
        all_chunks: list[CodeChunk] = []

        for parsed_file in parsed_files:
            file_chunks = self._chunk_single_file(parsed_file)
            all_chunks.extend(file_chunks)

        return all_chunks

    def _chunk_single_file(self, parsed_file: ParsedFile) -> list[CodeChunk]:
        """Process a single ParsedFile into chunks.

        Strategy:
        1. Group entities by parent class (methods under their class).
        2. Each function/method = 1 chunk with context header.
        3. If no entities found, treat the whole file as one chunk.
        4. Merge small chunks with adjacent.
        5. Split large chunks respecting MAX_CHUNK_SIZE.
        """
        if not parsed_file.entities:
            # File with no parseable entities — treat as a single file-level chunk
            return [
                CodeChunk(
                    text=f"// File: {parsed_file.file_path}\n(file with no parseable entities)",
                    chunk_type="file",
                    file_path=parsed_file.file_path,
                    module_name=self._extract_module_name(parsed_file.file_path),
                    function_name=None,
                    start_line=0,
                    end_line=parsed_file.loc,
                    metadata={"language": parsed_file.language},
                )
            ]

        # Build chunks for each entity
        raw_chunks: list[CodeChunk] = []
        for entity in parsed_file.entities:
            chunk = self._entity_to_chunk(entity, parsed_file)
            raw_chunks.append(chunk)

        # Merge small chunks with adjacent
        merged = self._merge_small_chunks(raw_chunks)

        # Split oversized chunks
        final: list[CodeChunk] = []
        for chunk in merged:
            if len(chunk.text) > _MAX_CHUNK_SIZE:
                final.extend(self._split_large_chunk(chunk))
            else:
                final.append(chunk)

        return final

    def _entity_to_chunk(self, entity: ParsedEntity, parsed_file: ParsedFile) -> CodeChunk:
        """Convert a ParsedEntity into a CodeChunk with context header."""
        # Determine parent class from metadata
        parent_class = entity.metadata.get("parent_class", "")
        class_label = parent_class if parent_class else "(module-level)"

        # Build context header
        header = f"// File: {parsed_file.file_path} | Class: {class_label}"

        # Build the chunk text body from entity metadata
        # If we have source_code in metadata, use it; otherwise create a signature stub
        source_code = entity.metadata.get("source_code", "")
        if not source_code:
            # Fallback: construct a representative text from entity info
            source_code = self._build_entity_text(entity)

        text = f"{header}\n{source_code}"

        # Determine chunk type
        chunk_type = entity.entity_type  # "function" | "method" | "class"
        if chunk_type not in ("function", "method", "class", "file"):
            chunk_type = "function"  # Default for interface, etc.

        # Determine function name
        function_name: str | None = None
        if entity.entity_type in ("function", "method"):
            function_name = entity.name

        return CodeChunk(
            text=text,
            chunk_type=chunk_type,
            file_path=parsed_file.file_path,
            module_name=self._extract_module_name(parsed_file.file_path),
            function_name=function_name,
            start_line=entity.start_line,
            end_line=entity.end_line,
            metadata={
                "language": parsed_file.language,
                "entity_name": entity.name,
                "parent_class": parent_class,
            },
        )

    def _merge_small_chunks(self, chunks: list[CodeChunk]) -> list[CodeChunk]:
        """Merge chunks smaller than _MIN_CHUNK_SIZE with adjacent chunks."""
        if not chunks:
            return []

        merged: list[CodeChunk] = []
        buffer: CodeChunk | None = None

        for chunk in chunks:
            if buffer is None:
                buffer = chunk
                continue

            # If the buffer is too small, merge with current chunk
            if len(buffer.text) < _MIN_CHUNK_SIZE:
                buffer = self._combine_chunks(buffer, chunk)
            else:
                merged.append(buffer)
                buffer = chunk

        # Handle remaining buffer
        if buffer is not None:
            # If still too small and we have previous chunks, merge with last
            if len(buffer.text) < _MIN_CHUNK_SIZE and merged:
                merged[-1] = self._combine_chunks(merged[-1], buffer)
            else:
                merged.append(buffer)

        return merged

    def _combine_chunks(self, a: CodeChunk, b: CodeChunk) -> CodeChunk:
        """Combine two chunks into one, preserving metadata from both."""
        combined_text = f"{a.text}\n\n{b.text}"
        function_name = a.function_name or b.function_name

        return CodeChunk(
            text=combined_text,
            chunk_type=a.chunk_type,
            file_path=a.file_path,
            module_name=a.module_name,
            function_name=function_name,
            start_line=a.start_line,
            end_line=b.end_line,
            metadata={
                **a.metadata,
                "merged": True,
                "merged_entities": [
                    a.metadata.get("entity_name", ""),
                    b.metadata.get("entity_name", ""),
                ],
            },
        )

    def _split_large_chunk(self, chunk: CodeChunk) -> list[CodeChunk]:
        """Split a chunk that exceeds _MAX_CHUNK_SIZE into smaller parts.

        Splits at line boundaries, preserving the context header in each part.
        """
        lines = chunk.text.split("\n")
        # Extract header (first line starting with //)
        header = lines[0] if lines and lines[0].startswith("//") else ""
        body_lines = lines[1:] if header else lines

        parts: list[CodeChunk] = []
        current_lines: list[str] = []
        current_size = len(header) + 1  # account for header + newline

        for line in body_lines:
            line_size = len(line) + 1  # +1 for newline
            if current_size + line_size > _MAX_CHUNK_SIZE and current_lines:
                # Emit current part
                part_text = f"{header}\n" + "\n".join(current_lines) if header else "\n".join(current_lines)
                parts.append(
                    CodeChunk(
                        text=part_text,
                        chunk_type=chunk.chunk_type,
                        file_path=chunk.file_path,
                        module_name=chunk.module_name,
                        function_name=chunk.function_name,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        metadata={**chunk.metadata, "split_part": len(parts) + 1},
                    )
                )
                current_lines = []
                current_size = len(header) + 1

            current_lines.append(line)
            current_size += line_size

        # Emit remaining lines
        if current_lines:
            part_text = f"{header}\n" + "\n".join(current_lines) if header else "\n".join(current_lines)
            parts.append(
                CodeChunk(
                    text=part_text,
                    chunk_type=chunk.chunk_type,
                    file_path=chunk.file_path,
                    module_name=chunk.module_name,
                    function_name=chunk.function_name,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    metadata={**chunk.metadata, "split_part": len(parts) + 1},
                )
            )

        return parts if parts else [chunk]

    @staticmethod
    def _extract_module_name(file_path: str) -> str:
        """Extract a module name from a file path.

        Converts 'src/main/java/com/example/auth/AuthService.java'
        to 'com.example.auth' (Java) or the directory path for other languages.
        """
        # Normalize separators
        normalized = file_path.replace("\\", "/")

        # For Java: extract package from path
        if "/java/" in normalized:
            parts = normalized.split("/java/")[-1]
            # Remove filename, keep package path
            segments = parts.rsplit("/", 1)[0].split("/")
            return ".".join(segments) if segments else "default"

        # For TS/JS: use directory structure
        # Remove common prefixes
        for prefix in ("src/", "lib/", "app/"):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break

        # Remove filename, use directory as module name
        if "/" in normalized:
            return normalized.rsplit("/", 1)[0].replace("/", ".")
        return "root"

    @staticmethod
    def _build_entity_text(entity: ParsedEntity) -> str:
        """Build a representative text for an entity when source_code is unavailable."""
        params = entity.metadata.get("parameters", "")
        return_type = entity.metadata.get("return_type", "")
        modifiers = entity.metadata.get("modifiers", "")

        parts = []
        if modifiers:
            parts.append(modifiers)
        parts.append(f"{entity.entity_type} {entity.name}")
        if params:
            parts.append(f"({params})")
        if return_type:
            parts.append(f" -> {return_type}")

        signature = " ".join(parts)
        return f"{signature}\n  // lines {entity.start_line}-{entity.end_line}"
