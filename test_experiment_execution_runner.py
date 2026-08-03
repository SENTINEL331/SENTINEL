import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from research.experiment import ExperimentRequest, ExperimentTestType
from research.experiment_result import ExperimentResult, ExperimentResultStatus
from research.runner import DEFAULT_SYMBOL, run_manual_experiment_execution


class ManualExperimentExecutionRunnerTests(unittest.TestCase):
    def test_runner_executes_requests_and_saves_results_for_symbol(self):
        storage = Mock()
        executor = Mock()

        matching_request = ExperimentRequest(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Validate momentum continuation",
            objective="Test whether breakout continuation persists over five sessions.",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Enter after breakout confirmation.",
            exit_conditions="Exit on invalidation.",
            time_horizon="5D",
        )
        mismatched_request = ExperimentRequest(
            experiment_request_id="expreq-002",
            hypothesis_id="hyp-002",
            hypothesis_version_id="hyp-002:v1",
            symbol="MSFT",
            title="Validate trend continuation",
            objective="Test whether trend continuation persists over five sessions.",
            test_type=ExperimentTestType.EXPLORATORY,
            entry_conditions="Enter after confirmation.",
            exit_conditions="Exit on invalidation.",
            time_horizon="5D",
        )
        storage.load_experiment_requests.return_value = [
            matching_request,
            mismatched_request,
        ]

        now = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
        execution_result = ExperimentResult(
            experiment_result_id="expr-001",
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.FAILED,
            started_at=now,
            completed_at=now,
            summary="Experiment execution is not implemented.",
            failure_reason="execution_not_implemented",
            created_at=now,
            updated_at=now,
        )
        executor.execute.return_value = execution_result

        with patch("builtins.print") as mock_print:
            results = run_manual_experiment_execution(
                symbol="NVDA",
                storage=storage,
                executor=executor,
            )

        self.assertEqual([execution_result], results)
        storage.load_experiment_requests.assert_called_once_with("NVDA")
        executor.execute.assert_called_once_with(matching_request)
        storage.save_experiment_results.assert_called_once_with("NVDA", [execution_result])

        mock_print.assert_any_call("Manual Experiment Execution: NVDA")
        mock_print.assert_any_call("Requests Loaded : 2")
        mock_print.assert_any_call("Requests Executed : 1")
        mock_print.assert_any_call("Requests Skipped : 1")
        mock_print.assert_any_call("Results Saved : 1")
        mock_print.assert_any_call("Not Implemented : 1")
        mock_print.assert_any_call(
            "- initial_backtest [failed] request_id=expreq-001 result_id=expr-001"
        )
        mock_print.assert_any_call("  reason: execution_not_implemented")

    def test_runner_handles_no_requests(self):
        storage = Mock()
        executor = Mock()

        storage.load_experiment_requests.return_value = []

        with patch("builtins.print") as mock_print:
            results = run_manual_experiment_execution(
                symbol=DEFAULT_SYMBOL,
                storage=storage,
                executor=executor,
            )

        self.assertEqual([], results)
        storage.load_experiment_requests.assert_called_once_with(DEFAULT_SYMBOL)
        executor.execute.assert_not_called()
        storage.save_experiment_results.assert_not_called()
        mock_print.assert_any_call(f"Manual Experiment Execution: {DEFAULT_SYMBOL}")
        mock_print.assert_any_call("Requests Loaded : 0")
        mock_print.assert_any_call("Requests Executed : 0")
        mock_print.assert_any_call("Requests Skipped : 0")
        mock_print.assert_any_call("Results Saved : 0")
        mock_print.assert_any_call("Not Implemented : 0")
        mock_print.assert_any_call("No experiment requests to execute.")


if __name__ == "__main__":
    unittest.main()