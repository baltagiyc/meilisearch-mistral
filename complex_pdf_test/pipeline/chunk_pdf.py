"""Chunk normalized document text into retrieval-sized units with optional overlap."""

from .schemas import Chunk

LOG_PREFIX = "[chunk]"


def chunk_text(
    text: str,
    doc_id: str,
    source_file: str,
    *,
    max_chars: int = 1200,
    overlap_chars: int = 120,
    split_on_headers: bool = True,
) -> list[Chunk]:
    """
    Split text into chunks. Prefer splitting on markdown headers (## / ###) when
    split_on_headers is True; otherwise use fixed-size windows with overlap.
    """
    if not text.strip():
        print(f"{LOG_PREFIX} Empty text, no chunks.")
        return []

    chunks: list[Chunk] = []
    if split_on_headers:
        sections = _split_by_headers(text)
        print(f"{LOG_PREFIX} Split by headers: {len(sections)} sections (max_chars={max_chars}, overlap={overlap_chars})")
    else:
        sections = [text]
        print(f"{LOG_PREFIX} Single block (no header split), max_chars={max_chars}, overlap={overlap_chars}")

    chunk_index = 0
    for section in sections:
        section = section.strip()
        if not section:
            continue
        heading = _extract_leading_heading(section) if split_on_headers else None
        if len(section) <= max_chars:
            chunk_id = f"{doc_id}_c{chunk_index}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    chunk_text=section,
                    page=None,
                    element_type="text",
                    source_file=source_file,
                    section_heading=heading,
                )
            )
            chunk_index += 1
        else:
            for sub in _split_by_size(section, max_chars, overlap_chars):
                if not sub.strip():
                    continue
                chunk_id = f"{doc_id}_c{chunk_index}"
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        chunk_text=sub.strip(),
                        page=None,
                        element_type="text",
                        source_file=source_file,
                        section_heading=heading,
                    )
                )
                chunk_index += 1

    print(f"{LOG_PREFIX} Produced {len(chunks)} chunks for doc_id={doc_id}")
    return chunks


def _split_by_headers(text: str) -> list[str]:
    """Split markdown on ## or ### lines; each part keeps its header with following content."""
    import re
    # Split right before a line that starts with ## or ###
    parts = re.split(r"\n(?=#{2,3}\s)", text)
    return [p.strip() for p in parts if p.strip()]


def _extract_leading_heading(block: str) -> str | None:
    """Return first line if it looks like a markdown heading."""
    import re
    first = block.split("\n")[0].strip()
    m = re.match(r"^#{1,6}\s+(.+)$", first)
    return m.group(1).strip() if m else None


def _split_by_size(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split text into chunks of at most max_chars with overlap."""
    out: list[str] = []
    start = 0
    while start < len(text):
        end = start + max_chars
        if end >= len(text):
            out.append(text[start:])
            break
        # Try to break at sentence or newline
        chunk = text[start:end]
        for sep in ("\n\n", "\n", ". ", " "):
            last = chunk.rfind(sep)
            if last > max_chars // 2:
                end = start + last + len(sep)
                chunk = text[start:end]
                break
        out.append(chunk)
        start = end - overlap
    return out
