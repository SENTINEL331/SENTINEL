import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

import pandas as pd

from research.executor import ExperimentExecutor
from research.experiment import ExperimentRequest, ExperimentTestType
from research.experiment_result import ExperimentResult, ExperimentResultStatus


class ExperimentExecutorTests(unittest.TestCase):
    def test_execute_loads_historical_data_and_runs_basic_backtest(self):
        request = ExperimentRequest(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Validate momentum continuation",
            objective="Test whether breakout continuation persists over five sessions.",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Enter when close is above 100.",
            machine_readable_entry_conditions=(
                {"field": "Close", "operator": ">", "value": 100.0},
            ),
            exit_conditions="Exit on stop breach or five-session horizon.",
            time_horizon="1D",
            forward_horizon=1,
        )
        historical_data = pd.DataFrame(
            {"Close": [99.0, 101.0, 103.0]},
            index=pd.Index(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )
        historical_data_loader = Mock()
        historical_data_loader.load.return_value = historical_data
        basic_backtest_runner = Mock()
        completed_result = ExperimentResult(
            experiment_result_id="expr-001",
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
            completed_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
            summary="Basic backtest completed.",
            created_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
        )
        basic_backtest_runner.run.return_value = completed_result

        executor = ExperimentExecutor(
            basic_backtest_runner=basic_backtest_runner,
            historical_data_loader=historical_data_loader,
        )
        result = executor.execute(request)

        self.assertIsInstance(result, ExperimentResult)
        self.assertEqual("expreq-001", result.experiment_request_id)
        self.assertEqual("hyp-001", result.hypothesis_id)
        self.assertEqual("NVDA", result.symbol)
        self.assertEqual(ExperimentTestType.INITIAL_BACKTEST, result.test_type)
        self.assertEqual(ExperimentResultStatus.COMPLETED, result.status)
        historical_data_loader.load.assert_called_once_with("NVDA")
        runner_request = basic_backtest_runner.run.call_args.args[0]
        self.assertEqual('[{"field": "Close", "operator": ">", "value": 100.0}]', runner_request.entry_conditions)
        self.assertEqual("1D", runner_request.time_horizon)
        basic_backtest_runner.run.assert_called_once_with(runner_request, historical_data)

    def test_execute_marks_unsupported_machine_unreadable_request_not_implemented(self):
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
        historical_data_loader = Mock()

        executor = ExperimentExecutor(historical_data_loader=historical_data_loader)
        result = executor.execute(request)

        self.assertEqual(ExperimentResultStatus.NOT_IMPLEMENTED, result.status)
        self.assertEqual("unsupported_experiment_request", result.failure_reason)
        self.assertIn("machine_readable_entry_conditions are required", result.summary)
        self.assertIsNotNone(result.started_at)
        self.assertIsNotNone(result.completed_at)
        self.assertEqual(result.started_at, result.completed_at)
        historical_data_loader.load.assert_not_called()

    def test_execute_marks_missing_historical_data_not_implemented(self):
        request = ExperimentRequest(
            experiment_request_id="expreq-003",
            hypothesis_id="hyp-003",
            hypothesis_version_id="hyp-003:v1",
            symbol="NVDA",
            title="Validate pullback continuation",
            objective="Test whether breakouts continue higher over one session.",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Enter when close is above 100.",
            machine_readable_entry_conditions=(
                {"field": "Close", "operator": ">", "value": 100.0},
            ),
            exit_conditions="Exit after one session.",
            time_horizon="1D",
            forward_horizon=1,
        )
        historical_data_loader = Mock()
        historical_data_loader.load.side_effect = FileNotFoundError("missing history")

        executor = ExperimentExecutor(historical_data_loader=historical_data_loader)
        result = executor.execute(request)

        self.assertEqual(ExperimentResultStatus.NOT_IMPLEMENTED, result.status)
        self.assertEqual("historical_data_unavailable", result.failure_reason)
        self.assertIn("historical data is unavailable", result.summary.lower())
        historical_data_loader.load.assert_called_once_with("NVDA")

    def test_execute_marks_actual_execution_errors_failed(self):
        request = ExperimentRequest(
            experiment_request_id="expreq-004",
            hypothesis_id="hyp-004",
            hypothesis_version_id="hyp-004:v1",
            symbol="NVDA",
            title="Validate momentum continuation",
            objective="Test whether breakouts continue higher over one session.",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Enter when close is above 100.",
            machine_readable_entry_conditions=(
                {"field": "Close", "operator": ">", "value": 100.0},
            ),
            exit_conditions="Exit after one session.",
            time_horizon="1D",
            forward_horizon=1,
        )
        historical_data = pd.DataFrame({"RSI_14": [45.0, 55.0]})
        historical_data_loader = Mock()
        historical_data_loader.load.return_value = historical_data
        basic_backtest_runner = Mock()
        basic_backtest_runner.run.side_effect = ValueError("missing required price column: Close")

        executor = ExperimentExecutor(
            basic_backtest_runner=basic_backtest_runner,
            historical_data_loader=historical_data_loader,
        )
        result = executor.execute(request)

        self.assertEqual(ExperimentResultStatus.FAILED, result.status)
        self.assertIn("basic_backtest_runner failed", result.failure_reason)
        self.assertIn("ValueError", result.failure_reason)
        self.assertIn("missing required price column", result.failure_reason)
        self.assertIn("basic backtest execution failed in basic_backtest_runner", result.summary.lower())

    def test_execute_failure_reason_includes_component_name_from_runner(self):
        request = ExperimentRequest(
            experiment_request_id="expreq-006",
            hypothesis_id="hyp-006",
            hypothesis_version_id="hyp-006:v1",
            symbol="NVDA",
            title="Validate momentum continuation",
            objective="Test whether breakouts continue higher over one session.",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Enter when close is above 100.",
            machine_readable_entry_conditions=(
                {"field": "Close", "operator": ">", "value": 100.0},
            ),
            exit_conditions="Exit after one session.",
            time_horizon="1D",
            forward_horizon=1,
        )
        historical_data = pd.DataFrame({"RSI_14": [45.0, 55.0]})
        historical_data_loader = Mock()
        historical_data_loader.load.return_value = historical_data

        executor = ExperimentExecutor(historical_data_loader=historical_data_loader)
        result = executor.execute(request)

        self.assertEqual(ExperimentResultStatus.FAILED, result.status)
        self.assertIn("setup_scanner failed", result.failure_reason)
        self.assertIn("unknown field: Close".lower(), result.failure_reason.lower())

    def test_execute_marks_empty_historical_data_not_implemented(self):
        request = ExperimentRequest(
            experiment_request_id="expreq-005",
            hypothesis_id="hyp-005",
            hypothesis_version_id="hyp-005:v1",
            symbol="NVDA",
            title="Validate momentum continuation",
            objective="Test whether breakouts continue higher over one session.",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Enter when close is above 100.",
            machine_readable_entry_conditions=(
                {"field": "Close", "operator": ">", "value": 100.0},
            ),
            exit_conditions="Exit after one session.",
            time_horizon="1D",
            forward_horizon=1,
        )
        historical_data_loader = Mock()
        historical_data_loader.load.return_value = pd.DataFrame()
        basic_backtest_runner = Mock()

        executor = ExperimentExecutor(
            basic_backtest_runner=basic_backtest_runner,
            historical_data_loader=historical_data_loader,
        )
        result = executor.execute(request)

        self.assertEqual(ExperimentResultStatus.NOT_IMPLEMENTED, result.status)
        self.assertEqual("historical_data_unavailable", result.failure_reason)
        basic_backtest_runner.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()