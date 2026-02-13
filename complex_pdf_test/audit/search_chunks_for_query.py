"""
Run the same search the chat uses (hybrid with Mistral embedder) and print the chunks returned.

Proxy for "which chunks were sent to the LLM".

Usage:
  python complex_pdf_test/audit/search_chunks_for_query.py "Ta question"
  python complex_pdf_test/audit/search_chunks_for_query.py "Ta question" --limit 10
"""

import sys
from pathlib import Path

# Project root (complex_pdf_test/audit/ -> parents[2])
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import meilisearch
from config import load_settings

PDF_INDEX = "pdf_chunks"
DEFAULT_LIMIT = 5


def main() -> None:
    limit = DEFAULT_LIMIT
    args = []
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
            i += 2
            continue
        args.append(sys.argv[i])
        i += 1
    query = " ".join(args).strip() if args else "architecture Mixtral paramètres"
    if not query:
        print("Usage: python search_chunks_for_query.py \"Your question\" [--limit N]", file=sys.stderr)
        sys.exit(1)

    settings = load_settings()
    client = meilisearch.Client(settings.meilisearch_url, settings.meilisearch_api_key or "")
    index = client.index(PDF_INDEX)

    results = index.search(
        query,
        {
            "limit": limit,
            "hybrid": {"semanticRatio": 0.5, "embedder": "mistral"},
            "attributesToRetrieve": ["id", "title", "chunk_text", "page", "source_file"],
        },
    )

    hits = results.get("hits", [])
    print(f"Query: {query!r}")
    print(f"Search: hybrid (semanticRatio=0.5, embedder=mistral) — same as chat\n")
    print(f"Chunks returned ({len(hits)}):\n")
    for i, hit in enumerate(hits, start=1):
        cid = hit.get("id", "?")
        title = hit.get("title") or "(no title)"
        text = (hit.get("chunk_text") or "")[:400]
        print(f"--- Chunk {i}: id={cid} | title={title!r} ---")
        print(f"{text}...")
        print()


if __name__ == "__main__":
    main()
