# Scale test — max scalability

This folder tests **whether the stack holds at scale**: we index **10k documents** (from the 43 real chunks) and measure **ingestion** then **search latency**. Answer to: *"Can it scale?"*.

## What we measure

1. **Ingestion (task queue + auto-embedder)**  
   **Time elapsed between sending the 10k documents and the moment all indexation tasks are finished.**  
   - Robustness of Meilisearch’s **task queue**: we send 10 batches of 1000 docs; we measure total time until every task is `succeeded`.  
   - **Auto-embedder under load**: 10k docs ⇒ 10k Mistral API calls. We see if the system handles the spike (throughput in docs/s, rate limits, errors).  
   - Reported: total time (s) and throughput (docs/s).

2. **Search (mmap / LMDB)**  
   After ingestion, we run **50 hybrid searches** and report mean / p50 / p95.  
   - Checks that at 10k docs the **latency doesn’t explode** (promise of memory-mapping / LMDB).  
   - If p95 jumps from ~700 ms to several seconds, we note degradation.

## API used

- **43 chunks** (pipeline + `load/load_to_meilisearch.py`): **`index.add_documents(documents, primary_key="id")`** — one call, one task.  
- **10k docs** (this scale test): **`index.add_documents_in_batches(documents, batch_size=1000, primary_key="id")`** — same `add_documents` under the hood; the SDK calls it once per batch (10 batches of 1000).

## Usage

From project root:

```bash
# Meilisearch + .env (MISTRAL_API_KEY, MEILISEARCH_URL, etc.) required
uv run python complex_pdf_test/scale_test/run_scale_test.py
```

- Uses index **`pdf_chunks_scale`** (separate from `pdf_chunks`) so the 43-chunk setup is untouched.
- Expect several minutes for 10k docs (Mistral embedder round-trip per doc).
- At the end, the script prints ingestion time, throughput, and hybrid search p50/p95 on the 10k index.

## Output

- Ingestion time (s) and throughput (docs/s).
- Hybrid search latency: mean, p50, p95 (ms) on 50 requests.
- Compare with BILAN numbers (43 chunks) to see if latency degrades at scale.
