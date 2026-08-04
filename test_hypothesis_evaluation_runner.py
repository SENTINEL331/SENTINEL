import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from research.experiment import ExperimentTestType
from research.experiment_result import ExperimentMetrics
from research.experiment_result import ExperimentResult
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.runner import run_manual_hypothesis_evaluation


class ManualHypothesisEvaluationRunnerTests(unittest.TestCase):
    def test_runner_prints_hypothesis_evidence_summary(self):
        storage = Mock()

        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Momentum continuation",
            description="Test whether momentum persists.",
            status=HypothesisStatus.ACTIVE,
        )
        storage.load_hypotheses.return_value = [hypothesis]
        storage.load_experiment_requests.return_value = []

        now = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)
        completed_result = ExperimentResult(
            experiment_result_id="expr-001",
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(
                trade_count=24,
                average_return=0.0125,
                win_rate=0.60,
                extra_metrics={
                    "best_return": 0.07,
                    "worst_return": -0.03,
                },
            ),
            summary="Completed",
            created_at=now,
            updated_at=now,
        )
        storage.load_experiment_results.return_value = [completed_result]

        with patch("builtins.print") as mock_print:
            evaluations = run_manual_hypothesis_evaluation(symbol="NVDA", storage=storage)

        self.assertEqual(1, len(evaluations))
        storage.load_hypotheses.assert_called_once_with("NVDA")
        storage.load_experiment_requests.assert_called_once_with("NVDA")
        storage.load_experiment_results.assert_called_once_with("NVDA")

        mock_print.assert_any_call("Manual Hypothesis Evaluation: NVDA")
        mock_print.assert_any_call("Hypotheses Loaded : 1")
        mock_print.assert_any_call("Completed Results Loaded : 1")
        mock_print.assert_any_call("Hypotheses Evaluated : 1")
        mock_print.assert_any_call("- Momentum continuation [insufficient_data] id=hyp-001")
        mock_print.assert_any_call("  completed_experiments=1, trade_count=24")
        mock_print.assert_any_call(
            "  average_return=1.25%, win_rate=60.00%, best_return=7.00%, worst_return=-3.00%"
        )


if __name__ == "__main__":
    unittest.main()