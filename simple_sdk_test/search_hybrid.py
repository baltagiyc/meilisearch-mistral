from _common import get_index, print_hits


def main() -> None:
    _, index, settings = get_index()
    query = "semantic retrieval with embeddings"
    print(f"Index: {settings.meilisearch_index}")
    print(f"Hybrid query: {query}\n")
    results = index.search(
        query,
        {
            "limit": 5,
            "hybrid": {"semanticRatio": 0.5, "embedder": "mistral"},
        },
    )
    print_hits(results)


if __name__ == "__main__":
    main()

