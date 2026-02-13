"""
Setup Meilisearch for conversational search (Option A – native chat).

Runs entirely via the Meilisearch API (no curl needed). Does:
  1. Enable experimental feature chatCompletions
  2. Configure index pdf_chunks with chat settings (description + documentTemplate)
  3. Create/update workspace "mistral-pdf" with Mistral as LLM

Requires: Meilisearch >= v1.15.1, MISTRAL_API_KEY in .env.
For chat to work, Meilisearch must be started WITH a master key and you must set
MEILISEARCH_API_KEY to that same key in .env (otherwise chat/completions panics).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure .env is loaded from project root (cwd may differ when run via uv/IDE)
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import requests
from config import load_settings

PDF_INDEX = "pdf_chunks"
WORKSPACE_UID = "mistral-pdf"
LOG_PREFIX = "[setup_chat]"


def _check_version(base: str, headers: dict) -> None:
    """Require Meilisearch >= 1.15.1 for chat."""
    r = requests.get(f"{base}/version", headers=headers, timeout=5)
    r.raise_for_status()
    data = r.json()
    version = data.get("pkgVersion", data.get("version", ""))
    try:
        major, minor, patch = (int(x) for x in version.split(".")[:3])
        if (major, minor, patch) < (1, 15, 1):
            raise SystemExit(
                f"{LOG_PREFIX} Meilisearch {version} is too old. Chat requires >= 1.15.1.\n"
                "Relance avec: docker run -it --rm -p 7700:7700 getmeili/meilisearch:v1.15"
            )
    except (ValueError, IndexError):
        pass  # skip check if version format unknown


def main() -> None:
    settings = load_settings()
    if not settings.meilisearch_api_key:
        raise SystemExit(
            f"{LOG_PREFIX} MEILISEARCH_API_KEY is empty. For chat, Meilisearch must be run with a master key\n"
            "and .env must set MEILISEARCH_API_KEY to that key (e.g. MEILI_MASTER_KEY=devMasterKey123456\n"
            "in docker run, and MEILISEARCH_API_KEY=devMasterKey123456 in .env). See README."
        )
    base = settings.meilisearch_url.rstrip("/")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.meilisearch_api_key}"}

    print(f"{LOG_PREFIX} Checking Meilisearch version...")
    _check_version(base, headers)

    # 1. Enable chatCompletions
    print(f"{LOG_PREFIX} Enabling experimental feature chatCompletions...")
    r = requests.patch(
        f"{base}/experimental-features",
        headers=headers,
        json={"chatCompletions": True},
        timeout=10,
    )
    if not r.ok:
        msg = r.text
        try:
            msg = r.json()
        except Exception:
            pass
        raise SystemExit(
            f"{LOG_PREFIX} Failed to enable chatCompletions ({r.status_code}): {msg}\n"
            "Ensure Meilisearch >= v1.15.1 and a master key is set (MEILISEARCH_API_KEY)."
        )
    print(f"{LOG_PREFIX} chatCompletions enabled.")

    # 2. Index chat settings for pdf_chunks
    print(f"{LOG_PREFIX} Configuring index '{PDF_INDEX}' for chat...")
    chat_settings = {
        "chat": {
            "description": "Chunks extraits de documents PDF (sections, paragraphes). Contient chunk_text, title, page, source_file. Utiliser pour répondre à des questions sur le contenu des PDFs indexés.",
            "documentTemplate": "{% if doc.title %}Section: {{ doc.title }}. {% endif %}{% if doc.chunk_text %}{{ doc.chunk_text }}{% endif %}",
            "documentTemplateMaxBytes": 500,
        }
    }
    r = requests.patch(
        f"{base}/indexes/{PDF_INDEX}/settings",
        headers=headers,
        json=chat_settings,
        timeout=30,
    )
    r.raise_for_status()
    print(f"{LOG_PREFIX} Index chat settings applied.")

    # 3. Create/update workspace (Mistral)
    print(f"{LOG_PREFIX} Creating/updating workspace '{WORKSPACE_UID}' (Mistral)...")
    # baseUrl forces Meilisearch to call Mistral instead of defaulting to OpenAI
    workspace_body = {
        "source": "mistral",
        "apiKey": settings.mistral_api_key,
        "baseUrl": "https://api.mistral.ai/v1",
        "prompts": {
            "system": "Tu es un assistant qui répond uniquement à partir des extraits de documents fournis. Réponds en français de façon précise et concise. Si les extraits ne contiennent pas l'information, dis-le.",
        },
    }
    r = requests.patch(
        f"{base}/chats/{WORKSPACE_UID}/settings",
        headers=headers,
        json=workspace_body,
        timeout=10,
    )
    r.raise_for_status()
    print(f"{LOG_PREFIX} Workspace '{WORKSPACE_UID}' ready.")

    print(f"{LOG_PREFIX} Done. Run: python complex_pdf_test/ask_chat.py \"Ta question\"")


if __name__ == "__main__":
    main()
