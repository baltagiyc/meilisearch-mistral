"""Parse a PDF with Docling: extract full document as markdown (text + tables + structure)."""

import time
from pathlib import Path

from docling.document_converter import DocumentConverter

LOG_PREFIX = "[parse_pdf]"


def parse_pdf(path: str | Path) -> tuple[str, str]:
    """
    Parse a PDF file with Docling. Returns (source_file_stem, full_markdown_text).
    """
    path = Path(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file, got {path.suffix}")

    print(f"{LOG_PREFIX} Input: {path.name} ({path.stat().st_size / 1024:.1f} KB)")
    print(f"{LOG_PREFIX} Initializing Docling (first run may download models)...")
    t0 = time.perf_counter()
    converter = DocumentConverter()
    print(f"{LOG_PREFIX} Converting PDF to markdown (layout + tables + text)...")
    result = converter.convert(path)
    doc = result.document
    full_md = doc.export_to_markdown() or ""
    elapsed = time.perf_counter() - t0
    print(f"{LOG_PREFIX} Done in {elapsed:.1f}s — {len(full_md)} chars extracted")
    return path.stem, full_md
