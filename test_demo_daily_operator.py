import unittest
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

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
            print("  exit_readiness=needs_more_time")
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
        mock_print.assert_any_call("  exit_readiness=needs_more_time")
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

    def _successful_cycle(self):
        return {"cycle_status": "completed", "records_modified": False}

    def _successful_dashboard(self):
        return _dashboard_result()

    def test_default_daily_operator_does_not_call_ai_review(self):
        ai_review = Mock()
        with patch("builtins.print") as mock_print:
            result = run_manual_demo_daily_operator(
                symbol="NVDA",
                storage=object(),
                monitoring_cycle_fn=Mock(return_value=self._successful_cycle()),
                status_dashboard_fn=Mock(return_value=self._successful_dashboard()),
                daily_ai_review_fn=ai_review,
            )

        ai_review.assert_not_called()
        self.assertFalse(result["ai_review_requested"])
        self.assertEqual(0, result["ai_calls_made"])
        mock_print.assert_any_call("ai_review_requested=no")
        mock_print.assert_any_call("ai_calls_made=0")

    def test_ai_review_without_confirmation_delegates_without_ai_call(self):
        ai_review = Mock(
            return_value={
                "records_modified": False,
                "ai_calls_made": 0,
                "daily_reviews_created": 0,
                "skipped_existing": 0,
                "review": None,
                "error": "confirmation is required",
            }
        )
        with patch("builtins.print") as mock_print:
            result = run_manual_demo_daily_operator(
                symbol="NVDA",
                storage=object(),
                monitoring_cycle_fn=Mock(return_value=self._successful_cycle()),
                status_dashboard_fn=Mock(return_value=self._successful_dashboard()),
                ai_review_requested=True,
                confirm_ai_call=False,
                daily_ai_review_fn=ai_review,
            )

        ai_review.assert_called_once_with(
            symbol="NVDA", storage=ANY, confirm_ai_call=False
        )
        self.assertEqual("completed_with_warnings", result["operator_status"])
        self.assertEqual(0, result["ai_calls_made"])
        mock_print.assert_any_call("ai_review_requested=yes")
        mock_print.assert_any_call("ai_review_confirmed=no")
        mock_print.assert_any_call("ai_calls_made=0")

    def test_confirmed_ai_review_delegates_and_reports_duplicate(self):
        ai_review = Mock(
            return_value={
                "records_modified": False,
                "ai_calls_made": 0,
                "daily_reviews_created": 0,
                "skipped_existing": 1,
                "review": None,
                "error": None,
            }
        )
        with patch("builtins.print") as mock_print:
            result = run_manual_demo_daily_operator(
                symbol="NVDA",
                storage=object(),
                monitoring_cycle_fn=Mock(return_value=self._successful_cycle()),
                status_dashboard_fn=Mock(return_value=self._successful_dashboard()),
                ai_review_requested=True,
                confirm_ai_call=True,
                daily_ai_review_fn=ai_review,
            )

        ai_review.assert_called_once_with(
            symbol="NVDA", storage=ANY, confirm_ai_call=True
        )
        self.assertEqual("completed", result["operator_status"])
        self.assertEqual(0, result["ai_calls_made"])
        self.assertEqual(1, result["skipped_existing"])
        mock_print.assert_any_call("ai_review_confirmed=yes")
        mock_print.assert_any_call("skipped_existing=1")


if __name__ == "__main__":
    unittest.main()