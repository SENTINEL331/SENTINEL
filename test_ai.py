from ai.client import AIClient

from ai.prompts import SYSTEM_PROMPT


def main():

    client = AIClient()

    print()
    print("=" * 50)
    print("Testing AI Connection")
    print("=" * 50)
    print()

    response = client.chat(

        SYSTEM_PROMPT,

        "State your mission in one sentence.",

    )

    print(response)


if __name__ == "__main__":
    main()