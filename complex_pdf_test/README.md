# Complex PDF Test

End-to-end test with rich PDFs (text, tables, figures). Pipeline: parse (Docling) → normalize → chunk → build JSON → optionally load into Meilisearch (index `pdf_chunks`) with Mistral embedder.

**Output:** a JSON file whose root is an array of chunk objects. Each object has: `id`, `doc_id`, `chunk_text`, `title`, `page`, `element_type`, `source_file`.

Run from project root:

```bash
# Produce chunks JSON only (default: <pdf_stem>.chunks.json next to the PDF)
python complex_pdf_test/run_pipeline.py complex_pdf_test/mistral-doc.pdf

# Custom output path
python complex_pdf_test/run_pipeline.py complex_pdf_test/mistral-doc.pdf -o out/chunks.json

# Also load chunks into Meilisearch
python complex_pdf_test/run_pipeline.py complex_pdf_test/mistral-doc.pdf --load
```

## Chat (Option A – Meilisearch native)

After loading chunks into Meilisearch, you can use the **experimental chat** to ask questions in natural language (Meilisearch does retrieval + Mistral LLM).

**Prerequisites:** Meilisearch ≥ v1.15.1 with a master key; `MEILISEARCH_API_KEY` (master) and `MISTRAL_API_KEY` in `.env`.

```bash
# One-time setup: enable chat, configure index pdf_chunks, create workspace mistral-pdf
python complex_pdf_test/setup_meilisearch_chat.py

# Ask a question (streaming reply)
python complex_pdf_test/ask_chat.py "Quelle est l'architecture de Mixtral ?"
```

