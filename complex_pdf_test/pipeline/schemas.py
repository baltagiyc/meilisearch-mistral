"""Data shapes for the complex PDF pipeline: raw elements, chunks, and Meilisearch documents."""

from dataclasses import dataclass
from typing import Any


@dataclass
class RawElement:
    """One piece of content extracted from the PDF (paragraph, table, caption, etc.)."""
    text: str
    page: int | None
    element_type: str  # "text" | "table" | "figure_caption" | "title" | "section_header"
    source_file: str


@dataclass
class Chunk:
    """One retrieval unit to be indexed (may span several raw elements)."""
    chunk_id: str
    doc_id: str
    chunk_text: str
    page: int | None
    element_type: str
    source_file: str
    section_heading: str | None = None


def chunk_to_meilisearch_doc(chunk: Chunk) -> dict[str, Any]:
    """Turn a Chunk into a JSON document for Meilisearch (and for output JSON)."""
    return {
        "id": chunk.chunk_id,
        "doc_id": chunk.doc_id,
        "chunk_text": chunk.chunk_text,
        "title": chunk.section_heading or "",
        "page": chunk.page,
        "element_type": chunk.element_type,
        "source_file": chunk.source_file,
    }
