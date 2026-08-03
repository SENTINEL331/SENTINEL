import unittest
from unittest.mock import Mock, patch

from research.experiment import (
    ExperimentRequest,
    ExperimentRequestStatus,
    ExperimentTestType,
)
from research.hypothesis import Hypothesis, HypothesisStatus
from research.observation import Observation
from research.runner import (
    DEFAULT_SYMBOL,
    run_manual_experiment_request_generation,
)


class ManualExperimentRequestRunnerTests(unittest.TestCase):
    def test_runner_loads_context_and_generates_one_symbol_requests(self):
        journal = Mock()
        storage = Mock()
        experiment_request_service = Mock()

        journal.build.return_value = "Research Journal: NVDA"

        hypotheses = [
            Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Momentum continuation",
                description="Price strength may continue after a breakout.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.75,
                source_observation_ids=("obs-1",),
            )
        ]
        storage.load_hypotheses.return_value = hypotheses
        storage.load_observations.return_value = [
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

        experiment_requests = [
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
        experiment_request_service.generate_for_symbol.return_value = experiment_requests

        with patch("builtins.print") as mock_print:
            result = run_manual_experiment_request_generation(
                symbol="NVDA",
                journal=journal,
                storage=storage,
                experiment_request_service=experiment_request_service,
            )

        self.assertEqual(experiment_requests, result)
        journal.build.assert_called_once_with("NVDA")
        storage.load_hypotheses.assert_called_once_with("NVDA")
        storage.load_observations.assert_called_once_with("NVDA")
        experiment_request_service.generate_for_symbol.assert_called_once()

        call_kwargs = experiment_request_service.generate_for_symbol.call_args.kwargs
        self.assertEqual("NVDA", call_kwargs["symbol"])
        self.assertEqual("Research Journal: NVDA", call_kwargs["journal"])
        self.assertEqual(hypotheses, call_kwargs["hypotheses"])
        self.assertIn("obs-1", call_kwargs["observations"])

        mock_print.assert_any_call("Manual Experiment Request Generation: NVDA")
        mock_print.assert_any_call("Hypotheses Loaded : 1")
        mock_print.assert_any_call("Experiment Requests Generated : 1")
        mock_print.assert_any_call(
            "- Validate momentum continuation [proposed] test_type=initial_backtest"
        )
        mock_print.assert_any_call(
            "  objective: Test whether breakout continuation persists over five sessions."
        )

    def test_runner_uses_default_symbol_and_handles_empty_output(self):
        journal = Mock()
        storage = Mock()
        experiment_request_service = Mock()

        journal.build.return_value = f"Research Journal: {DEFAULT_SYMBOL}"
        storage.load_hypotheses.return_value = []
        storage.load_observations.return_value = []
        experiment_request_service.generate_for_symbol.return_value = []

        with patch("builtins.print") as mock_print:
            result = run_manual_experiment_request_generation(
                journal=journal,
                storage=storage,
                experiment_request_service=experiment_request_service,
            )

        self.assertEqual([], result)
        journal.build.assert_called_once_with(DEFAULT_SYMBOL)
        storage.load_hypotheses.assert_called_once_with(DEFAULT_SYMBOL)
        storage.load_observations.assert_called_once_with(DEFAULT_SYMBOL)
        mock_print.assert_any_call(
            f"Manual Experiment Request Generation: {DEFAULT_SYMBOL}"
        )
        mock_print.assert_any_call("Hypotheses Loaded : 0")
        mock_print.assert_any_call("Experiment Requests Generated : 0")
        mock_print.assert_any_call("No experiment requests generated.")


if __name__ == "__main__":
    unittest.main()