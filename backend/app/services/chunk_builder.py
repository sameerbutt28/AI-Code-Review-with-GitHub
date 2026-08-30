"""
=============================================================================
CHUNK BUILDER
FILE: app/services/chunk_builder.py

PURPOSE:
Split a repository's source files into smaller CHUNKS so each chunk can be
sent to the LLM separately (fits token limits, better coverage).

HOW CHUNKING WORKS:
1. Collect all source files (already sorted by path)
2. Pack files into groups until size/file limits are reached
3. Each chunk becomes one LLM request
4. After ALL chunks finish, findings are merged and shown to the user

USED BY: step3_ai_analyzer.py
=============================================================================
"""

from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings
from app.services.step1_github_clone import get_relative_path, read_file_content


@dataclass
class CodeChunk:
    """One pack of source files sent to the LLM in a single request."""

    chunk_index: int          # 1-based index for display (Chunk 1 of N)
    total_chunks: int
    file_paths: list[str] = field(default_factory=list)
    code_text: str = ""
    char_count: int = 0

    @property
    def file_count(self) -> int:
        return len(self.file_paths)

    @property
    def label(self) -> str:
        return f"Chunk {self.chunk_index}/{self.total_chunks}"


def _format_file_block(rel_path: str, content: str) -> str:
    """Format one file with line numbers for the LLM."""
    numbered = "\n".join(
        f"{i:4d}| {line}" for i, line in enumerate(content.splitlines(), start=1)
    )
    return f"\n--- FILE: {rel_path} ---\n{numbered}\n"


def build_code_chunks(
    files: list[Path],
    repo_path: Path,
    max_chars: int | None = None,
    max_files: int | None = None,
) -> list[CodeChunk]:
    """
    Split source files into chunks.

    Rules:
    - Prefer packing whole files together
    - Start a new chunk when char or file limit would be exceeded
    - A single oversize file becomes its own (possibly truncated) chunk
    """
    max_chars = max_chars or settings.chunk_max_chars
    max_files = max_files or settings.chunk_max_files

    # First pass: build (rel_path, block) pairs
    prepared: list[tuple[str, str]] = []
    for file_path in files:
        content = read_file_content(file_path)
        if not content.strip():
            continue
        rel = get_relative_path(file_path, repo_path)
        block = _format_file_block(rel, content)

        # Truncate a single huge file so one chunk never overwhelms the model
        if len(block) > max_chars:
            block = block[: max_chars - 80] + "\n\n[truncated — file exceeds chunk size limit]\n"
        prepared.append((rel, block))

    if not prepared:
        return []

    # Pack into draft groups (index placeholder = 0 until we know total)
    draft_groups: list[tuple[list[str], str, int]] = []
    current_files: list[str] = []
    current_parts: list[str] = []
    current_size = 0

    def flush() -> None:
        nonlocal current_files, current_parts, current_size
        if not current_files:
            return
        text = "".join(current_parts)
        draft_groups.append((current_files, text, current_size))
        current_files = []
        current_parts = []
        current_size = 0

    for rel, block in prepared:
        would_exceed_chars = current_size > 0 and (current_size + len(block) > max_chars)
        would_exceed_files = current_size > 0 and (len(current_files) >= max_files)

        if would_exceed_chars or would_exceed_files:
            flush()

        current_files.append(rel)
        current_parts.append(block)
        current_size += len(block)

    flush()

    total = len(draft_groups)
    chunks: list[CodeChunk] = []
    for i, (paths, text, size) in enumerate(draft_groups, start=1):
        chunks.append(
            CodeChunk(
                chunk_index=i,
                total_chunks=total,
                file_paths=paths,
                code_text=text,
                char_count=size,
            )
        )
    return chunks


def patterns_for_chunk(pattern_findings: list[dict], chunk: CodeChunk) -> list[dict]:
    """Keep only pattern findings that belong to files in this chunk."""
    file_set = set(chunk.file_paths)
    return [p for p in pattern_findings if p.get("file_path") in file_set]
