import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from research.runner import _build_arg_parser, run_manual_demo_monitoring_cycle


def _result(**values):
    defaults = {
        "records_modified": False,
        "status_synced": 0,
        "failed_sync": 0,
        "position_found": False,
        "snapshots_created": 0,
        "performance_snapshots_created": 0,
        "latest_trades_displayed": 0,
        "evaluations_created": 0,
        "summaries_created": 0,
        "skipped_existing": 0,
        "board_items_displayed": 0,
        "refused_reason": None,
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


class DemoMonitoringCycleTests(unittest.TestCase):
    def test_cli_help_includes_monitoring_cycle(self):
        self.assertIn("demo-monitoring-cycle", _build_arg_parser().format_help())

    def test_runs_existing_steps_in_order_with_shared_storage(self):
        storage = object()
        calls = []

        def step(name, result):
            def run(**kwargs):
                calls.append((name, kwargs["symbol"], kwargs["storage"]))
                return result

            return run

        result = run_manual_demo_monitoring_cycle(
            symbol="NVDA",
            storage=storage,
            status_sync_fn=step("status", _result(status_synced=1, records_modified=True)),
            snapshot_sync_fn=step("position", _result(position_found=True, snapshots_created=1, records_modified=True)),
            performance_snapshot_fn=step("performance", _result(performance_snapshots_created=2, records_modified=True)),
            dashboard_fn=step("dashboard", _result(latest_trades_displayed=2)),
            evaluation_fn=step("evaluation", _result(evaluations_created=1, skipped_existing=2, records_modified=True)),
            summary_fn=step("summary", _result(summaries_created=1, skipped_existing=1, records_modified=True)),
            board_fn=step("board", _result(board_items_displayed=3)),
        )

        self.assertEqual(
            ["status", "position", "performance", "dashboard", "evaluation", "summary", "board"],
            [name for name, _, _ in calls],
        )
        self.assertTrue(all(call_storage is storage for _, _, call_storage in calls))
        self.assertEqual("completed", result["cycle_status"])
        self.assertTrue(result["records_modified"])

    def test_reports_required_safety_contract_and_totals(self):
        with patch("builtins.print") as mock_print:
            run_manual_demo_monitoring_cycle(
                storage=Mock(),
                status_sync_fn=Mock(return_value=_result(status_synced=2)),
                snapshot_sync_fn=Mock(return_value=_result(snapshots_created=1, position_found=False)),
                performance_snapshot_fn=Mock(return_value=_result(performance_snapshots_created=3)),
                dashboard_fn=Mock(return_value=_result(latest_trades_displayed=4)),
                evaluation_fn=Mock(return_value=_result(evaluations_created=2, skipped_existing=1)),
                summary_fn=Mock(return_value=_result(summaries_created=1, skipped_existing=2)),
                board_fn=Mock(return_value=_result(board_items_displayed=4)),
            )

        mock_print.assert_any_call("Broker Calls Allowed : yes")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Order Cancellation Allowed : no")
        mock_print.assert_any_call("Position Close Allowed : no")
        mock_print.assert_any_call("  promotion_actions_taken=0")
        mock_print.assert_any_call("broker_status_synced=2")
        mock_print.assert_any_call("position_snapshots_created=1")
        mock_print.assert_any_call("performance_snapshots_created=3")
        mock_print.assert_any_call("evaluations_created=2")
        mock_print.assert_any_call("hypothesis_summaries_created=1")
        mock_print.assert_any_call("board_items_displayed=4")

    def test_continues_after_safe_step_failure_and_reports_warning(self):
        calls = []

        def failing_status(**kwargs):
            calls.append("status")
            raise RuntimeError("status unavailable")

        def later_step(name, result):
            def run(**kwargs):
                calls.append(name)
                return result

            return run

        with patch("builtins.print") as mock_print:
            result = run_manual_demo_monitoring_cycle(
                storage=Mock(),
                status_sync_fn=failing_status,
                snapshot_sync_fn=later_step("position", _result()),
                performance_snapshot_fn=later_step("performance", _result()),
                dashboard_fn=later_step("dashboard", _result()),
                evaluation_fn=later_step("evaluation", _result()),
                summary_fn=later_step("summary", _result()),
                board_fn=later_step("board", _result()),
            )

        self.assertEqual(["status", "position", "performance", "dashboard", "evaluation", "summary", "board"], calls)
        self.assertEqual("completed_with_warnings", result["cycle_status"])
        mock_print.assert_any_call("- broker_order_status_sync: failed")
        mock_print.assert_any_call("  error=status unavailable")


if __name__ == "__main__":
    unittest.main()