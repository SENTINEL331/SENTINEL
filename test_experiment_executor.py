import unittest

import pandas as pd

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
            entry_conditions=(
                '[{"field": "Close", "operator": ">", "value": 100.0}]'
            ),
            exit_conditions="Exit on stop breach or five-session horizon.",
            time_horizon="1D",
        )
        feature_data = pd.DataFrame(
            {"Close": [99.0, 101.0, 103.0]},
            index=pd.Index(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )

        executor = ExperimentExecutor()
        result = executor.execute(request, feature_data)

        self.assertIsInstance(result, ExperimentResult)
        self.assertTrue(result.experiment_result_id.startswith("expr-"))
        self.assertEqual("expreq-001", result.experiment_request_id)
        self.assertEqual("hyp-001", result.hypothesis_id)
        self.assertEqual("NVDA", result.symbol)
        self.assertEqual(ExperimentTestType.INITIAL_BACKTEST, result.test_type)
        self.assertEqual(ExperimentResultStatus.COMPLETED, result.status)
        self.assertEqual(1, result.metrics.trade_count)

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

        self.assertEqual(ExperimentResultStatus.NOT_IMPLEMENTED, result.status)
        self.assertEqual("historical_feature_data_required", result.failure_reason)
        self.assertIn("not implemented", result.summary.lower())
        self.assertIsNotNone(result.started_at)
        self.assertIsNotNone(result.completed_at)
        self.assertEqual(result.started_at, result.completed_at)

    def test_execute_marks_unsupported_machine_unreadable_request_not_implemented(self):
        request = ExperimentRequest(
            experiment_request_id="expreq-003",
            hypothesis_id="hyp-003",
            hypothesis_version_id="hyp-003:v1",
            symbol="NVDA",
            title="Validate pullback continuation",
            objective="Test whether pullbacks recover in trend continuation setups.",
            test_type=ExperimentTestType.EXPLORATORY,
            entry_conditions="Enter after pullback confirmation.",
            exit_conditions="Exit on invalidation.",
            time_horizon="3D",
        )
        feature_data = pd.DataFrame({"Close": [100.0, 101.0]})

        executor = ExperimentExecutor()
        result = executor.execute(request, feature_data)

        self.assertEqual(ExperimentResultStatus.NOT_IMPLEMENTED, result.status)
        self.assertEqual("unsupported_experiment_request", result.failure_reason)
        self.assertIn("valid json", result.summary.lower())

    def test_execute_marks_actual_execution_errors_failed(self):
        request = ExperimentRequest(
            experiment_request_id="expreq-004",
            hypothesis_id="hyp-004",
            hypothesis_version_id="hyp-004:v1",
            symbol="NVDA",
            title="Validate momentum continuation",
            objective="Test whether breakouts continue higher over one session.",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions=(
                '[{"field": "Close", "operator": ">", "value": 100.0}]'
            ),
            exit_conditions="Exit after one session.",
            time_horizon="1D",
        )
        feature_data = pd.DataFrame({"RSI_14": [45.0, 55.0]})

        executor = ExperimentExecutor()
        result = executor.execute(request, feature_data)

        self.assertEqual(ExperimentResultStatus.FAILED, result.status)
        self.assertEqual("basic_backtest_execution_failed", result.failure_reason)
        self.assertIn("unknown field: close", result.summary.lower())


if __name__ == "__main__":
    unittest.main()