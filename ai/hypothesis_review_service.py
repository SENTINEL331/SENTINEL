import json

from ai.journal import ResearchJournal
from ai.storage import Storage
from research.hypothesis import Hypothesis
from research.parser import parse_hypothesis_reviews


class HypothesisReviewService:
    """Coordinate hypothesis review generation for a single symbol."""

    def __init__(self, ai_client=None, storage=None, journal_builder=None):
        if ai_client is None:
            from ai.client import AIClient

            ai_client = AIClient()

        self.ai = ai_client
        self.storage = storage or Storage()
        self.journal_builder = journal_builder or ResearchJournal()
        self.journal_builder.storage = self.storage

    def _render_hypotheses(self, hypotheses):
        if isinstance(hypotheses, str):
            return hypotheses

        serialized = []

        for hypothesis in hypotheses:
            if isinstance(hypothesis, Hypothesis):
                serialized.append(
                    {
                        "hypothesis_id": hypothesis.hypothesis_id,
                        "symbol": hypothesis.symbol,
                        "title": hypothesis.title,
                        "description": hypothesis.description,
                        "status": hypothesis.status.value,
                        "confidence": hypothesis.confidence,
                        "experiment_refs": list(hypothesis.experiment_refs),
                    }
                )
                continue

            if isinstance(hypothesis, dict):
                serialized.append(hypothesis)
                continue

            raise ValueError("hypotheses must be a JSON string, dicts, or Hypothesis objects")

        return json.dumps(serialized, indent=4)

    def generate_for_symbol(
        self,
        symbol,
        journal=None,
        hypotheses=None,
    ):
        """Generate, parse, store, and return hypothesis reviews for one symbol."""

        if not symbol:
            raise ValueError("symbol is required")

        resolved_hypotheses = hypotheses if hypotheses is not None else self.storage.load_hypotheses(symbol)
        hypothesis_payload = self._render_hypotheses(resolved_hypotheses)

        resolved_journal = journal if journal is not None else self.journal_builder.build(symbol)

        response = self.ai.hypothesis_review(
            symbol=symbol,
            journal=resolved_journal,
            hypotheses=hypothesis_payload,
        )

        reviews = parse_hypothesis_reviews(symbol, response)

        self.storage.save_hypothesis_reviews(symbol, reviews)

        return reviews
