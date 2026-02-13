# meilisearch-mistral

Due diligence repo: **Meilisearch + Mistral** — hybrid search, embeddings, and native RAG chat on real documents.

---

## What we explored

- **Simple SDK test** (`simple_sdk_test/`): import JSON, configure the Mistral embedder, run keyword, semantic, and **hybrid** search. Baseline to confirm the SDK and vector search work.
- **Complex PDF pipeline** (`complex_pdf_test/`): real PDF (e.g. Mixtral paper) → **Docling** parse → normalize → chunk by sections/size → build JSON → load into Meilisearch. Validates the full chain on rich layout (tables, sections), not just pre-built data.
- **Native chat (Option A)**: Meilisearch has a **chat** API: you send a question, it runs the search and calls an LLM (e.g. Mistral), then streams back the LLM’s answer. That **chat API** is what Meilisearch marks as **experimental** (unstable, may change). Indexing PDF chunks, hybrid search, embeddings — all of that is normal/stable; only the “question → synthesized answer” endpoint is experimental.
- **Audit**: script to see which chunks hybrid search returns for a query (proxy for “what the chat sent to the LLM”), since the chat response doesn’t expose sources.
- **SDK and API limits**: we checked the Meilisearch Python SDK (e.g. `index.py`): only **JSON / NDJSON / CSV** (and list-of-dicts); no raw PDF/DOCX ingestion. Chat has no dedicated SDK method — HTTP + SSE parsing. All of that is documented.

So: hybrid search in production-like conditions, real PDF → index → conversational RAG, plus a clear list of gotchas (version, master key, baseUrl, experimental status). That’s why this repo is a solid reference for “can we build on Meilisearch + Mistral?” — it’s not just a hello-world; it’s a full pass with real data and honest caveats.

---

## What’s in this repo

| Area | Purpose |
|------|---------|
| `simple_sdk_test/` | Keyword, semantic, hybrid search on pre-built JSON; Mistral embedder. |
| `complex_pdf_test/` | PDF pipeline (parse → chunk → index), optional load to Meilisearch, native chat setup + ask, audit script. See [complex_pdf_test/README.md](complex_pdf_test/README.md) and [BILAN.md](complex_pdf_test/BILAN.md). |
| `mistral_key_tests/` | Quick checks: API key, list models, list embedding models. |
| `config/` | Shared settings (e.g. `.env` loading). |

---

## Environment variables (secrets)

All configuration is read from a `.env` file at the project root. **Do not commit `.env`** (it is in `.gitignore`).

### What you need

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MISTRAL_API_KEY` | **Yes** | — | Mistral API key for embeddings (`mistral-embed`). |
| `MEILISEARCH_URL` | No | `http://localhost:7700` | Meilisearch instance URL. |
| `MEILISEARCH_API_KEY` | No | (empty) | Meilisearch API key if your instance is secured (e.g. Cloud). Leave empty for local dev without auth. |

### How to provide them

1. **Copy the template**
   ```bash
   cp .env.example .env
   ```

2. **Mistral API key**
   - Go to [Mistral Console](https://console.mistral.ai/) → **API Keys**.
   - Create a key and paste it in `.env` as `MISTRAL_API_KEY=sk-...`.

3. **Meilisearch**
   - **Local (no auth)** : leave `MEILISEARCH_URL=http://localhost:7700` and `MEILISEARCH_API_KEY=` empty.
   - **Meilisearch Cloud or secured** : set `MEILISEARCH_URL` to your instance URL and `MEILISEARCH_API_KEY` to your key.

## Running Meilisearch locally (Docker)

**Meilisearch is not a Python package**: it is a server (like a database). You do not install it with `uv` or `pip`; you **start** it (often via Docker).

- **Search + indexing**: any recent version is fine (e.g. `v1.13`).
- **Chat (Option A)**: you need **Meilisearch ≥ v1.15.1** (chat is an experimental feature added in that version).

**For search only** (no chat), one command is enough:

```bash
docker run -it --rm -p 7700:7700 getmeili/meilisearch:v1.15.1
```

**For chat (Option A)**: the server **must** be started with a **master key**, otherwise the chat/completions route causes a panic (Meilisearch-side bug). For example:

```bash
docker run -it --rm -p 7700:7700 -e MEILI_MASTER_KEY=devMasterKey123456 getmeili/meilisearch:v1.15.1
```

In your `.env`, add: `MEILISEARCH_API_KEY=devMasterKey123456` (same value as `MEILI_MASTER_KEY`). Scripts then authenticate and chat can run.

- `7700`: the default port expected in `.env`.
- Without chat: you can leave `MEILISEARCH_API_KEY` empty and omit the master key.

Once the server is running, Python scripts (`uv run python ...`) talk to Meilisearch via the URL and key configured in `.env`.

## Mistral API key tests

Scripts are grouped in `mistral_key_tests/`:

- `check_api_key.py`: quick chat call to validate key usage.
- `list_models.py`: lists models and shows a capacity heuristic.
- `list_embedding_models.py`: lists embedding models for RAG.


