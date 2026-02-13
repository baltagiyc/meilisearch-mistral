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

## Lancer Meilisearch en local (Docker)

**Meilisearch n’est pas un package Python** : c’est un serveur (comme une base de données). On ne l’installe pas avec `uv` ou `pip`, on le **démarre** (souvent via Docker).

- **Recherche + indexation** : n’importe quelle version récente suffit (ex. `v1.13`).
- **Chat (Option A)** : il faut **Meilisearch ≥ v1.15.1** (le chat est une feature expérimentale ajoutée dans cette version).

**Pour la recherche seule** (sans chat), une commande suffit :

```bash
docker run -it --rm -p 7700:7700 getmeili/meilisearch:v1.15.1
```

**Pour le chat (Option A)** : le serveur **doit** être lancé avec une **master key**, sinon la route chat/completions provoque un panic (bug côté Meilisearch). Utilise par exemple :

```bash
docker run -it --rm -p 7700:7700 -e MEILI_MASTER_KEY=devMasterKey123456 getmeili/meilisearch:v1.15.1
```

Et dans ton `.env` ajoute : `MEILISEARCH_API_KEY=devMasterKey123456` (la même valeur que `MEILI_MASTER_KEY`). Ainsi les scripts s’authentifient et le chat peut s’exécuter.

- `7700` : le port attendu par défaut dans `.env`.
- Sans chat : tu peux laisser `MEILISEARCH_API_KEY` vide et ne pas mettre de master key.

Une fois le serveur démarré, les scripts Python (`uv run python ...`) parlent à Meilisearch via l’URL et la clé configurées dans `.env`.

## Mistral API key tests

Scripts are grouped in `mistral_key_tests/`:

- `check_api_key.py`: quick chat call to validate key usage.
- `list_models.py`: lists models and shows a capacity heuristic.
- `list_embedding_models.py`: lists embedding models for RAG.


