import unittest
from unittest.mock import Mock

from ai.journal import ResearchJournal
from research.experiment import (
    ExperimentRequest,
    ExperimentRequestStatus,
    ExperimentTestType,
)
from research.hypothesis import Hypothesis, HypothesisStatus
from research.observation import Observation


class ResearchJournalOutputTests(unittest.TestCase):
    def test_build_includes_experiment_requests_section(self):
        journal = ResearchJournal()
        journal.storage = Mock()

        journal.storage.load_observations.return_value = [
            Observation(
                observation_id="obs-1",
                symbol_id="NVDA",
                statement="Price closed above the configured breakout range.",
                evidence_refs=["snapshot:NVDA:2026-08-03"],
                importance=1,
                effective_time="2026-08-03",
                created_at="2026-08-03T00:00:00+00:00",
                research_cycle_id="cycle-001",
                ai_call_id="ai-001",
            )
        ]
        journal.storage.load_hypotheses.return_value = [
            Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Momentum continuation",
                description="Price strength may continue after an earnings-driven breakout.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.75,
                source_observation_ids=("obs-1",),
            )
        ]
        journal.storage.load_experiment_requests.return_value = [
            ExperimentRequest(
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                hypothesis_version_id="hyp-001:v1",
                symbol="NVDA",
                title="Validate momentum continuation",
                objective="Test whether breakout continuation persists over five sessions.",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                entry_conditions="Enter after breakout close above prior 20-day high.",
                exit_conditions="Exit on stop breach or five-session horizon.",
                time_horizon="5D",
                status=ExperimentRequestStatus.PROPOSED,
                source_observation_ids=("obs-1",),
            )
        ]

        result = journal.build("NVDA")

        self.assertIn("Observations", result)
        self.assertIn("Price closed above the configured breakout range.", result)
        self.assertIn("Hypotheses", result)
        self.assertIn(
            "- Momentum continuation [active] confidence=0.75 id=hyp-001",
            result,
        )
        self.assertIn("Experiment Requests", result)
        self.assertIn(
            "- Validate momentum continuation [proposed] test_type=initial_backtest id=expreq-001",
            result,
        )
        self.assertIn(
            "  objective: Test whether breakout continuation persists over five sessions.",
            result,
        )

    def test_build_shows_empty_experiment_requests_state(self):
        journal = ResearchJournal()
        journal.storage = Mock()

        journal.storage.load_observations.return_value = []
        journal.storage.load_hypotheses.return_value = []
        journal.storage.load_experiment_requests.return_value = []

        result = journal.build("NVDA")

        self.assertIn("Observations", result)
        self.assertIn("No previous observations.", result)
        self.assertIn("Hypotheses", result)
        self.assertIn("No active hypotheses.", result)
        self.assertIn("Experiment Requests", result)
        self.assertIn("No experiment requests.", result)


if __name__ == "__main__":
    unittest.main()