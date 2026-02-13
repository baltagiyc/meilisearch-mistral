from _common import build_client


def main() -> None:
    client = build_client()
    model = "mistral-medium-latest"

    chat_response = client.chat.complete(
        model=model,
        messages=[
            {
                "role": "user",
                "content": "Say only: API key is valid.",
            },
        ],
    )
    print(chat_response.choices[0].message.content)


if __name__ == "__main__":
    main()
