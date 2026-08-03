import json

from ai.storage import Storage
from research.hypothesis import Hypothesis
from research.parser import parse_experiment_requests


class ExperimentRequestService:
    """Coordinate experiment request generation for a single symbol."""

    def __init__(self, ai_client=None, storage=None):
        if ai_client is None:
            from ai.client import AIClient

            ai_client = AIClient()

        self.ai = ai_client
        self.storage = storage or Storage()

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
                        "source_observation_ids": list(
                            hypothesis.source_observation_ids
                        ),
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
        journal,
        hypotheses,
        observations="[]",
    ):
        """Generate, parse, store, and return experiment requests for one symbol."""

        if not symbol:
            raise ValueError("symbol is required")

        hypothesis_payload = self._render_hypotheses(hypotheses)

        response = self.ai.experiment_request(
            symbol=symbol,
            journal=journal,
            hypotheses=hypothesis_payload,
            observations=observations,
        )

        experiment_requests = parse_experiment_requests(
            symbol,
            response,
        )

        self.storage.save_experiment_requests(
            symbol,
            experiment_requests,
        )

        return experiment_requests