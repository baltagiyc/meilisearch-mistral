from _common import get_index, read_documents, wait_task


def main() -> None:
    client, index, settings = get_index()
    documents = read_documents()

    print(f"Using index: {settings.meilisearch_index}")
    print("Applying index settings...")

    settings_task = index.update_settings(
        {
            "searchableAttributes": ["title", "content"],
            "filterableAttributes": ["category", "language", "source"],
            "embedders": {
                "mistral": {
                    "source": "rest",
                    "apiKey": settings.mistral_api_key,
                    "dimensions": 1024,
                    "documentTemplate": (
                        "{% if doc.title %}Title: {{ doc.title }}. {% endif %}"
                        "{% if doc.content %}Content: {{ doc.content | truncatewords: 40 }}{% endif %}"
                    ),
                    "url": "https://api.mistral.ai/v1/embeddings",
                    "request": {
                        "model": settings.mistral_embedding_model,
                        "input": ["{{text}}", "{{..}}"],
                    },
                    "response": {
                        "data": [
                            {"embedding": "{{embedding}}"},
                            "{{..}}",
                        ]
                    },
                }
            },
        }
    )
    wait_task(client, settings_task)
    print("Settings applied.")

    print(f"Importing {len(documents)} documents...")
    add_task = index.add_documents(documents, primary_key="id")
    wait_task(client, add_task)
    print("Documents imported.")


if __name__ == "__main__":
    main()

