import json
import sys
from pathlib import Path
from typing import Any

import meilisearch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import load_settings


def get_client() -> meilisearch.Client:
    settings = load_settings()
    if settings.meilisearch_api_key:
        return meilisearch.Client(settings.meilisearch_url, settings.meilisearch_api_key)
    return meilisearch.Client(settings.meilisearch_url)


def get_index():
    settings = load_settings()
    client = get_client()
    return client, client.index(settings.meilisearch_index), settings


def read_documents() -> list[dict[str, Any]]:
    path = Path(__file__).with_name("documents.json")
    return json.loads(path.read_text(encoding="utf-8"))


def wait_task(client: meilisearch.Client, task: Any) -> Any:
    task_uid = getattr(task, "task_uid", None) or getattr(task, "uid", None)
    if task_uid is None and isinstance(task, dict):
        task_uid = task.get("taskUid") or task.get("uid")
    if task_uid is None:
        raise RuntimeError(f"Task UID not found in response: {task}")
    return client.wait_for_task(task_uid)


def print_hits(results: dict[str, Any]) -> None:
    hits = results.get("hits", [])
    if not hits:
        print("No results.")
        return
    for i, hit in enumerate(hits, start=1):
        print(f"{i}. [{hit.get('id')}] {hit.get('title')}")
        print(f"   category={hit.get('category')} language={hit.get('language')}")
        print(f"   {hit.get('content')}")
