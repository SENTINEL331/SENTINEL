from ai.client import AIClient

from ai.prompts import SYSTEM_PROMPT

from ai.client import AIClient
from ai.prompts import (
    SYSTEM_PROMPT,
    OBSERVATION_PROMPT,
)

from sentinel.sentinel import Sentinel


def main():

    sentinel = Sentinel()

    client = AIClient()

    snapshot = sentinel.get_snapshot("NVDA")

    prompt = OBSERVATION_PROMPT.format(
        snapshot=snapshot.to_text(),
    )

    print()
    print("=" * 50)
    print("AI Research Test")
    print("=" * 50)
    print()

    response = client.chat(
        SYSTEM_PROMPT,
        prompt,
    )

    print(response)


if __name__ == "__main__":
    main()