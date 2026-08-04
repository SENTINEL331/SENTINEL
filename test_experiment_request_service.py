import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from ai.experiment_request_service import ExperimentRequestService
from research.experiment import (
    ExperimentRequest,
    ExperimentRequestStatus,
    ExperimentTestType,
)
from research.hypothesis import Hypothesis, HypothesisStatus


class ExperimentRequestServiceTests(unittest.TestCase):
    def test_generate_for_symbol_calls_ai_parses_and_saves(self):
        ai_client = Mock()
        storage = Mock()

        ai_client.experiment_request.return_value = """
        {
            "experiment_requests": [
                {
                    "experiment_request_id": "expreq-001",
                    "hypothesis_id": "hyp-001",
                    "hypothesis_version_id": "hyp-001:v1",
                    "symbol": "NVDA",
                    "title": "Validate momentum continuation",
                    "objective": "Test whether breakout continuation persists over the next five sessions.",
                    "test_type": "initial_backtest",
                    "entry_conditions": "Enter after breakout close above prior 20-day high.",
                    "machine_readable_entry_conditions": [
                        {
                            "field": "Close",
                            "operator": ">",
                            "other_field": "EMA_20"
                        }
                    ],
                    "exit_conditions": "Exit on stop breach or five-session horizon.",
                    "time_horizon": "5D",
                    "forward_horizon": 5,
                    "status": "proposed",
                    "source_observation_ids": ["obs-1"],
                    "created_at": "2026-08-03T00:00:00+00:00",
                    "updated_at": "2026-08-03T00:00:00+00:00"
                }
            ]
        }
        """

        service = ExperimentRequestService(ai_client=ai_client, storage=storage)
        hypotheses = [
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

        requests = service.generate_for_symbol(
            symbol="NVDA",
            journal="Existing journal context.",
            hypotheses=hypotheses,
            observations='[{"observation_id": "obs-1"}]',
        )

        self.assertEqual(1, len(requests))
        self.assertIsInstance(requests[0], ExperimentRequest)
        self.assertEqual("expreq-001", requests[0].experiment_request_id)
        self.assertEqual("hyp-001", requests[0].hypothesis_id)
        self.assertEqual("hyp-001:v1", requests[0].hypothesis_version_id)
        self.assertEqual(ExperimentTestType.INITIAL_BACKTEST, requests[0].test_type)
        self.assertEqual(ExperimentRequestStatus.PROPOSED, requests[0].status)
        self.assertEqual(("obs-1",), requests[0].source_observation_ids)
        self.assertEqual(
            "EMA_20",
            requests[0].machine_readable_entry_conditions[0]["other_field"],
        )
        self.assertEqual(5, requests[0].forward_horizon)
        self.assertEqual(
            datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc),
            requests[0].created_at,
        )

        ai_client.experiment_request.assert_called_once()
        storage.save_experiment_requests.assert_called_once_with("NVDA", requests)

        call_kwargs = ai_client.experiment_request.call_args.kwargs
        self.assertEqual("NVDA", call_kwargs["symbol"])
        self.assertEqual("Existing journal context.", call_kwargs["journal"])
        self.assertIn("hyp-001", call_kwargs["hypotheses"])
        self.assertIn("Momentum continuation", call_kwargs["hypotheses"])
        self.assertEqual('[{"observation_id": "obs-1"}]', call_kwargs["observations"])

    def test_generate_for_symbol_rejects_invalid_hypothesis_inputs(self):
        service = ExperimentRequestService(ai_client=Mock(), storage=Mock())

        with self.assertRaisesRegex(
            ValueError,
            "hypotheses must be a JSON string, dicts, or Hypothesis objects",
        ):
            service.generate_for_symbol(
                symbol="NVDA",
                journal="Existing journal context.",
                hypotheses=[123],
            )


if __name__ == "__main__":
    unittest.main()