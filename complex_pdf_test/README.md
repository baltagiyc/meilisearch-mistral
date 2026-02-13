# Complex PDF Test

End-to-end test with **real PDFs** (text, tables, figures) for the Meilisearch + Mistral due diligence. The simple SDK test uses pre-built JSON and does not validate PDF parsing, chunking, or behaviour on complex layout. This folder runs a full chain: **parse → normalize → chunk → index → (optional) native chat**, so we can check whether hybrid search and Meilisearch’s experimental chat hold up on a realistic document (e.g. the Mixtral paper). For the full assessment, difficulties, and conclusions, see [BILAN.md](BILAN.md).

**What’s in this folder:** parse (Docling) → normalize → chunk → build JSON → optionally load into Meilisearch (index `pdf_chunks`) with Mistral embedder.

**Layout:**
- **pipeline/** — parse, normalize, chunk, build, schemas (PDF → list of chunk dicts)
- **load/** — index `pdf_chunks` + Mistral embedder
- **chat/** — Meilisearch native chat (setup workspace, ask questions)
- **audit/** — e.g. see which chunks hybrid search returns for a query

**Output:** a JSON file whose root is an array of chunk objects (`id`, `doc_id`, `chunk_text`, `title`, `page`, `element_type`, `source_file`).

Run from project root:

```bash
# Produce chunks JSON only (default: <pdf_stem>.chunks.json next to the PDF)
python complex_pdf_test/run_pipeline.py complex_pdf_test/mistral-doc.pdf

# Custom output path
python complex_pdf_test/run_pipeline.py complex_pdf_test/mistral-doc.pdf -o out/chunks.json

# Also load chunks into Meilisearch
python complex_pdf_test/run_pipeline.py complex_pdf_test/mistral-doc.pdf --load
```

## Chat (Meilisearch native)

After loading chunks into Meilisearch, use the **experimental chat** to ask questions in natural language.

**Prerequisites:** Meilisearch ≥ v1.15.1 with a master key; `MEILISEARCH_API_KEY` (master) and `MISTRAL_API_KEY` in `.env`.

```bash
# One-time setup: enable chat, configure index pdf_chunks, create workspace mistral-pdf
python complex_pdf_test/chat/setup_meilisearch_chat.py

# Ask a question (streaming reply)
python complex_pdf_test/chat/ask_chat.py "What is Mixtral's architecture?"
```

## Audit (which chunks are retrieved)

```bash
python complex_pdf_test/audit/search_chunks_for_query.py "Your question" [--limit N]
```

