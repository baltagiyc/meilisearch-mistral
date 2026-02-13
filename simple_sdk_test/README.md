# Simple SDK test

This folder contains a minimal Meilisearch + Mistral workflow:

1. Import JSON documents and configure the Mistral embedder
2. Run keyword search
3. Run semantic search
4. Run hybrid search

Run from project root:

```bash
python simple_sdk_test/import_documents.py
python simple_sdk_test/search_keyword.py
python simple_sdk_test/search_semantic.py
python simple_sdk_test/search_hybrid.py
```

