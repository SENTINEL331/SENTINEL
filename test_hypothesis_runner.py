import unittest
from unittest.mock import Mock, call, patch

from research.hypothesis import Hypothesis, HypothesisStatus
from research.runner import DEFAULT_SYMBOL, run_manual_hypothesis_generation


class ManualHypothesisRunnerTests(unittest.TestCase):
    def test_runner_loads_context_and_generates_one_symbol_hypotheses(self):
        sentinel = Mock()
        journal = Mock()
        storage = Mock()
        hypothesis_service = Mock()

        snapshot = Mock()
        snapshot.to_text.return_value = "Snapshot text for NVDA"
        sentinel.get_snapshot.return_value = snapshot

        journal.build.return_value = "Research Journal: NVDA"
        observations = [Mock(statement="Observation 1")]
        storage.load_observations.return_value = observations

        hypotheses = [
            Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Momentum continuation",
                description="Price strength may continue after a breakout.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.75,
            )
        ]
        hypothesis_service.generate_for_symbol.return_value = hypotheses

        with patch("builtins.print") as mock_print:
            result = run_manual_hypothesis_generation(
                symbol="NVDA",
                sentinel=sentinel,
                journal=journal,
                storage=storage,
                hypothesis_service=hypothesis_service,
            )

        self.assertEqual(hypotheses, result)
        sentinel.get_snapshot.assert_called_once_with("NVDA")
        journal.build.assert_called_once_with("NVDA")
        storage.load_observations.assert_called_once_with("NVDA")
        hypothesis_service.generate_for_symbol.assert_called_once_with(
            symbol="NVDA",
            journal="Research Journal: NVDA",
            observations=observations,
            snapshot_text="Snapshot text for NVDA",
        )

        mock_print.assert_any_call("Manual Hypothesis Generation: NVDA")
        mock_print.assert_any_call("Observations Loaded : 1")
        mock_print.assert_any_call("Hypotheses Generated : 1")
        mock_print.assert_any_call("- Momentum continuation [active] confidence=0.75")

    def test_runner_uses_default_symbol_and_handles_empty_output(self):
        sentinel = Mock()
        journal = Mock()
        storage = Mock()
        hypothesis_service = Mock()

        snapshot = Mock()
        snapshot.to_text.return_value = f"Snapshot text for {DEFAULT_SYMBOL}"
        sentinel.get_snapshot.return_value = snapshot
        journal.build.return_value = f"Research Journal: {DEFAULT_SYMBOL}"
        storage.load_observations.return_value = []
        hypothesis_service.generate_for_symbol.return_value = []

        with patch("builtins.print") as mock_print:
            result = run_manual_hypothesis_generation(
                sentinel=sentinel,
                journal=journal,
                storage=storage,
                hypothesis_service=hypothesis_service,
            )

        self.assertEqual([], result)
        sentinel.get_snapshot.assert_called_once_with(DEFAULT_SYMBOL)
        mock_print.assert_any_call(f"Manual Hypothesis Generation: {DEFAULT_SYMBOL}")
        mock_print.assert_any_call("Observations Loaded : 0")
        mock_print.assert_any_call("Hypotheses Generated : 0")
        mock_print.assert_any_call("No hypotheses generated.")


if __name__ == "__main__":
    unittest.main()