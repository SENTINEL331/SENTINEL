import unittest
from datetime import datetime, timezone
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from ai.storage import Storage
from research.experiment import ExperimentRequest, ExperimentTestType
from research.experiment import ExperimentRequestStatus
from research.experiment_result import ExperimentMetrics
from research.experiment_result import ExperimentResult, ExperimentResultStatus
from research.runner import DEFAULT_SYMBOL, run_manual_experiment_execution


class ManualExperimentExecutionRunnerTests(unittest.TestCase):
    def test_runner_executes_requests_and_saves_results_for_symbol(self):
        storage = Mock()
        executor = Mock()

        executable_request = ExperimentRequest(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Validate momentum continuation",
            objective="Test whether breakout continuation persists over five sessions.",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Enter after breakout confirmation.",
            machine_readable_entry_conditions=(
                {"field": "Close", "operator": ">", "value": 100.0},
            ),
            exit_conditions="Exit on invalidation.",
            time_horizon="5D",
            forward_horizon=5,
        )
        legacy_non_executable_request = ExperimentRequest(
            experiment_request_id="expreq-legacy-001",
            hypothesis_id="hyp-legacy-001",
            hypothesis_version_id="hyp-legacy-001:v1",
            symbol="NVDA",
            title="Legacy request without structured fields",
            objective="Legacy objective",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Legacy entry",
            exit_conditions="Legacy exit",
            time_horizon="5D",
        )
        obsolete_request = ExperimentRequest(
            experiment_request_id="expreq-obsolete-001",
            hypothesis_id="hyp-obsolete-001",
            hypothesis_version_id="hyp-obsolete-001:v1",
            symbol="NVDA",
            title="Obsolete request",
            objective="Obsolete objective",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Entry",
            machine_readable_entry_conditions=(
                {"field": "Close", "operator": ">", "value": 100.0},
            ),
            exit_conditions="Exit",
            time_horizon="5D",
            forward_horizon=5,
            status=ExperimentRequestStatus.REJECTED,
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
            executable_request,
            legacy_non_executable_request,
            obsolete_request,
            mismatched_request,
        ]

        now = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
        execution_result = ExperimentResult(
            experiment_result_id="expr-001",
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.NOT_IMPLEMENTED,
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
        executor.execute.assert_called_once_with(executable_request)
        storage.save_experiment_results.assert_called_once_with("NVDA", [execution_result])

        mock_print.assert_any_call("Manual Experiment Execution: NVDA")
        mock_print.assert_any_call("Requests Loaded : 4")
        mock_print.assert_any_call("Requests Executed : 1")
        mock_print.assert_any_call("Requests Skipped : 3")
        mock_print.assert_any_call("Skipped Non-Executable : 1")
        mock_print.assert_any_call("Skipped Obsolete : 1")
        mock_print.assert_any_call("Skipped Symbol Mismatch : 1")
        mock_print.assert_any_call("Results Saved : 1")
        mock_print.assert_any_call("Not Implemented : 1")
        mock_print.assert_any_call(
            "- initial_backtest [not_implemented] request_id=expreq-001 result_id=expr-001"
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
        mock_print.assert_any_call("Skipped Non-Executable : 0")
        mock_print.assert_any_call("Skipped Obsolete : 0")
        mock_print.assert_any_call("Skipped Symbol Mismatch : 0")
        mock_print.assert_any_call("Results Saved : 0")
        mock_print.assert_any_call("Not Implemented : 0")
        mock_print.assert_any_call("No experiment requests to execute.")

    def test_runner_skips_legacy_stored_requests_without_crashing(self):
        storage = Storage()
        executor = Mock()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            requests_dir = Path(tmp_dir) / "experiments" / "requests"
            requests_dir.mkdir(parents=True, exist_ok=True)
            requests_path = requests_dir / "NVDA.json"
            requests_path.write_text(
                """[
    {
        "experiment_request_id": "expreq-legacy-file-001",
        "hypothesis_id": "hyp-legacy-file-001",
        "hypothesis_version": "v1",
        "symbol": "NVDA",
        "title": "Legacy request from old schema",
        "objective": "Legacy objective",
        "test_type": "initial_backtest",
        "entry_conditions": "Legacy natural language only",
        "exit_conditions": "Legacy exit",
        "time_horizon": "5D"
    }
]""",
                encoding="utf-8",
            )

            with patch("builtins.print") as mock_print:
                results = run_manual_experiment_execution(
                    symbol="NVDA",
                    storage=storage,
                    executor=executor,
                )

            self.assertEqual([], results)
            executor.execute.assert_not_called()
            mock_print.assert_any_call("Requests Loaded : 1")
            mock_print.assert_any_call("Requests Executed : 0")
            mock_print.assert_any_call("Requests Skipped : 1")
            mock_print.assert_any_call("Skipped Non-Executable : 1")
            mock_print.assert_any_call("Skipped Obsolete : 0")
            mock_print.assert_any_call("Skipped Symbol Mismatch : 0")
            storage_path = Path(tmp_dir) / "experiments" / "results" / "NVDA.json"
            self.assertFalse(storage_path.exists())

    def test_runner_prints_completed_result_summary_and_key_metrics(self):
        storage = Mock()
        executor = Mock()

        executable_request = ExperimentRequest(
            experiment_request_id="expreq-200",
            hypothesis_id="hyp-200",
            hypothesis_version_id="hyp-200:v1",
            symbol="NVDA",
            title="Completed result display request",
            objective="Validate runner output formatting for completed result metrics.",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Entry",
            machine_readable_entry_conditions=(
                {"field": "Close", "operator": ">", "value": 100.0},
            ),
            exit_conditions="Exit",
            time_horizon="5D",
            forward_horizon=5,
        )

        storage.load_experiment_requests.return_value = [executable_request]

        now = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)
        completed_result = ExperimentResult(
            experiment_result_id="expr-200",
            experiment_request_id="expreq-200",
            hypothesis_id="hyp-200",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(
                trade_count=7,
                average_return=0.0125,
                win_rate=0.57,
                total_return=0.0875,
                extra_metrics={
                    "best_return": 0.08,
                    "worst_return": -0.03,
                },
            ),
            summary="Basic backtest completed with deterministic metrics.",
            created_at=now,
            updated_at=now,
        )
        executor.execute.return_value = completed_result

        with patch("builtins.print") as mock_print:
            results = run_manual_experiment_execution(
                symbol="NVDA",
                storage=storage,
                executor=executor,
            )

        self.assertEqual([completed_result], results)
        mock_print.assert_any_call(
            "  summary: Basic backtest completed with deterministic metrics."
        )
        mock_print.assert_any_call(
            "  metrics: trade_count=7, average_return=1.25%, win_rate=57.00%, best_return=8.00%, worst_return=-3.00%, total_return=8.75%"
        )


if __name__ == "__main__":
    unittest.main()