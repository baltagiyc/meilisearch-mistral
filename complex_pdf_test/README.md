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

