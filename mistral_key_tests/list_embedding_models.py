from _common import build_client


def is_embedding_model(model: object) -> bool:
    content = " ".join(
        [
            str(getattr(model, "id", "") or ""),
            str(getattr(model, "name", "") or ""),
            str(getattr(model, "description", "") or ""),
        ]
    ).lower()

    embedding_keywords = ("embed", "embedding", "mistral-embed", "e5")
    return any(keyword in content for keyword in embedding_keywords)


def main() -> None:
    client = build_client()
    model_list = client.models.list()
    models = list(model_list.data or [])

    embedding_models = [model for model in models if is_embedding_model(model)]
    embedding_models.sort(key=lambda m: m.id.lower())

    if not embedding_models:
        print("No embedding models detected for this API key.")
        return

    print("Embedding models for RAG:")
    print(f"{'MODEL_ID':45} {'MAX_CTX':8} DESCRIPTION")
    print("-" * 90)

    for model in embedding_models:
        description = str(getattr(model, "description", "") or "-").replace("\n", " ")
        print(
            f"{model.id[:45]:45} "
            f"{str(model.max_context_length or '-'):8} "
            f"{description}"
        )


if __name__ == "__main__":
    main()
