# meilisearch-mistral

Repository to explore Meilisearch SDK with the API of Mistral (hybrid search audit / due diligence).

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

## Mistral API key tests

Scripts are grouped in `mistral_key_tests/`:

- `check_api_key.py`: quick chat call to validate key usage.
- `list_models.py`: lists models and shows a capacity heuristic.
- `list_embedding_models.py`: lists embedding models for RAG.

Run them from the project root:

```bash
python mistral_key_tests/check_api_key.py
python mistral_key_tests/list_models.py
python mistral_key_tests/list_embedding_models.py
```

Note: capacity in `list_models.py` is an internal heuristic (model name + capability flags), not an official benchmark from Mistral.

