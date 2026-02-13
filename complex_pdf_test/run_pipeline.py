"""
Run the full PDF pipeline: parse -> normalize -> chunk -> build -> output JSON.
Optionally load the resulting chunks into Meilisearch.
"""

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from complex_pdf_test.pipeline import parse_pdf, normalize_text, chunk_text, build_documents
from complex_pdf_test.load import load_chunks_into_meilisearch

LOG_PREFIX = "[run_pipeline]"


def run_pipeline(
    pdf_path: str | Path,
    *,
    output_json_path: str | Path | None = None,
    load_to_meilisearch: bool = False,
    max_chars: int = 1200,
    overlap_chars: int = 120,
) -> list[dict]:
    """
    Parse PDF, normalize, chunk, build documents. Optionally write JSON and/or load to Meilisearch.
    Returns the list of chunk documents (list of dicts).
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(pdf_path)

    total_start = time.perf_counter()
    print(f"{LOG_PREFIX} Starting pipeline for {pdf_path.name}")
    print(f"{LOG_PREFIX} --- Step 1/4: Parse PDF (Docling) ---")

    doc_id, raw_md = parse_pdf(pdf_path)

    print(f"{LOG_PREFIX} --- Step 2/4: Normalize text ---")
    normalized = normalize_text(raw_md)

    print(f"{LOG_PREFIX} --- Step 3/4: Chunk (max_chars={max_chars}, overlap={overlap_chars}) ---")
    chunks = chunk_text(
        normalized,
        doc_id=doc_id,
        source_file=pdf_path.name,
        max_chars=max_chars,
        overlap_chars=overlap_chars,
        split_on_headers=True,
    )
    documents = build_documents(chunks)
    print(f"{LOG_PREFIX} --- Step 4/4: Build documents → {len(documents)} docs ---")

    if output_json_path is not None:
        out = Path(output_json_path)
        print(f"{LOG_PREFIX} Writing JSON to {out}...")
        out.write_text(json.dumps(documents, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{LOG_PREFIX} Wrote {out.stat().st_size / 1024:.1f} KB")

    if load_to_meilisearch:
        print(f"{LOG_PREFIX} --- Load to Meilisearch (index pdf_chunks) ---")
        load_chunks_into_meilisearch(documents)

    elapsed = time.perf_counter() - total_start
    print(f"{LOG_PREFIX} Pipeline finished in {elapsed:.1f}s total")
    return documents


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="PDF pipeline: parse, chunk, output JSON.")
    parser.add_argument("pdf", type=Path, help="Path to PDF file")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output JSON path (default: next to PDF)")
    parser.add_argument("--load", action="store_true", help="Load chunks into Meilisearch after building")
    parser.add_argument("--max-chars", type=int, default=1200, help="Max characters per chunk")
    parser.add_argument("--overlap", type=int, default=120, help="Overlap between chunks")
    args = parser.parse_args()

    output_path = args.output
    if output_path is None:
        output_path = args.pdf.with_suffix(".chunks.json")

    docs = run_pipeline(
        args.pdf,
        output_json_path=output_path,
        load_to_meilisearch=args.load,
        max_chars=args.max_chars,
        overlap_chars=args.overlap,
    )
    print(f"Chunks: {len(docs)}")
    print(f"Output: {output_path}")
    if args.load:
        print("Loaded into Meilisearch index 'pdf_chunks'.")


if __name__ == "__main__":
    main()
