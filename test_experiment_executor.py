import unittest

from research.executor import ExperimentExecutor
from research.experiment import ExperimentRequest, ExperimentTestType
from research.experiment_result import ExperimentResult, ExperimentResultStatus


class ExperimentExecutorTests(unittest.TestCase):
    def test_execute_returns_experiment_result(self):
        request = ExperimentRequest(
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
        )

        executor = ExperimentExecutor()
        result = executor.execute(request)

        self.assertIsInstance(result, ExperimentResult)
        self.assertTrue(result.experiment_result_id.startswith("expr-"))
        self.assertEqual("expreq-001", result.experiment_request_id)
        self.assertEqual("hyp-001", result.hypothesis_id)
        self.assertEqual("NVDA", result.symbol)
        self.assertEqual(ExperimentTestType.INITIAL_BACKTEST, result.test_type)

    def test_execute_marks_not_implemented_clearly(self):
        request = ExperimentRequest(
            experiment_request_id="expreq-002",
            hypothesis_id="hyp-002",
            hypothesis_version_id="hyp-002:v1",
            symbol="NVDA",
            title="Validate pullback continuation",
            objective="Test whether pullbacks recover in trend continuation setups.",
            test_type=ExperimentTestType.EXPLORATORY,
            entry_conditions="Enter after pullback confirmation.",
            exit_conditions="Exit on invalidation.",
            time_horizon="3D",
        )

        executor = ExperimentExecutor()
        result = executor.execute(request)

        self.assertEqual(ExperimentResultStatus.FAILED, result.status)
        self.assertEqual("execution_not_implemented", result.failure_reason)
        self.assertIn("not implemented", result.summary.lower())
        self.assertIsNotNone(result.started_at)
        self.assertIsNotNone(result.completed_at)
        self.assertEqual(result.started_at, result.completed_at)


if __name__ == "__main__":
    unittest.main()