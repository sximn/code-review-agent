from openai import OpenAI

from env import environment


def main():
    client = OpenAI(api_key=environment.openai_api_key)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": "Make a 5-step bullet list on how to build an AI agent",
            },
        ],
    )

    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
