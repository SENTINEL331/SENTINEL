import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from config.settings import AI_MODEL


class AIClient:
    """
    Interface between Sentinel and the AI model.
    """

    def __init__(self):
        """Create the AI client."""

        #
        # Load .env from the Sentinel project root.
        #

        env_path = Path(__file__).resolve().parent.parent / ".env"

        print()
        print("AI Client")
        print("-" * 50)
        print(f"Looking for .env at:")
        print(env_path)

        loaded = load_dotenv(env_path)

        print()
        print(f".env loaded : {loaded}")

        api_key = os.getenv("OPENAI_API_KEY")

        print(f"API key found : {api_key is not None}")

        if not api_key:

            raise ValueError(
                "OPENAI_API_KEY not found in .env"
            )

        self.client = OpenAI(
            api_key=api_key,
        )

        self.model = AI_MODEL

    def chat(
        self,
        system_prompt,
        user_prompt,
    ):
        """
        Send a conversation to the AI and
        return the response.
        """

        response = self.client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        )

        return response.output_text