from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any

from reposage.repository.language import detect_language

try:
    from tree_sitter_languages import get_parser
except ImportError:  # pragma: no cover
    get_parser = None


DOCUMENT_LANGUAGES = {"markdown", "text", "yaml", "toml", "json", "ini"}
TREE_SITTER_LANGUAGE_MAP = {
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "tsx": "tsx",
    "java": "java",
    "go": "go",
    "rust": "rust",
    "c": "c",
    "cpp": "cpp",
    "csharp": "c_sharp",
    "ruby": "ruby",
    "php": "php",
}

SYMBOL_NODE_TYPES = {
    "python": {"function_definition": "function", "class_definition": "class"},
    "javascript": {
        "function_declaration": "function",
        "class_declaration": "class",
        "method_definition": "method",
    },
    "typescript": {
        "function_declaration": "function",
        "class_declaration": "class",
        "method_definition": "method",
        "interface_declaration": "interface",
        "type_alias_declaration": "type",
        "enum_declaration": "enum",
    },
    "tsx": {
        "function_declaration": "function",
        "class_declaration": "class",
        "method_definition": "method",
        "interface_declaration": "interface",
        "type_alias_declaration": "type",
        "enum_declaration": "enum",
    },
    "java": {
        "class_declaration": "class",
        "interface_declaration": "interface",
        "method_declaration": "method",
        "constructor_declaration": "method",
        "enum_declaration": "enum",
    },
    "go": {
        "function_declaration": "function",
        "method_declaration": "method",
        "type_declaration": "type",
    },
    "rust": {
        "function_item": "function",
        "struct_item": "struct",
        "enum_item": "enum",
        "trait_item": "trait",
        "impl_item": "impl",
    },
    "c": {"function_definition": "function", "struct_specifier": "struct", "enum_specifier": "enum"},
    "cpp": {
        "function_definition": "function",
        "class_specifier": "class",
        "struct_specifier": "struct",
        "namespace_definition": "namespace",
    },
    "csharp": {
        "class_declaration": "class",
        "method_declaration": "method",
        "struct_declaration": "struct",
        "interface_declaration": "interface",
        "enum_declaration": "enum",
    },
    "ruby": {"class": "class", "module": "module", "method": "method", "singleton_method": "method"},
    "php": {
        "function_definition": "function",
        "class_declaration": "class",
        "method_declaration": "method",
        "interface_declaration": "interface",
        "trait_declaration": "trait",
    },
}

HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")


@dataclass(slots=True)
class ChunkCandidate:
    path: str
    language: str | None
    chunk_type: str
    symbol_name: str | None
    start_line: int | None
    end_line: int | None
    content: str
    metadata: dict[str, Any]


@dataclass(slots=True)
class FileAnalysis:
    language: str | None
    chunks: list[ChunkCandidate]
    summary: str | None


def analyze_file(
    path: str,
    content: str,
    *,
    max_chars: int,
    overlap_lines: int,
) -> FileAnalysis:
    language = detect_language(path)
    syntax_chunks = extract_syntax_chunks(path, language, content)
    if syntax_chunks:
        chunks = split_large_chunks(syntax_chunks, max_chars=max_chars, overlap_lines=overlap_lines)
    elif language in DOCUMENT_LANGUAGES:
        chunks = split_large_chunks(
            extract_document_chunks(path, language, content),
            max_chars=max_chars,
            overlap_lines=overlap_lines,
        )
    else:
        chunks = fallback_window_chunks(path, language, content, max_chars=max_chars, overlap_lines=overlap_lines)
    return FileAnalysis(language=language, chunks=chunks, summary=build_file_summary(language, chunks))


def extract_syntax_chunks(path: str, language: str | None, content: str) -> list[ChunkCandidate]:
    parser_language = TREE_SITTER_LANGUAGE_MAP.get(language or "")
    if not parser_language or get_parser is None:
        return []

    try:
        parser = get_parser(parser_language)
        tree = parser.parse(content.encode("utf-8"))
    except Exception:
        return []

    source_bytes = content.encode("utf-8")
    node_types = SYMBOL_NODE_TYPES.get(parser_language, {})
    chunks: list[ChunkCandidate] = []

    def visit(node: Any) -> None:
        if node.type in node_types:
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            text = source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore").strip()
            if text:
                chunks.append(
                    ChunkCandidate(
                        path=path,
                        language=language,
                        chunk_type=node_types[node.type],
                        symbol_name=extract_symbol_name(node, source_bytes),
                        start_line=start_line,
                        end_line=end_line,
                        content=text,
                        metadata={"parser": parser_language, "node_type": node.type},
                    )
                )
        for child in getattr(node, "children", []):
            visit(child)

    visit(tree.root_node)
    return chunks


def extract_symbol_name(node: Any, source_bytes: bytes) -> str | None:
    for field_name in ("name", "declarator", "type", "body"):
        child = node.child_by_field_name(field_name)
        if child is None:
            continue
        text = _extract_identifier_text(child, source_bytes)
        if text:
            return text
    return _extract_identifier_text(node, source_bytes)


def _extract_identifier_text(node: Any, source_bytes: bytes) -> str | None:
    if "identifier" in node.type or node.type.endswith("name"):
        return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="ignore").strip()
    for child in getattr(node, "children", []):
        text = _extract_identifier_text(child, source_bytes)
        if text:
            return text
    return None


def extract_document_chunks(path: str, language: str | None, content: str) -> list[ChunkCandidate]:
    lines = content.splitlines()
    if not lines:
        return []

    chunks: list[ChunkCandidate] = []
    current_title = "Section"
    start_index = 0
    buffer: list[str] = []

    def flush(end_index: int) -> None:
        nonlocal buffer, start_index, current_title
        text = "\n".join(buffer).strip()
        if not text:
            return
        chunks.append(
            ChunkCandidate(
                path=path,
                language=language,
                chunk_type="doc_section",
                symbol_name=current_title,
                start_line=start_index + 1,
                end_line=end_index,
                content=text,
                metadata={"section": current_title},
            )
        )

    for index, line in enumerate(lines):
        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush(index)
            current_title = heading_match.group(2).strip()
            start_index = index
            buffer = [line]
            continue
        if not buffer:
            start_index = index
        buffer.append(line)

    flush(len(lines))
    return chunks


def fallback_window_chunks(
    path: str,
    language: str | None,
    content: str,
    *,
    max_chars: int,
    overlap_lines: int,
) -> list[ChunkCandidate]:
    lines = content.splitlines()
    if not lines:
        return []

    chunks: list[ChunkCandidate] = []
    index = 0
    window_index = 0
    while index < len(lines):
        current_lines: list[str] = []
        current_length = 0
        start_index = index
        while index < len(lines):
            candidate = lines[index]
            if current_lines and current_length + len(candidate) + 1 > max_chars:
                break
            current_lines.append(candidate)
            current_length += len(candidate) + 1
            index += 1
        if not current_lines:
            current_lines.append(lines[index])
            index += 1
        end_index = start_index + len(current_lines)
        chunks.append(
            ChunkCandidate(
                path=path,
                language=language,
                chunk_type="fallback_text",
                symbol_name=None,
                start_line=start_index + 1,
                end_line=end_index,
                content="\n".join(current_lines).strip(),
                metadata={"window_index": window_index},
            )
        )
        window_index += 1
        if end_index >= len(lines):
            index = end_index
        else:
            index = max(end_index - overlap_lines, start_index + 1)
    return [chunk for chunk in chunks if chunk.content]


def split_large_chunks(
    chunks: list[ChunkCandidate], *, max_chars: int, overlap_lines: int
) -> list[ChunkCandidate]:
    results: list[ChunkCandidate] = []
    for chunk in chunks:
        if len(chunk.content) <= max_chars:
            results.append(chunk)
            continue

        lines = chunk.content.splitlines()
        pointer = 0
        part_index = 0
        while pointer < len(lines):
            collected: list[str] = []
            collected_length = 0
            start_pointer = pointer
            while pointer < len(lines):
                line = lines[pointer]
                if collected and collected_length + len(line) + 1 > max_chars:
                    break
                collected.append(line)
                collected_length += len(line) + 1
                pointer += 1

            if not collected:
                collected.append(lines[pointer])
                pointer += 1

            part_start = (chunk.start_line or 1) + start_pointer
            part_end = part_start + len(collected) - 1
            metadata = dict(chunk.metadata)
            metadata["part_index"] = part_index
            results.append(
                replace(
                    chunk,
                    start_line=part_start,
                    end_line=part_end,
                    content="\n".join(collected).strip(),
                    metadata=metadata,
                )
            )
            part_index += 1
            if pointer < len(lines):
                pointer = max(pointer - overlap_lines, start_pointer + 1)
    return [chunk for chunk in results if chunk.content]


def build_file_summary(language: str | None, chunks: list[ChunkCandidate]) -> str | None:
    if not chunks:
        return None
    symbols = [chunk.symbol_name for chunk in chunks if chunk.symbol_name][:5]
    chunk_types = sorted({chunk.chunk_type for chunk in chunks})
    fragments = []
    if language:
        fragments.append(f"{language} file")
    if chunk_types:
        fragments.append(f"contains {', '.join(chunk_types)} chunks")
    if symbols:
        fragments.append(f"main symbols: {', '.join(symbols)}")
    return "; ".join(fragments)
