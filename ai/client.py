import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from config.settings import AI_MODEL

from ai.prompts import (
    SYSTEM_PROMPT,
    OBSERVATION_PROMPT,
)


class AIClient:
    """
    Interface between Sentinel and the AI model.
    """

    def __init__(self):

        env_path = Path(__file__).resolve().parent.parent / ".env"

        load_dotenv(env_path)

        api_key = os.getenv("OPENAI_API_KEY")

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

    def observe(
        self,
        snapshot,
    ):
        """
        Ask the AI to produce objective observations
        from a market snapshot.
        """

        prompt = OBSERVATION_PROMPT.format(
            snapshot=snapshot.to_text(),
        )

        return self.chat(
            SYSTEM_PROMPT,
            prompt,
        )