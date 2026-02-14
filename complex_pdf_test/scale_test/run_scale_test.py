"""
Scale test: index 10k docs in batches, then benchmark search latency.

We measure two things:

1. INGESTION (task queue + embedder)
   Time from first batch sent until all indexation tasks are "succeeded".
   - Tests Meilisearch task queue robustness (10 batches of 1000 docs).
   - Tests auto-embedder under load: 10k docs = 10k Mistral API calls; we see if
     the system handles the spike (throughput, rate limits, failures).
   - Same API as the 43-chunk load: add_documents. Here we use add_documents_in_batches
     (SDK helper that calls add_documents in a loop with batch_size=1000).

2. SEARCH (mmap / LMDB)
   After ingestion, run 50 hybrid searches and report mean / p50 / p95.
   - Verifies that at 10k docs the latency doesn't explode (memory-mapping / LMDB).

43 chunks (load_to_meilisearch): index.add_documents(documents, primary_key="id") — one call.
10k (this script): index.add_documents_in_batches(documents, batch_size=1000, primary_key="id")
  → same add_documents under the hood, called once per batch.

Usage (from project root):
  uv run python complex_pdf_test/scale_test/run_scale_test.py
"""

import json
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

# Index dedicated to scale test (do not overwrite pdf_chunks)
INDEX_UID = "pdf_chunks_scale"
CHUNKS_PATH = PROJECT_ROOT / "complex_pdf_test" / "mistral-doc.chunks.json"
TARGET_DOCS = 10_000
BATCH_SIZE = 1000
BENCHMARK_REQUESTS = 50
QUERY = "architecture Mixtral experts routing"

# Logging: elapsed seconds since script start
_script_start = time.perf_counter()


def _elapsed() -> float:
    return time.perf_counter() - _script_start


def log(msg: str) -> None:
    print(f"[{_elapsed():.1f}s] [scale_test] {msg}", flush=True)


def get_client() -> meilisearch.Client:
    settings = load_settings()
    if settings.meilisearch_api_key:
        return meilisearch.Client(settings.meilisearch_url, settings.meilisearch_api_key)
    return meilisearch.Client(settings.meilisearch_url)


# Per-batch indexation with embedder can take minutes (Mistral API). Default SDK timeout is 5s.
TASK_WAIT_TIMEOUT_MS = 30 * 60 * 1000  # 30 min per batch


def _task_uid(task) -> int:
    uid = getattr(task, "task_uid", None) or getattr(task, "uid", None)
    if uid is None and hasattr(task, "task_uid"):
        uid = task.task_uid
    if uid is None and isinstance(task, dict):
        uid = task.get("taskUid") or task.get("uid")
    if uid is None:
        raise RuntimeError(f"Task UID not found in response: {task}")
    return uid


def wait_task(client: meilisearch.Client, task, timeout_in_ms: int = TASK_WAIT_TIMEOUT_MS) -> None:
    task_uid = _task_uid(task)
    client.wait_for_task(task_uid, timeout_in_ms=timeout_in_ms)


def load_seed_chunks() -> list[dict]:
    data = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    if not data:
        raise RuntimeError(f"No chunks in {CHUNKS_PATH}")
    return data


def build_scale_documents(seed_chunks: list[dict], target: int) -> list[dict]:
    """Clone seed chunks to reach target count; vary id and add small text noise to avoid perfect duplicates."""
    out: list[dict] = []
    n_seed = len(seed_chunks)
    for i in range(target):
        base = seed_chunks[i % n_seed].copy()
        base["id"] = f"scale_c{i}"
        base["doc_id"] = "scale_doc"
        # Slight noise so embeddings aren't all identical
        base["chunk_text"] = (base.get("chunk_text") or "") + f" [scale-{i}]"
        out.append(base)
    return out


def main() -> None:
    log("========== Scale test start ==========")
    log(f"Index: {INDEX_UID}  |  Target docs: {TARGET_DOCS}  |  Batch size: {BATCH_SIZE}")
    log(f"Chunks path: {CHUNKS_PATH}")

    log("Loading seed chunks...")
    seed = load_seed_chunks()
    log(f"Loaded {len(seed)} seed chunks from {CHUNKS_PATH.name}")

    log(f"Building {TARGET_DOCS} documents from {len(seed)} chunks (clone + id/noise)...")
    documents = build_scale_documents(seed, TARGET_DOCS)
    log(f"Built {len(documents)} documents (sample id: {documents[0]['id']})")

    settings = load_settings()
    log(f"Connecting to Meilisearch at {settings.meilisearch_url} ...")
    client = get_client()
    index = client.index(INDEX_UID)
    log("Client connected.")

    log(f"Configuring index {INDEX_UID} (searchable, filterable, Mistral embedder)...")
    settings_task = index.update_settings(
        {
            "searchableAttributes": ["chunk_text", "title"],
            "filterableAttributes": ["doc_id", "page", "element_type", "source_file"],
            "embedders": {
                "mistral": {
                    "source": "rest",
                    "apiKey": settings.mistral_api_key,
                    "dimensions": 1024,
                    "documentTemplate": (
                        "{% if doc.title %}Section: {{ doc.title }}. {% endif %}"
                        "{% if doc.chunk_text %}{{ doc.chunk_text | truncatewords: 50 }}{% endif %}"
                    ),
                    "url": "https://api.mistral.ai/v1/embeddings",
                    "request": {
                        "model": settings.mistral_embedding_model,
                        "input": ["{{text}}", "{{..}}"],
                    },
                    "response": {
                        "data": [
                            {"embedding": "{{embedding}}"},
                            "{{..}}",
                        ]
                    },
                }
            },
        }
    )
    settings_uid = _task_uid(settings_task)
    log(f"Settings task enqueued (task_uid={settings_uid}), waiting for success (timeout {TASK_WAIT_TIMEOUT_MS // 1000}s)...")
    wait_task(client, settings_task)
    log("Settings applied successfully.")

    num_batches = (len(documents) + BATCH_SIZE - 1) // BATCH_SIZE
    log(f"Adding {len(documents)} documents in {num_batches} batches of {BATCH_SIZE}...")
    t0_ingestion = time.perf_counter()
    tasks = index.add_documents_in_batches(documents, batch_size=BATCH_SIZE, primary_key="id")
    log(f"Enqueued {len(tasks)} indexation tasks (add_documents_in_batches returned).")

    for i, task in enumerate(tasks):
        task_uid = _task_uid(task)
        batch_start = time.perf_counter()
        doc_start = i * BATCH_SIZE
        doc_end = min((i + 1) * BATCH_SIZE, len(documents))
        log(f"Batch {i + 1}/{len(tasks)}: task_uid={task_uid}, docs {doc_start}-{doc_end-1}, waiting (timeout 30min)...")
        wait_task(client, task)
        batch_elapsed = time.perf_counter() - batch_start
        cumulative = time.perf_counter() - t0_ingestion
        log(f"Batch {i + 1}/{len(tasks)} done in {batch_elapsed:.1f}s (cumulative: {cumulative:.1f}s)")

    elapsed = time.perf_counter() - t0_ingestion
    throughput = len(documents) / elapsed if elapsed > 0 else 0
    log(f"All batches finished. Total ingestion time: {elapsed:.1f}s — throughput: {throughput:.1f} docs/s")

    log(f"Running {BENCHMARK_REQUESTS} hybrid searches on {INDEX_UID} (query: {QUERY!r})...")
    latencies_ms: list[float] = []
    for k in range(BENCHMARK_REQUESTS):
        t0 = time.perf_counter()
        index.search(
            QUERY,
            {
                "limit": 5,
                "hybrid": {"semanticRatio": 0.5, "embedder": "mistral"},
                "attributesToRetrieve": ["id", "title", "chunk_text"],
            },
        )
        latencies_ms.append((time.perf_counter() - t0) * 1000)
        if (k + 1) % 10 == 0 or k == 0:
            log(f"  Search request {k + 1}/{BENCHMARK_REQUESTS} done (last: {latencies_ms[-1]:.0f} ms)")

    latencies_ms.sort()
    p50 = latencies_ms[len(latencies_ms) // 2]
    p95_idx = int(len(latencies_ms) * 0.95)
    p95 = latencies_ms[p95_idx] if p95_idx < len(latencies_ms) else latencies_ms[-1]
    mean_ms = sum(latencies_ms) / len(latencies_ms)

    log("========== Scale test results ==========")
    print()
    print(f"  Ingestion (send → all tasks succeeded): {len(documents)} docs in {elapsed:.1f} s ({throughput:.1f} docs/s)")
    print(f"  Hybrid search ({BENCHMARK_REQUESTS} requests, query {QUERY!r}):")
    print(f"    Mean: {mean_ms:.1f} ms  |  p50: {p50:.1f} ms  |  p95: {p95:.1f} ms")
    print()
    print("  Compare with BILAN (43 chunks): mean ~335 ms, p50 ~194 ms, p95 ~727 ms.")
    if p95 > 2000:
        print("  → p95 degraded significantly at 10k docs.")
    else:
        print("  → Latency at 10k docs in the same order as at 43 chunks.")
    log("========== Scale test end ==========")


if __name__ == "__main__":
    main()
