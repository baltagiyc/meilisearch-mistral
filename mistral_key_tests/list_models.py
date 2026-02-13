from _common import (
    build_client,
    capability_flags,
    estimated_capacity_score,
)


def main() -> None:
    client = build_client()
    model_list = client.models.list()
    models = list(model_list.data or [])

    if not models:
        print("No models returned for this API key.")
        return

    models_sorted = sorted(models, key=lambda m: m.id.lower())

    rows = []
    for model in models_sorted:
        flags = capability_flags(model.capabilities)
        score = estimated_capacity_score(model.id, flags)
        rows.append(
            {
                "id": model.id,
                "max_context_length": model.max_context_length,
                "flags": ",".join(flags) if flags else "-",
                "capacity_score": score,
            }
        )

    print("Models accessible with this API key:")
    print(f"{'MODEL_ID':45} {'MAX_CTX':8} {'CAPACITY_SCORE':14} CAPABILITIES")
    print("-" * 100)
    for row in rows:
        print(
            f"{row['id'][:45]:45} "
            f"{str(row['max_context_length'] or '-'):8} "
            f"{str(row['capacity_score']):14} "
            f"{row['flags']}"
        )

    print("\nTop estimated capacity models (heuristic, not official benchmark):")
    for row in sorted(rows, key=lambda x: x["capacity_score"], reverse=True)[:10]:
        print(f"- {row['id']} (score={row['capacity_score']})")


if __name__ == "__main__":
    main()
