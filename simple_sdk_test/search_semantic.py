from _common import get_index, print_hits


def main() -> None:
    _, index, settings = get_index()
    query = "How can I improve retrieval quality in RAG?"
    print(f"Index: {settings.meilisearch_index}")
    print(f"Semantic query: {query}\n")
    results = index.search(
        query,
        {
            "limit": 5,
            "hybrid": {"semanticRatio": 1.0, "embedder": "mistral"},
        },
    )
    print_hits(results)


if __name__ == "__main__":
    main()

