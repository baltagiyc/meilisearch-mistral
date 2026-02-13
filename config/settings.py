import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    mistral_api_key: str
    mistral_embedding_model: str
    mistral_chat_model: str
    meilisearch_url: str
    meilisearch_api_key: str
    meilisearch_index: str


def load_settings() -> Settings:
    load_dotenv()

    mistral_api_key = os.getenv("MISTRAL_API_KEY", "").strip()
    if not mistral_api_key:
        raise RuntimeError(
            "MISTRAL_API_KEY is missing. Set it in .env or your shell environment."
        )

    return Settings(
        mistral_api_key=mistral_api_key,
        mistral_embedding_model=os.getenv("MISTRAL_EMBEDDING_MODEL", "mistral-embed"),
        mistral_chat_model=os.getenv("MISTRAL_CHAT_MODEL", "mistral-large-latest"),
        meilisearch_url=os.getenv("MEILISEARCH_URL", "http://localhost:7700"),
        meilisearch_api_key=os.getenv("MEILISEARCH_API_KEY", ""),
        meilisearch_index=os.getenv("MEILISEARCH_INDEX", "documents"),
    )
