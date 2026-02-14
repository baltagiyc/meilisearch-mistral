"""
Run 50 keyword-only searches on pdf_chunks and report p50 (median) and p95 latency in ms.

No embedder call — Meilisearch full-text only. Compare with benchmark_hybrid_latency.py.

Usage (from project root):
  uv run python complex_pdf_test/audit/benchmark_keyword_latency.py

Requires: Meilisearch running with pdf_chunks index populated (run_pipeline.py --load).
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import meilisearch
from config import load_settings

PDF_INDEX = "pdf_chunks"
NUM_REQUESTS = 50
QUERY = "architecture Mixtral experts routing"


def main() -> None:
    settings = load_settings()
    client = meilisearch.Client(settings.meilisearch_url, settings.meilisearch_api_key or "")
    index = client.index(PDF_INDEX)

    latencies_ms: list[float] = []
    for i in range(NUM_REQUESTS):
        t0 = time.perf_counter()
        index.search(
            QUERY,
            {
                "limit": 5,
                "attributesToRetrieve": ["id", "title", "chunk_text"],
            },
        )
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000)

    latencies_ms.sort()
    p50 = latencies_ms[len(latencies_ms) // 2]
    p95_idx = int(len(latencies_ms) * 0.95)
    p95 = latencies_ms[p95_idx] if p95_idx < len(latencies_ms) else latencies_ms[-1]
    mean_ms = sum(latencies_ms) / len(latencies_ms)

    print(f"Keyword search latency (index: {PDF_INDEX}, {NUM_REQUESTS} requests)")
    print(f"  Query: {QUERY!r}")
    print(f"  Mean:  {mean_ms:.1f} ms")
    print(f"  p50:   {p50:.1f} ms")
    print(f"  p95:   {p95:.1f} ms")
    print()
    print(f"→ Due diligence one-liner: \"{mean_ms:.0f} ms average (p50 {p50:.0f} ms) for keyword-only search on a complex document (no embedder).\"")


if __name__ == "__main__":
    main()
