from _common import get_index, print_hits


def main() -> None:
    _, index, settings = get_index()
    query = "retrieval semantique sans llm"
    print(f"Index: {settings.meilisearch_index}")
    print(f"Keyword query: {query}\n")
    results = index.search(query, {"limit": 5})
    print_hits(results)


if __name__ == "__main__":
    main()

