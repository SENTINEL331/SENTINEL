import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from config.settings import AI_MODEL

from ai.prompts import (
    SYSTEM_PROMPT,
    OBSERVATION_PROMPT,
    COMPARISON_PROMPT,
    HYPOTHESIS_PROMPT,
    EXPERIMENT_REQUEST_PROMPT,
    HYPOTHESIS_REVIEW_PROMPT,
    HYPOTHESIS_REVISION_PROPOSAL_PROMPT,
    DEMO_TRADE_CANDIDATE_PROMPT,
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
        Produce objective observations from
        a market snapshot.
        """

        prompt = OBSERVATION_PROMPT.format(
            snapshot=snapshot.to_text(),
        )

        return self.chat(
            SYSTEM_PROMPT,
            prompt,
        )

    def compare(
        self,
        previous,
        current,
    ):
        """
        Compare two observation sets.
        """

        prompt = COMPARISON_PROMPT.format(
            previous=previous,
            current=current,
        )

        return self.chat(
            SYSTEM_PROMPT,
            prompt,
        )

    def hypothesis(
        self,
        symbol,
        journal,
        observations,
        snapshot_text=None,
    ):
        """
        Request hypotheses for one symbol.
        """

        prompt_sections = [
            f"Symbol: {symbol}",
        ]

        if journal:

            prompt_sections.append(
                f"Journal Context:\n{journal}"
            )

        if snapshot_text:

            prompt_sections.append(
                f"Snapshot Evidence:\n{snapshot_text}"
            )

        prompt = HYPOTHESIS_PROMPT.format(
            journal="\n\n".join(prompt_sections),
            observations=observations,
        )

        return self.chat(
            SYSTEM_PROMPT,
            prompt,
        )

    def experiment_request(
        self,
        symbol,
        journal,
        hypotheses,
        observations="[]",
    ):
        """
        Request experiment requests for one symbol.
        """

        prompt_sections = [
            f"Symbol: {symbol}",
        ]

        if journal:

            prompt_sections.append(
                f"Journal Context:\n{journal}"
            )

        prompt = EXPERIMENT_REQUEST_PROMPT.format(
            hypotheses=hypotheses,
            journal="\n\n".join(prompt_sections),
            observations=observations,
        )

        return self.chat(
            SYSTEM_PROMPT,
            prompt,
        )

    def hypothesis_review(
        self,
        symbol,
        journal,
        hypotheses,
    ):
        """Request hypothesis reviews for one symbol."""

        prompt_sections = [
            f"Symbol: {symbol}",
        ]

        if journal:

            prompt_sections.append(
                f"Journal Context:\n{journal}"
            )

        prompt = HYPOTHESIS_REVIEW_PROMPT.format(
            hypotheses=hypotheses,
            journal="\n\n".join(prompt_sections),
        )

        return self.chat(
            SYSTEM_PROMPT,
            prompt,
        )

    def hypothesis_revision_proposals(
        self,
        symbol,
        journal,
        hypotheses,
        lifecycle_recommendations,
    ):
        """Request hypothesis revision proposals for one symbol."""

        prompt_sections = [
            f"Symbol: {symbol}",
        ]

        if journal:

            prompt_sections.append(
                f"Journal Context:\n{journal}"
            )

        prompt = HYPOTHESIS_REVISION_PROPOSAL_PROMPT.format(
            hypotheses=hypotheses,
            lifecycle_recommendations=lifecycle_recommendations,
            journal="\n\n".join(prompt_sections),
        )

        return self.chat(
            SYSTEM_PROMPT,
            prompt,
        )

    def demo_trade_candidate_generation(
        self,
        symbol,
        journal,
        qualified_candidates,
    ):
        """Request demo trade candidate proposals for one symbol."""

        prompt_sections = [
            f"Symbol: {symbol}",
        ]

        if journal:

            prompt_sections.append(
                f"Journal Context:\n{journal}"
            )

        prompt = DEMO_TRADE_CANDIDATE_PROMPT.format(
            qualified_candidates=qualified_candidates,
            journal="\n\n".join(prompt_sections),
        )

        return self.chat(
            SYSTEM_PROMPT,
            prompt,
        )