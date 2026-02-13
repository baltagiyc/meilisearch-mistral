"""Load chunk documents into Meilisearch (index pdf_chunks) with Mistral embedder."""

import json
import sys
import time
from pathlib import Path

import meilisearch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import load_settings

PDF_INDEX = "pdf_chunks"
LOG_PREFIX = "[load_meilisearch]"


def get_client() -> meilisearch.Client:
    settings = load_settings()
    if settings.meilisearch_api_key:
        return meilisearch.Client(settings.meilisearch_url, settings.meilisearch_api_key)
    return meilisearch.Client(settings.meilisearch_url)


def wait_task(client: meilisearch.Client, task) -> None:
    task_uid = getattr(task, "task_uid", None) or getattr(task, "uid", None)
    if task_uid is None and isinstance(task, dict):
        task_uid = task.get("taskUid") or task.get("uid")
    if task_uid is None:
        raise RuntimeError(f"Task UID not found in response: {task}")
    client.wait_for_task(task_uid)


def load_chunks_into_meilisearch(documents: list[dict]) -> None:
    """Configure index pdf_chunks (searchable + filterable + Mistral embedder) and add documents."""
    print(f"{LOG_PREFIX} Connecting to Meilisearch...")
    settings = load_settings()
    client = get_client()
    index = client.index(PDF_INDEX)
    print(f"{LOG_PREFIX} Updating index settings (searchable, filterable, embedder mistral)...")
    t0 = time.perf_counter()
    settings_task = index.update_settings(
        {
            "searchableAttributes": ["chunk_text", "title"],
            "filterableAttributes": ["doc_id", "page", "element_type", "source_file"],
            "embedders": {
                "mistral": {
                    "source": "rest",
                    "apiKey": settings.mistral_api_key,
                    "dimensions": 1024,
                    "documentTemplate": (
                        "{% if doc.title %}Section: {{ doc.title }}. {% endif %}"
                        "{% if doc.chunk_text %}{{ doc.chunk_text | truncatewords: 50 }}{% endif %}"
                    ),
                    "url": "https://api.mistral.ai/v1/embeddings",
                    "request": {
                        "model": settings.mistral_embedding_model,
                        "input": ["{{text}}", "{{..}}"],
                    },
                    "response": {
                        "data": [
                            {"embedding": "{{embedding}}"},
                            "{{..}}",
                        ]
                    },
                }
            },
        }
    )
    wait_task(client, settings_task)
    print(f"{LOG_PREFIX} Settings applied in {time.perf_counter() - t0:.1f}s")
    print(f"{LOG_PREFIX} Adding {len(documents)} documents (embedding via Mistral)...")
    t1 = time.perf_counter()
    add_task = index.add_documents(documents, primary_key="id")
    wait_task(client, add_task)
    print(f"{LOG_PREFIX} Documents indexed in {time.perf_counter() - t1:.1f}s")


def load_from_json_path(json_path: str | Path) -> None:
    """Read a chunks JSON file and load it into Meilisearch."""
    path = Path(json_path)
    documents = json.loads(path.read_text(encoding="utf-8"))
    load_chunks_into_meilisearch(documents)
