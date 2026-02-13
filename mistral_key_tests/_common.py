import os
from datetime import datetime, timezone
from typing import Iterable

from dotenv import load_dotenv
from mistralai import Mistral


CAPABILITY_FIELDS = (
    "completion_chat",
    "function_calling",
    "completion_fim",
    "fine_tuning",
    "vision",
    "ocr",
    "classification",
    "moderation",
    "audio",
    "audio_transcription",
)


def build_client() -> Mistral:
    load_dotenv()
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError(
            "MISTRAL_API_KEY is missing. Set it in .env or your shell environment."
        )
    return Mistral(api_key=api_key)


def format_created(created: int | None) -> str:
    if not created:
        return "unknown"
    return datetime.fromtimestamp(created, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def capability_flags(capabilities: object | None) -> list[str]:
    if capabilities is None:
        return []
    enabled = []
    for field in CAPABILITY_FIELDS:
        if bool(getattr(capabilities, field, False)):
            enabled.append(field)
    return enabled


def estimated_capacity_score(model_id: str, enabled_capabilities: Iterable[str]) -> int:
    """
    Heuristic score only (not an official benchmark from Mistral).
    """
    model_id_lower = model_id.lower()
    score = 0

    if "large" in model_id_lower:
        score += 40
    elif "medium" in model_id_lower:
        score += 30
    elif "small" in model_id_lower:
        score += 20
    elif "mini" in model_id_lower:
        score += 10

    if "codestral" in model_id_lower:
        score += 8
    if "pixtral" in model_id_lower:
        score += 8
    if "mistral" in model_id_lower:
        score += 4

    return score + len(list(enabled_capabilities))
