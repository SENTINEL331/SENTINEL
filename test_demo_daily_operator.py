import unittest
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

from research.runner import _build_arg_parser, run_manual_demo_daily_operator


def _dashboard_result():
    return SimpleNamespace(
        open_demo_trades=4,
        total_unrealized_plpc=0.0125,
        trades=(
            SimpleNamespace(
                trading_days_elapsed=1,
                evaluation_window_trading_days=5,
            ),
        ),
        rating_counts={
            "current_no_new_entry": 4,
            "attractive_now": 0,
            "exit_needs_more_time": 4,
            "exit_candidate": 0,
            "risk_exit_candidate": 0,
            "max_evaluation_days_remaining": 4,
        },
    )


def _healthy_system_health():
    return SimpleNamespace(
        overall_health="healthy",
        required_checks_passed=True,
        warnings=(),
        blocked_checks=(),
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
            print("  evaluation_window_trading_days=5")
            print("  evaluation_days_remaining=3")
            print("  evaluation_window_complete=False")
            print("Latest Daily AI Review")
            print("latest_ai_review_available=yes")
            return _dashboard_result()

        with patch("builtins.print") as mock_print:
            result = run_manual_demo_daily_operator(
                symbol="NVDA",
                storage=storage,
                monitoring_cycle_fn=monitoring_cycle,
                status_dashboard_fn=status_dashboard,
                health_fn=Mock(return_value=_healthy_system_health()),
            )

        self.assertEqual(["cycle", "dashboard"], [name for name, _, _ in calls])
        self.assertTrue(all(call_storage is storage for _, _, call_storage in calls))
        self.assertEqual("completed", result["operator_status"])
        self.assertEqual("healthy", result["system_health"])
        self.assertFalse(result["system_blocked"])
        self.assertTrue(result["dashboard_displayed"])
        mock_print.assert_any_call("System Health")
        mock_print.assert_any_call("overall_health=healthy")
        mock_print.assert_any_call("system_blocked=no")
        mock_print.assert_any_call("Daily Decision Summary")
        mock_print.assert_any_call("system_health=healthy")
        mock_print.assert_any_call("open_demo_trades=4")
        mock_print.assert_any_call("evaluation_progress=1/5 trading_days")
        mock_print.assert_any_call("evaluation_days_remaining=4")
        mock_print.assert_any_call("exit_action=continue_monitoring")
        mock_print.assert_any_call("new_entry_action=no_new_entry")
        mock_print.assert_any_call("promotion_action=no_promotion")
        mock_print.assert_any_call("ai_review_action=not_requested")
        mock_print.assert_any_call("operator_decision=continue_monitoring")
        mock_print.assert_any_call("Broker Calls Allowed : yes")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Order Cancellation Allowed : no")
        mock_print.assert_any_call("Position Close Allowed : no")
        mock_print.assert_any_call("Promotion Actions Taken : 0")
        mock_print.assert_any_call("  current_no_new_entry=4")
        mock_print.assert_any_call("  exit_readiness=needs_more_time")
        mock_print.assert_any_call("  evaluation_window_trading_days=5")
        mock_print.assert_any_call("  evaluation_days_remaining=3")
        mock_print.assert_any_call("  evaluation_window_complete=False")
        mock_print.assert_any_call("Latest Daily AI Review")
        mock_print.assert_any_call("latest_ai_review_available=yes")
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
                health_fn=Mock(return_value=_healthy_system_health()),
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
                health_fn=Mock(return_value=_healthy_system_health()),
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
                health_fn=Mock(return_value=_healthy_system_health()),
            )

        ai_review.assert_not_called()
        self.assertFalse(result["ai_review_requested"])
        self.assertEqual(0, result["ai_calls_made"])
        mock_print.assert_any_call("ai_review_requested=no")
        mock_print.assert_any_call("ai_calls_made=0")
        printed_messages = [call.args[0] for call in mock_print.call_args_list if call.args]
        self.assertNotIn("Latest AI Review After Operator", printed_messages)

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
                health_fn=Mock(return_value=_healthy_system_health()),
            )

        ai_review.assert_called_once_with(
            symbol="NVDA", storage=ANY, confirm_ai_call=False
        )
        self.assertEqual("completed_with_warnings", result["operator_status"])
        self.assertEqual(0, result["ai_calls_made"])
        mock_print.assert_any_call("ai_review_requested=yes")
        mock_print.assert_any_call("ai_review_confirmed=no")
        mock_print.assert_any_call("ai_calls_made=0")
        mock_print.assert_any_call("ai_review_action=confirmation_required")
        mock_print.assert_any_call("Latest AI Review After Operator")
        mock_print.assert_any_call("ai_review_source=confirmation_required")

    def test_confirmed_ai_review_delegates_and_reports_duplicate(self):
        existing_review = SimpleNamespace(
            demo_daily_ai_review_id="ddair-existing",
            reviewed_at="2026-08-16 12:00:00+00:00",
            deeper_ai_review_needed=False,
            reason="evaluation_window_incomplete",
        )
        ai_review = Mock(
            return_value={
                "records_modified": False,
                "ai_calls_made": 0,
                "daily_reviews_created": 0,
                "skipped_existing": 1,
                "review": None,
                "existing_latest_review": existing_review,
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
                health_fn=Mock(return_value=_healthy_system_health()),
            )

        ai_review.assert_called_once_with(
            symbol="NVDA", storage=ANY, confirm_ai_call=True
        )
        self.assertEqual("completed", result["operator_status"])
        self.assertEqual(0, result["ai_calls_made"])
        self.assertEqual(1, result["skipped_existing"])
        mock_print.assert_any_call("ai_review_confirmed=yes")
        mock_print.assert_any_call("skipped_existing=1")
        mock_print.assert_any_call("ai_review_action=duplicate_latest_state")
        mock_print.assert_any_call("Latest AI Review After Operator")
        mock_print.assert_any_call("latest_ai_review_id=ddair-existing")
        mock_print.assert_any_call("latest_ai_review_at=2026-08-16T12:00:00+00:00")
        mock_print.assert_any_call("ai_review_source=existing_latest_state")

    def test_confirmed_ai_review_summary_reports_reviewed_when_created(self):
        ai_review = Mock(
            return_value={
                "records_modified": True,
                "ai_calls_made": 1,
                "daily_reviews_created": 1,
                "skipped_existing": 0,
                "review": SimpleNamespace(
                    deeper_ai_review_needed=False,
                    reason="evaluation_window_incomplete",
                ),
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
                health_fn=Mock(return_value=_healthy_system_health()),
            )

        self.assertEqual(1, result["daily_reviews_created"])
        mock_print.assert_any_call("ai_review_action=reviewed")
        mock_print.assert_any_call("Latest AI Review After Operator")
        mock_print.assert_any_call("ai_review_source=created_this_run")

    def test_confirmed_ai_review_without_result_reports_no_ai_call_made(self):
        ai_review = Mock(
            return_value={
                "records_modified": False,
                "ai_calls_made": 0,
                "daily_reviews_created": 0,
                "skipped_existing": 0,
                "review": None,
                "error": None,
            }
        )
        with patch("builtins.print") as mock_print:
            run_manual_demo_daily_operator(
                symbol="NVDA",
                storage=object(),
                monitoring_cycle_fn=Mock(return_value=self._successful_cycle()),
                status_dashboard_fn=Mock(return_value=self._successful_dashboard()),
                ai_review_requested=True,
                confirm_ai_call=True,
                daily_ai_review_fn=ai_review,
                health_fn=Mock(return_value=_healthy_system_health()),
            )

        mock_print.assert_any_call("ai_review_action=no_ai_call_made")

    def test_blocked_health_prevents_monitoring_and_dashboard(self):
        health = SimpleNamespace(
            overall_health="blocked",
            required_checks_passed=False,
            warnings=(),
            blocked_checks=("demo_broker_mode_paper",),
        )
        monitoring_cycle = Mock()
        status_dashboard = Mock()
        ai_review = Mock()

        with patch("builtins.print") as mock_print:
            result = run_manual_demo_daily_operator(
                symbol="NVDA",
                storage=object(),
                monitoring_cycle_fn=monitoring_cycle,
                status_dashboard_fn=status_dashboard,
                ai_review_requested=True,
                confirm_ai_call=True,
                daily_ai_review_fn=ai_review,
                health_fn=Mock(return_value=health),
            )

        monitoring_cycle.assert_not_called()
        status_dashboard.assert_not_called()
        ai_review.assert_not_called()
        self.assertEqual("blocked", result["operator_status"])
        self.assertTrue(result["system_blocked"])
        self.assertEqual(0, result["ai_calls_made"])
        mock_print.assert_any_call("blocked_checks=demo_broker_mode_paper")
        mock_print.assert_any_call("Daily Decision Summary")
        mock_print.assert_any_call("operator_decision=blocked")
        mock_print.assert_any_call("Blocked Reason : demo_broker_mode_paper")
        mock_print.assert_any_call("system_blocked=yes")


if __name__ == "__main__":
    unittest.main()