# meilisearch-mistral

Due diligence: **Meilisearch + Mistral** — hybrid search, embeddings, RAG chat on real documents.

---

## What we explored

| Area | What we did |
|------|-------------|
| **SDK** | Import JSON, Mistral embedder, keyword / semantic / hybrid search. |
| **PDF pipeline** | Real PDF → Docling parse → chunk → index. Full chain on 43 chunks + scale test at 10k docs. |
| **Experimental chat** | Meilisearch’s “question → LLM answer” API (experimental, **requires v1.15.1**). We enabled it, wired Mistral (baseUrl), streamed answers. Search + embeddings are stable; only this chat endpoint is experimental. |
| **Audit** | Which chunks hybrid returns; latency benchmarks (keyword + hybrid); ingestion throughput. |
| **Limits** | SDK: JSON/NDJSON/CSV only, no raw PDF. Chat: no SDK helper, we use HTTP + SSE. |

---

## What’s in this repo

| Path | Contents |
|------|----------|
| `simple_sdk_test/` | Import docs, keyword / semantic / hybrid search (Mistral embedder). |
| `complex_pdf_test/` | Pipeline (parse → chunk → build), load to Meilisearch, chat setup + ask, audit (search chunks, latency benchmarks), scale_test (10k docs). [README](complex_pdf_test/README.md) · [RESULTS](complex_pdf_test/RESULTS.md) · [BILAN](complex_pdf_test/BILAN.md). |
| `complex_pdf_test/pipeline/` | parse_pdf, normalize, chunk_pdf, build_documents, schemas. |
| `complex_pdf_test/load/` | Load chunks into index `pdf_chunks` (Mistral embedder). |
| `complex_pdf_test/chat/` | Setup experimental chat (workspace, baseUrl), ask_chat (streaming). |
| `complex_pdf_test/audit/` | search_chunks_for_query, benchmark_keyword_latency, benchmark_hybrid_latency. |
| `complex_pdf_test/scale_test/` | run_scale_test (10k docs, ingestion + latency), plot_scale_comparison (charts). |
| `mistral_key_tests/` | check_api_key, list_models, list_embedding_models. |
| `config/` | load_settings, .env at project root. |
| `.env.example` | Template for required variables. |

---

## Environment variables (secrets)

Config from `.env` at project root. **Do not commit `.env`** (in `.gitignore`).

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MISTRAL_API_KEY` | **Yes** | — | Mistral API key (embeddings, chat). [Mistral Console](https://console.mistral.ai/) → API Keys. |
| `MEILISEARCH_URL` | No | `http://localhost:7700` | Meilisearch instance URL. |
| `MEILISEARCH_API_KEY` | **Yes for chat** | (empty) | Meilisearch API key. **Required** to use the experimental chat (master key). Optional if you only do search + indexing. |

```bash
cp .env.example .env
# Edit .env: set MISTRAL_API_KEY=sk-... and, for chat, MEILISEARCH_API_KEY=same-as-master-key
```

## Running Meilisearch locally (Docker)

Meilisearch is a **server** (like a DB). Start it with Docker.

- **Search + indexing only**: any recent image (e.g. `v1.13`). No API key needed in `.env`.
- **Experimental chat**: **Meilisearch ≥ v1.15.1** and a **master key** (without it, chat route panics).

**Search only:**
```bash
docker run -it --rm -p 7700:7700 getmeili/meilisearch:v1.15.1
```

**With experimental chat** (set same key in `.env` as `MEILISEARCH_API_KEY`):
```bash
docker run -it --rm -p 7700:7700 -e MEILI_MASTER_KEY=devMasterKey123456 getmeili/meilisearch:v1.15.1
```

Scripts use `MEILISEARCH_URL` and `MEILISEARCH_API_KEY` from `.env`.

## Mistral API key tests

Scripts are grouped in `mistral_key_tests/`:

- `check_api_key.py`: quick chat call to validate key usage.
- `list_models.py`: lists models and shows a capacity heuristic.
- `list_embedding_models.py`: lists embedding models for RAG.


