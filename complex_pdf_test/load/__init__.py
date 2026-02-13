"""Load chunks into Meilisearch (index pdf_chunks, Mistral embedder)."""

from .load_to_meilisearch import load_chunks_into_meilisearch, load_from_json_path

__all__ = ["load_chunks_into_meilisearch", "load_from_json_path"]
