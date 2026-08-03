import json

from ai.storage import Storage
from research.observation import Observation
from research.parser import parse_hypotheses


class HypothesisService:
    """Coordinate hypothesis generation for a single symbol."""

    def __init__(self, ai_client=None, storage=None):
        if ai_client is None:
            from ai.client import AIClient

            ai_client = AIClient()

        self.ai = ai_client
        self.storage = storage or Storage()

    def _render_observations(self, observations):
        if isinstance(observations, str):
            return observations

        serialized = []

        for observation in observations:
            if isinstance(observation, Observation):
                serialized.append(
                    {
                        "observation_id": observation.observation_id,
                        "statement": observation.statement,
                        "importance": observation.importance,
                        "evidence_refs": observation.evidence_refs,
                    }
                )
                continue

            if isinstance(observation, dict):
                serialized.append(observation)
                continue

            raise ValueError("observations must be a JSON string, dicts, or Observation objects")

        return json.dumps(serialized, indent=4)

    def generate_for_symbol(
        self,
        symbol,
        journal,
        observations,
        snapshot_text=None,
    ):
        """Generate, parse, store, and return hypotheses for one symbol."""

        if not symbol:
            raise ValueError("symbol is required")

        observation_payload = self._render_observations(observations)

        response = self.ai.hypothesis(
            symbol=symbol,
            journal=journal,
            observations=observation_payload,
            snapshot_text=snapshot_text,
        )

        hypotheses = parse_hypotheses(
            symbol,
            response,
        )

        self.storage.save_hypotheses(
            symbol,
            hypotheses,
        )

        return hypotheses