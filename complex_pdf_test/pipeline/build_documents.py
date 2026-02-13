"""Build Meilisearch-ready JSON documents from chunks."""

from .schemas import Chunk, chunk_to_meilisearch_doc


def build_documents(chunks: list[Chunk]) -> list[dict]:
    """Convert chunks to a list of dicts (one per chunk) for JSON output and Meilisearch."""
    return [chunk_to_meilisearch_doc(c) for c in chunks]
