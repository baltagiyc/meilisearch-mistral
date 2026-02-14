# Full assessment — Complex PDF Test & Chat (Experimental Feature)

## Short conclusion

We set up a **PDF → chunks → Meilisearch (Mistral embedder) pipeline**, then **native Meilisearch chat (Option A)** using the **experimental** `chatCompletions` feature. On a real technical PDF (Mixtral 8x7B paper), the system correctly answers four targeted questions (architecture, benchmarks, routing, French), with **hybrid search** (keyword + semantic). The due diligence is strengthened: we validated the stack on a realistic case and identified constraints (version, master key, Mistral baseUrl, no dedicated chat SDK). The issues encountered (panic, wrong provider, 401) are documented and fixed in the scripts; the assessment is **positive for a PoC**, with clear caveats on the experimental nature and operational maturity.

---

## 1. Objectives: why we did this

### 1.1 Test the experimental-features phase

- Meilisearch docs describe **chat** as an **experimental** feature (`chatCompletions`), enabled via `PATCH /experimental-features`.
- Goal: check in real conditions whether this feature is **usable** in a RAG scenario (chunk index, Mistral LLM), and whether it adds real value (answers grounded in chunks, no gross hallucination).
- Due diligence stake: decide whether to recommend relying on this building block for a project (with the right precautions).

### 1.2 See performance on a real PDF

- “Simple” tests (e.g. `simple_sdk_test/`) use pre-built JSONs; they do not validate **PDF parsing**, **chunking**, or behaviour on **tables / sections / figures**.
- Goal: use a **real technical PDF** (Mixtral of Experts paper, ~2.4 MB, tables, benchmarks, formulas, multiple sections) to evaluate:
  - the **parse → normalize → chunk → index** chain;
  - **search quality** (hybrid) and **chat response** on precise questions (numbers, semantic nuance, tables).
- Due diligence stake: answer “Does Meilisearch + Mistral hold up on a complex document or not?”.

### 1.3 Answer base due diligence questions

The repo is dedicated to a **Meilisearch + Mistral audit / due diligence** (hybrid search, RAG). What we did in `complex_pdf_test/` directly contributes to:

| Due diligence question | What the complex PDF test provides |
|------------------------|-------------------------------------|
| **Hybrid search in real conditions** | Index `pdf_chunks` with Mistral embedder; hybrid search (keyword + semantic) used by chat; script `search_chunks_for_query.py` to inspect returned chunks. |
| **“Turnkey” RAG vs DIY** | Native Chat = single API call, Meilisearch handles retrieval + LLM call; we verified that answers are grounded in the document (4 targeted questions validated). |
| **Maturity / risks of experimental features** | Enabling `chatCompletions`, bugs encountered (panic without master key, baseUrl required for Mistral), no chat SDK wrapper: we document the cost and workarounds. |
| **Quality on complex PDFs** | A real paper with tables and sections; validation that numbers (GSM8K, Humaneval, Table 4 FR) and nuance (routing not domain-specialized) are correctly retrieved. |
| **Mistral integration (embedding + chat)** | Mistral embedding for chunks; chat configured with Mistral source + baseUrl to avoid routing to OpenAI; a single coherent stack. |

---

## 2. What was implemented (point by point)

### 2.1 PDF → chunks → JSON pipeline

| File | Role | Why |
|------|------|-----|
| **parse_pdf.py** | Uses **Docling** to convert PDF to markdown (layout, tables, text). | Get a structured representation of the PDF for clean chunking (sections, paragraphs) instead of character-level splits. |
| **normalize_elements.py** | Text normalization (spaces, line breaks) via regex. | Reduce noise and spacing variation before chunking and indexing. |
| **chunk_pdf.py** | Split by `##` / `###` headers, then by size (max_chars, overlap). | Avoid cutting mid-sentence or mid-table; keep semantic units (sections) when possible. |
| **build_documents.py** | Builds the list of documents (chunks) in the target format. | Unify format (id, doc_id, chunk_text, title, page, element_type, source_file) for JSON export and Meilisearch. |
| **schemas.py** | Defines `RawElement`, `Chunk`, `chunk_to_meilisearch_doc`. | Typing and consistency of structures across the pipeline. |
| **run_pipeline.py** | Orchestrates parse → normalize → chunk → build → JSON write; `--load` option to push to Meilisearch. | Single entry point to reproduce the flow and load the index. |

**Test document:** `mistral-doc.pdf` (Mixtral of Experts paper).  
**Output:** `mistral-doc.chunks.json` (43 chunks). Notes: first chunk sometimes noisy (author names), figure captions in text, `page` often null; we left as-is for the report.

### 2.2 Loading into Meilisearch (index `pdf_chunks`)

| File | Role | Why |
|------|------|-----|
| **load_to_meilisearch.py** | Configures index `pdf_chunks` (searchable: `chunk_text`, `title`; filterable: `doc_id`, `page`, etc.) and registers the **Mistral embedder** (REST, 1024 dimensions, documentTemplate for embedding). Then adds documents. | Enable **hybrid search** (keyword + semantic); embeddings are computed by Meilisearch via the Mistral API. |

The index is ready for full-text and semantic search with the same Mistral model as for chat.

### 2.3 Native Meilisearch chat (Option A — experimental)

| File | Role | Why |
|------|------|-----|
| **setup_meilisearch_chat.py** | 1) Enables experimental feature `chatCompletions` (PATCH `/experimental-features`). 2) Configures index `pdf_chunks` for chat (description, documentTemplate Liquid, documentTemplateMaxBytes). 3) Creates/updates workspace **mistral-pdf** (Mistral source, apiKey, **baseUrl** `https://api.mistral.ai/v1`, system prompts). | Without this setup, chat does not exist (feature off), the index is not “chat-aware”, and the LLM would not be Mistral (without baseUrl, Meilisearch routed to OpenAI in our tests). |
| **ask_chat.py** | Sends a question via POST `/chats/mistral-pdf/chat/completions` (stream: true), parses the SSE stream (OpenAI-like format), prints content and handles errors (events with `error`). `--debug` option to inspect SSE chunk structure. | Allow querying the document in natural language and getting a synthetic answer instead of only a list of hits. |
| **search_chunks_for_query.py** | Runs **hybrid search** (same parameters as chat uses internally) on `pdf_chunks` and prints returned chunks (id, title, chunk_text excerpt). | Since chat does not return sources (tools disabled), this script acts as a **proxy** to see “which chunks were (or would have been) sent to the LLM”. |

**Search mode actually used by chat:** **hybrid** (keyword + semantic, embedder `mistral`). Chunks sent to the LLM are from this hybrid search, formatted per the index chat `documentTemplate`.

### 2.4 Search latency benchmarks

Two scripts run **50 searches** on `pdf_chunks` and report mean / p50 / p95 latency (ms). Same query: *"architecture Mixtral experts routing"*, index with 43 chunks.

**Keyword-only** (`audit/benchmark_keyword_latency.py`): full-text only, no embedder.

| Metric | Keyword | Hybrid |
|--------|--------|--------|
| **Mean** | 3 ms | 335 ms |
| **p50 (median)** | 2 ms | 194 ms |
| **p95** | 9 ms | 727 ms |

**Hybrid** (`audit/benchmark_hybrid_latency.py`): same params as chat (`semanticRatio` 0.5, embedder `mistral`). Latency includes the **Mistral embedder API round-trip** plus Meilisearch search.

**Due diligence one-liners:**
- *"~2 ms median for keyword-only search on a complex document."*
- *"~200 ms median for hybrid search on a complex document — includes Mistral embedder round-trip."*

Re-run: `uv run python complex_pdf_test/audit/benchmark_keyword_latency.py` and `benchmark_hybrid_latency.py` to reproduce or refresh numbers.

### 2.5 Scale test (10k documents)

Script `scale_test/run_scale_test.py`: index **10 000 documents** (from 43 chunks, index `pdf_chunks_scale`) in batches of 1000, then run 50 hybrid searches. Measures ingestion throughput and search latency at scale.

**Results** (single run, Feb 2026):

| Phase | Result |
|-------|--------|
| **Ingestion** | 10 000 docs in **776.9 s** → **12.9 docs/s** (excl. initial settings ~533 s). Batches of 1000; bottleneck = Mistral embedder API. |
| **Hybrid search** (50 req, same query) | **Mean 758 ms** \| **p50 206 ms** \| **p95 2997 ms** |

**Comparison with 43 chunks (section 2.4):**

| Metric | 43 chunks | 10k docs |
|--------|-----------|----------|
| Mean | 335 ms | 758 ms |
| p50 | 194 ms | 206 ms |
| p95 | 727 ms | 2997 ms |

**Takeaway:** p50 stable (~200 ms); mean and p95 degrade at 10k (tail latency). Ingestion ~12.9 docs/s; for larger corpora, consider batch embedding or async. Re-run: `uv run python complex_pdf_test/scale_test/run_scale_test.py`.

---

## 3. Difficulties observed (critical view)

### 3.1 Version and enabling chat

- **Meilisearch &lt; v1.15.1**: the `/experimental-features` route returns **400** for `chatCompletions` (feature missing or not enableable). We had to **upgrade the Docker image** (v1.13 → v1.15.1).
- **Impact**: in prod or CI, pin a version ≥ v1.15.1 and document the dependency.

### 3.2 Server panic (Rust unwrap on None)

- In **v1.15** and **v1.15.1**, **without a master key**: the server **panics** (e.g. `chat_completions.rs:446`, `Option::unwrap()` on `None`) on a call to `/chat/.../completions`. The docs mention a “Default Chat API Key” created when a master key is present; without it, the code assumes a key and crashes.
- **Workaround**: run Meilisearch with a **master key** (≥ 16 characters) and use the **same value** in `.env` (`MEILISEARCH_API_KEY`). We made the key **required** in `setup_meilisearch_chat.py` and `ask_chat.py` for chat.
- **Criticism**: an experimental feature should not crash the process; this is a maturity risk.

### 3.3 Routing to the wrong provider (OpenAI instead of Mistral)

- Without **baseUrl** in the workspace, Meilisearch sent chat requests to **OpenAI**; the error was “Incorrect API key... platform.openai.com” even though we had configured a Mistral key.
- **Workaround**: explicitly add **`baseUrl": "https://api.mistral.ai/v1"`** in the workspace. After re-setup, chat correctly used Mistral and returned correct answers.
- **Criticism**: default behaviour (no baseUrl) is misleading; docs could better state that for Mistral, setting baseUrl is strongly recommended.

### 3.4 Chat tools (Progress / Sources) disabled

- Sending the **`tools`** parameter (e.g. `_meiliSearchProgress`, `_meiliSearchSources`) caused a **panic** (unwrap on None) in v1.15. We therefore **removed** `tools` from the body in `ask_chat.py`.
- **Consequence**: no **sources** (chunks) in the chat response; we do not see explicitly “this passage comes from chunk X”. For audit we compensate with `search_chunks_for_query.py`.
- **Criticism**: for “serious” use (traceability, compliance), showing sources matters; stability of experimental tools should be monitored.

### 3.5 Script and configuration errors

- **401 on GET /version**: in `setup_meilisearch_chat.py`, the `/version` call did not send **headers** (Authorization). Fixed by adding `headers=headers`.
- **Empty or wrong API key**: if the master key is &lt; 16 characters, Meilisearch generates another and prints it; if `.env` keeps the old one, **403 invalid_api_key**. We documented “same value in docker run and MEILISEARCH_API_KEY”, and added `.strip()` on the key in `config/settings.py` to avoid stray spaces.
- **Loading .env**: depending on working directory, `load_dotenv()` did not find `.env`. We added **`load_dotenv(PROJECT_ROOT / ".env")`** in `setup_meilisearch_chat.py` and `ask_chat.py` to force loading from project root.

### 3.6 Display (encoding)

- In terminal output, accented characters may show as **mojibake** (e.g. `Ã©` instead of `é`). The received content is valid UTF-8; the issue is on the display environment (terminal/IDE). No code fix for now.

---

## 4. Procedure followed (how we proceeded)

1. **PDF pipeline**: set up parse (Docling) → normalize → chunk (by sections then size/overlap) → build → JSON. Run on `mistral-doc.pdf` and check chunk file.
2. **Indexing**: configure index `pdf_chunks` (searchable, filterable, Mistral embedder) and load 43 chunks via `run_pipeline.py --load`.
3. **Chat**: read Meilisearch docs (experimental-features, chats, workspace, stream completions). Implement `setup_meilisearch_chat.py` and `ask_chat.py` in Python (no manual curl).
4. **Troubleshooting**: 400 → upgrade Docker to v1.15.1; panic → enable master key and align `.env`; empty response → debug SSE → spot “OpenAI” error → add Mistral `baseUrl`; 401 → add headers on `/version`; 403 → clarify master key and `.strip()`.
5. **Validation**: four targeted questions (47B/13B architecture, GSM8K/Humaneval benchmarks, expert specialization, FR Table 4 benchmarks); all received correct, document-grounded answers.
6. **Transparency**: added `search_chunks_for_query.py` to show **search mode** (hybrid) and **chunks** returned for a given query (proxy for chunks sent to the LLM).

---

## 5. Positive points

- **Option A operational**: single API call (chat completions) for a RAG answer; no need to code the search → prompt → LLM loop yourself.
- **Results on a real PDF**: 4/4 questions validated (technical accuracy, tables, semantic nuance, French); tables and numbers are correctly extracted and restituted.
- **Hybrid search**: keyword + semantic (Mistral); the right passages are retrieved (sections, tables, conclusion).
- **Coherent stack**: one embedder (Mistral) for the index and one LLM (Mistral) for chat; centralized config (`.env`, `config/settings.py`).
- **Reproducible scripts**: everything can be run from the repo (setup, pipeline, ask, search_chunks_for_query); no dependency on a Meilisearch UI.
- **Documented pitfalls**: version, master key, baseUrl, tools, 401/403 are documented in README and comments; a new user can avoid the same errors.
- **Due diligence**: concrete evidence that “Meilisearch + Mistral” can support conversational RAG on a complex technical document, with a clear list of limits and prerequisites.

---

## 6. Negative points

- **Experimental feature**: chat not stabilized (panics, misleading defaults); API may change; use with full awareness.
- **No chat SDK**: no dedicated method in the Python SDK; everything goes through HTTP calls (requests) and manual SSE stream parsing.
- **Master key required for chat**: in local “no auth” mode you cannot use chat; you must manage a key (≥ 16 chars) and keep it in sync between Docker and `.env`.
- **No sources in the response**: tools (including _meiliSearchSources) are disabled; you do not see the exact chunks sent to the LLM in the chat response (only via the proxy script).
- **Single test document**: one PDF (Mixtral paper); no variety of formats (reports, slides, multi-language) or volume.
- **Meilisearch version dependency**: need v1.15.1+; any infra or docs must state this.
- **Display encoding**: possible mojibake in terminal output; cosmetic but worth noting.

---

## 7. File summary for `complex_pdf_test/`

| Folder / File | Type | One-line role |
|---------------|------|----------------|
| **pipeline/** | | PDF → list of chunk dicts |
| pipeline/parse_pdf.py | Pipeline | PDF → markdown via Docling. |
| pipeline/normalize_elements.py | Pipeline | Text normalization (regex). |
| pipeline/chunk_pdf.py | Pipeline | Split by sections then by size/overlap. |
| pipeline/build_documents.py | Pipeline | Build documents (chunks) in target format. |
| pipeline/schemas.py | Data | RawElement, Chunk, chunk_to_meilisearch_doc. |
| **load/** | | Meilisearch indexing |
| load/load_to_meilisearch.py | Indexing | Configure `pdf_chunks` (Mistral embedder) and load documents. |
| **chat/** | | Native chat (Option A) |
| chat/setup_meilisearch_chat.py | Chat | Enable chatCompletions, configure index for chat, create Mistral workspace (with baseUrl). |
| chat/ask_chat.py | Chat | Send question to chat, parse SSE stream, print response. |
| **audit/** | | Inspection |
| audit/search_chunks_for_query.py | Audit | Run hybrid search (same as chat) and print returned chunks. |
| audit/benchmark_hybrid_latency.py | Audit | Run 50 hybrid searches, report mean / p50 / p95 latency (ms). |
| audit/benchmark_keyword_latency.py | Audit | Run 50 keyword-only searches, report mean / p50 / p95 latency (ms). |
| **run_pipeline.py** | Orchestration | parse → normalize → chunk → build → JSON; `--load` for Meilisearch. |
| **mistral-doc.pdf** | Data | Test PDF (Mixtral of Experts paper). |
| **mistral-doc.chunks.json** | Data | Pipeline output (43 chunks). |
| **README.md** | Doc | Instructions and layout (pipeline, load, chat, audit). |
| **BILAN.md** | Doc | This document. |

---

## 8. Summary vs due diligence

- **Hybrid search**: validated on a real chunk index (Mistral embedder); chat correctly relies on it.
- **“Native” RAG**: Option A tested end-to-end; relevant, document-grounded answers.
- **Experimental feature**: usable under conditions (version, master key, baseUrl); difficulties and workarounds are documented.
- **Performance on complex PDF**: a paper with tables and sections was processed successfully (numbers, nuance, French).
- **Mistral integration**: embedding + chat; single stack, explicit config (baseUrl) to avoid wrong routing.

This assessment can serve as a **factual basis** for the “tests on real document” and “experimental chat” parts of the due diligence report, citing both the positive results and the caveats listed above.
