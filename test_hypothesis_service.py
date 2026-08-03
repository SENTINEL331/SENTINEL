import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from ai.hypothesis_service import HypothesisService
from research.hypothesis import Hypothesis, HypothesisStatus
from research.observation import Observation


class HypothesisServiceTests(unittest.TestCase):
    def test_generate_for_symbol_calls_ai_parses_and_saves(self):
        ai_client = Mock()
        storage = Mock()

        ai_client.hypothesis.return_value = """
        {
            "hypotheses": [
                {
                    "hypothesis_id": "hyp-001",
                    "symbol": "NVDA",
                    "title": "Momentum continuation",
                    "description": "Price strength may continue after an earnings-driven breakout.",
                    "status": "active",
                    "confidence": 0.75,
                    "source_observation_ids": ["obs-1"],
                    "parent_hypothesis_id": null,
                    "lineage_hypothesis_ids": [],
                    "experiment_refs": [],
                    "created_at": "2026-08-03T00:00:00+00:00",
                    "updated_at": "2026-08-03T00:00:00+00:00"
                }
            ]
        }
        """

        service = HypothesisService(ai_client=ai_client, storage=storage)
        observations = [
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
                schema_version="1.0",
            )
        ]

        hypotheses = service.generate_for_symbol(
            symbol="NVDA",
            journal="Existing journal context.",
            observations=observations,
            snapshot_text="Snapshot summary.",
        )

        self.assertEqual(1, len(hypotheses))
        self.assertIsInstance(hypotheses[0], Hypothesis)
        self.assertEqual("hyp-001", hypotheses[0].hypothesis_id)
        self.assertEqual(HypothesisStatus.ACTIVE, hypotheses[0].status)
        self.assertEqual(0.75, hypotheses[0].confidence)
        self.assertEqual(("obs-1",), hypotheses[0].source_observation_ids)
        self.assertEqual(
            datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc),
            hypotheses[0].created_at,
        )

        ai_client.hypothesis.assert_called_once()
        storage.save_hypotheses.assert_called_once_with("NVDA", hypotheses)

        call_kwargs = ai_client.hypothesis.call_args.kwargs
        self.assertEqual("NVDA", call_kwargs["symbol"])
        self.assertEqual("Existing journal context.", call_kwargs["journal"])
        self.assertEqual("Snapshot summary.", call_kwargs["snapshot_text"])
        self.assertIn("obs-1", call_kwargs["observations"])
        self.assertIn("Price closed above the configured breakout range.", call_kwargs["observations"])

    def test_generate_for_symbol_rejects_invalid_observation_inputs(self):
        service = HypothesisService(ai_client=Mock(), storage=Mock())

        with self.assertRaisesRegex(
            ValueError,
            "observations must be a JSON string, dicts, or Observation objects",
        ):
            service.generate_for_symbol(
                symbol="NVDA",
                journal="Existing journal context.",
                observations=[123],
            )


if __name__ == "__main__":
    unittest.main()