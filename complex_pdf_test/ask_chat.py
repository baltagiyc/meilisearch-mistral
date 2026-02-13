"""
Ask a question via Meilisearch native chat (Option A).

Calls POST /chats/{workspace}/chat/completions (streaming) and prints the reply.
No curl: everything via this script.

Usage:
  python complex_pdf_test/ask_chat.py "Quelle est l'architecture de Mixtral ?"
  python complex_pdf_test/ask_chat.py   # reads question from stdin
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import requests
from config import load_settings

WORKSPACE_UID = "mistral-pdf"

# Recommended Meilisearch tools (from doc)
MEILI_TOOLS = [
    {"type": "function", "function": {"name": "_meiliSearchProgress", "description": "Reports real-time search progress to the user"}},
    {"type": "function", "function": {"name": "_meiliSearchSources", "description": "Provides sources and references for the information"}},
]


def ask(question: str, debug: bool = False) -> None:
    settings = load_settings()
    if not settings.meilisearch_api_key:
        raise SystemExit(
            "MEILISEARCH_API_KEY is required for chat (use the same value as MEILI_MASTER_KEY in docker run). See README."
        )
    base = settings.meilisearch_url.rstrip("/")
    url = f"{base}/chats/{WORKSPACE_UID}/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {settings.meilisearch_api_key}"}

    # Minimal body: model, messages, stream. "tools" can trigger a panic in Meilisearch v1.15
    # (unwrap on None at chat_completions.rs:449). Omit tools or use Meilisearch v1.15.1+ / latest.
    body = {
        "model": settings.mistral_chat_model,
        "messages": [{"role": "user", "content": question}],
        "stream": True,
    }

    try:
        r = requests.post(
            url, headers=headers, json=body, stream=True, timeout=(30, 90)
        )
    except requests.exceptions.ConnectionError as e:
        raise SystemExit(
            "Connection closed by server (Meilisearch may have failed calling Mistral).\n"
            "Check: 1) Docker container is running, 2) MISTRAL_API_KEY in .env is valid, "
            "3) docker logs for the Meilisearch container."
        ) from e
    if not r.ok:
        raise SystemExit(f"Chat API error {r.status_code}: {r.text[:500]}")

    # Parse SSE (OpenAI-compatible stream)
    full_content: list[str] = []
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            if debug and line:
                print(f"[debug] skip line: {line[:80]!r}", file=sys.stderr)
            continue
        payload = line[6:].strip()
        if payload == "[DONE]":
            break
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            if debug:
                print(f"[debug] invalid json: {payload[:100]!r}", file=sys.stderr)
            continue
        if debug:
            print(f"[debug] chunk keys: {list(data.keys())}", file=sys.stderr)
        # Meilisearch may send error events (event_id, type, error) instead of OpenAI format
        if "error" in data:
            err = data["error"]
            msg = err if isinstance(err, str) else err.get("message", str(err))
            raise SystemExit(f"Chat API error from Meilisearch: {msg}")
        for choice in data.get("choices", []):
            delta = choice.get("delta", {})
            content = delta.get("content") if isinstance(delta.get("content"), str) else None
            if content:
                full_content.append(content)
                print(content, end="", flush=True)
    print()
    return "".join(full_content)


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--debug"]
    debug = "--debug" in sys.argv
    if args:
        question = " ".join(args)
    else:
        question = sys.stdin.read().strip()
    if not question:
        print("Usage: python ask_chat.py \"Your question\" [--debug]", file=sys.stderr)
        sys.exit(1)
    if debug:
        print("[debug] enabled (chunk structure printed to stderr)", file=sys.stderr)
    ask(question, debug=debug)


if __name__ == "__main__":
    main()
