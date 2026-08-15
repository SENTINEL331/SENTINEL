import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from research.runner import _build_arg_parser, run_manual_demo_daily_operator


def _dashboard_result():
    return SimpleNamespace(
        open_demo_trades=2,
        rating_counts={"current_no_new_entry": 2},
    )


class DemoDailyOperatorTests(unittest.TestCase):
    def test_cli_help_includes_daily_operator(self):
        self.assertIn("demo-daily-operator", _build_arg_parser().format_help())

    def test_runs_monitoring_cycle_before_status_dashboard(self):
        calls = []
        storage = object()

        def monitoring_cycle(**kwargs):
            calls.append(("cycle", kwargs["symbol"], kwargs["storage"]))
            return {
                "cycle_status": "completed",
                "records_modified": True,
            }

        def status_dashboard(**kwargs):
            calls.append(("dashboard", kwargs["symbol"], kwargs["storage"]))
            print("Manual Demo Status Dashboard: NVDA")
            return _dashboard_result()

        with patch("builtins.print") as mock_print:
            result = run_manual_demo_daily_operator(
                symbol="NVDA",
                storage=storage,
                monitoring_cycle_fn=monitoring_cycle,
                status_dashboard_fn=status_dashboard,
            )

        self.assertEqual(["cycle", "dashboard"], [name for name, _, _ in calls])
        self.assertTrue(all(call_storage is storage for _, _, call_storage in calls))
        self.assertEqual("completed", result["operator_status"])
        self.assertTrue(result["dashboard_displayed"])
        mock_print.assert_any_call("Broker Calls Allowed : yes")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Order Cancellation Allowed : no")
        mock_print.assert_any_call("Position Close Allowed : no")
        mock_print.assert_any_call("Promotion Actions Taken : 0")
        mock_print.assert_any_call("  current_no_new_entry=2")
        mock_print.assert_any_call("orders_submitted=0")
        mock_print.assert_any_call("orders_cancelled=0")
        mock_print.assert_any_call("positions_closed=0")
        mock_print.assert_any_call("promotions_performed=0")

    def test_monitoring_failure_still_runs_dashboard_with_warning(self):
        calls = []

        def monitoring_cycle(**kwargs):
            calls.append("cycle")
            raise RuntimeError("cycle unavailable")

        def status_dashboard(**kwargs):
            calls.append("dashboard")
            return _dashboard_result()

        with patch("builtins.print") as mock_print:
            result = run_manual_demo_daily_operator(
                symbol="NVDA",
                storage=object(),
                monitoring_cycle_fn=monitoring_cycle,
                status_dashboard_fn=status_dashboard,
            )

        self.assertEqual(["cycle", "dashboard"], calls)
        self.assertEqual("completed_with_warnings", result["operator_status"])
        mock_print.assert_any_call("- demo_monitoring_cycle: failed")
        mock_print.assert_any_call("  error=cycle unavailable")

    def test_dashboard_failure_reports_warning(self):
        def monitoring_cycle(**kwargs):
            return {"cycle_status": "completed", "records_modified": False}

        def status_dashboard(**kwargs):
            raise RuntimeError("dashboard unavailable")

        with patch("builtins.print") as mock_print:
            result = run_manual_demo_daily_operator(
                symbol="NVDA",
                storage=object(),
                monitoring_cycle_fn=monitoring_cycle,
                status_dashboard_fn=status_dashboard,
            )

        self.assertEqual("completed_with_warnings", result["operator_status"])
        self.assertFalse(result["dashboard_displayed"])
        mock_print.assert_any_call("- demo_status_dashboard: failed")
        mock_print.assert_any_call("  error=dashboard unavailable")


if __name__ == "__main__":
    unittest.main()