import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

from research.runner import (
    _build_arg_parser,
    _operator_action_ledger,
    _operator_decision_packet,
    run_manual_demo_daily_operator,
    run_manual_demo_operator_runs,
)


def _dashboard_result():
    return SimpleNamespace(
        open_demo_trades=4,
        total_unrealized_plpc=0.0125,
        trades=(
            SimpleNamespace(
                trading_days_elapsed=1,
                evaluation_window_trading_days=5,
				evaluation_window_complete=False,
				entry_performance_rating="positive_open",
            ),
        ),
		position_snapshot=SimpleNamespace(status="open"),
		hypotheses=(),
        rating_counts={
            "current_no_new_entry": 4,
            "attractive_now": 0,
            "exit_needs_more_time": 4,
            "exit_candidate": 0,
            "risk_exit_candidate": 0,
            "max_evaluation_days_remaining": 4,
        },
        staleness_status="fresh",
        freshness_reason="latest_required_snapshots_fresh",
        ai_review_freshness="behind_latest_snapshot",
        ai_review_freshness_reason="ai_review_older_than_latest_required_snapshot",
        ai_review_suggested_action="request_fresh_ai_review",
        ai_review_action_reason="latest_monitoring_snapshot_newer_than_ai_review",
        latest_required_snapshot_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        latest_daily_ai_review=SimpleNamespace(
            reviewed_at=datetime.now(timezone.utc) - timedelta(hours=2)
        ),
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
        mock_print.assert_any_call("staleness_status=fresh")
        mock_print.assert_any_call("freshness_reason=latest_required_snapshots_fresh")
        mock_print.assert_any_call("ai_review_freshness=behind_latest_snapshot")
        mock_print.assert_any_call(
            "ai_review_freshness_reason=ai_review_older_than_latest_required_snapshot"
        )
        mock_print.assert_any_call("ai_review_suggested_action=request_fresh_ai_review")
        mock_print.assert_any_call(
            "ai_review_action_reason=latest_monitoring_snapshot_newer_than_ai_review"
        )
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
        mock_print.assert_any_call("Operator Decision Packet")
        mock_print.assert_any_call("decision=request_fresh_ai_review")
        mock_print.assert_any_call("demo_trade_state=positive_open")
        mock_print.assert_any_call("evaluation_state=incomplete")
        mock_print.assert_any_call("blocked_actions=orders,cancellations,position_closes,promotions,live_trading")
        mock_print.assert_any_call("Action Ledger")
        mock_print.assert_any_call("monitoring=performed")
        mock_print.assert_any_call("monitoring_reason=safe_read_snapshot_evaluation_cycle_completed")
        mock_print.assert_any_call("ai_review=not_requested")
        mock_print.assert_any_call("exit=blocked_by_incomplete_evaluation_window")
        mock_print.assert_any_call("new_entry=blocked_by_current_opportunity_not_ready")
        mock_print.assert_any_call("promotion=blocked_by_no_completed_evaluation_window")
        mock_print.assert_any_call("orders=blocked_by_demo_operator_policy")
        mock_print.assert_any_call("cancellations=blocked_by_demo_operator_policy")
        mock_print.assert_any_call("position_closes=blocked_by_demo_operator_policy")
        mock_print.assert_any_call("live_trading=blocked_by_policy")
        mock_print.assert_any_call("ledger_status=complete")

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
        mock_print.assert_any_call("ai_review_suggested_action=request_fresh_ai_review")
        printed_messages = [call.args[0] for call in mock_print.call_args_list if call.args]
        self.assertNotIn("Latest AI Review After Operator", printed_messages)

    def test_daily_operator_appends_finalized_demo_only_run_record(self):
        storage = Mock()
        storage.save_demo_operator_run_record.return_value = True
        with patch("builtins.print") as mock_print:
            result = run_manual_demo_daily_operator(
                symbol="NVDA",
                storage=storage,
                monitoring_cycle_fn=Mock(return_value=self._successful_cycle()),
                status_dashboard_fn=Mock(return_value=self._successful_dashboard()),
                health_fn=Mock(return_value=_healthy_system_health()),
            )

        storage.save_demo_operator_run_record.assert_called_once()
        record = storage.save_demo_operator_run_record.call_args.args[0]
        self.assertTrue(record.demo_only)
        self.assertEqual("not_requested", record.ai_review_action)
        self.assertEqual("request_fresh_ai_review", record.decision)
        self.assertEqual("positive_open", record.demo_trade_state)
        self.assertEqual("complete", record.action_ledger["ledger_status"])
        self.assertEqual("blocked_by_demo_operator_policy", record.action_ledger["orders"])
        self.assertTrue(result["operator_run_recorded"])
        mock_print.assert_any_call("Operator Run Record")
        mock_print.assert_any_call("operator_run_recorded=yes")
        mock_print.assert_any_call("record_storage=local_append_only")
        mock_print.assert_any_call("demo_only=True")

    def test_operator_runs_is_read_only_and_prints_recent_records(self):
        record = SimpleNamespace(
            run_id="dor-NVDA-001",
            created_at=datetime(2026, 8, 17, tzinfo=timezone.utc),
            decision="continue_monitoring",
            decision_reason="monitoring_state_requires_no_action",
            operator_status="completed",
            ai_review_action="not_requested",
            ai_calls_made=0,
            orders_submitted=0,
            orders_cancelled=0,
            positions_closed=0,
            promotions_performed=0,
            human_next_step="run_again_next_trading_day",
        )
        storage = Mock()
        storage.load_demo_operator_run_records.return_value = [record]
        with patch("builtins.print") as mock_print, patch("urllib.request.urlopen") as mock_urlopen:
            result = run_manual_demo_operator_runs(symbol="NVDA", storage=storage)

        self.assertEqual([record], result)
        storage.load_demo_operator_run_records.assert_called_once_with(symbol="NVDA")
        mock_urlopen.assert_not_called()
        self.assertTrue(all(call[0].startswith("load_") for call in storage.method_calls))
        mock_print.assert_any_call("Manual Demo Operator Runs: NVDA")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Broker Calls Allowed : no")
        mock_print.assert_any_call("Market Data Calls Allowed : no")
        mock_print.assert_any_call("Filters")
        mock_print.assert_any_call("limit=none")
        mock_print.assert_any_call("decision=none")
        mock_print.assert_any_call("ai_review_action=none")
        mock_print.assert_any_call("status=none")
        mock_print.assert_any_call("records_after_filters=1")
        mock_print.assert_any_call("- operator_run_id=dor-NVDA-001")
        mock_print.assert_any_call("runs_loaded=1")
        mock_print.assert_any_call("latest_decision=continue_monitoring")
        mock_print.assert_any_call("reviewed_runs=0")
        mock_print.assert_any_call("confirmation_required_runs=0")
        mock_print.assert_any_call("not_requested_runs=1")
        mock_print.assert_any_call("continue_monitoring_runs=1")
        mock_print.assert_any_call("orders_submitted_total=0")
        mock_print.assert_any_call("orders_cancelled_total=0")
        mock_print.assert_any_call("positions_closed_total=0")
        mock_print.assert_any_call("promotions_performed_total=0")
        mock_print.assert_any_call("latest_run_demo_only=unknown")
        mock_print.assert_any_call("history_health=warning")
        mock_print.assert_any_call("history_health_reason=demo_only_missing_or_unknown")
        mock_print.assert_any_call("History Health Details")
        mock_print.assert_any_call("records_checked=1")
        mock_print.assert_any_call("demo_only_records=0")
        mock_print.assert_any_call("missing_demo_only_records=1")
        mock_print.assert_any_call("non_demo_only_records=0")
        mock_print.assert_any_call("records_with_order_actions=0")
        mock_print.assert_any_call("latest_run_id=dor-NVDA-001")
        mock_print.assert_any_call("latest_run_created_at=2026-08-17T00:00:00+00:00")
        mock_print.assert_any_call("latest_run_demo_only=unknown")
        mock_print.assert_any_call("latest_run_decision=continue_monitoring")
        mock_print.assert_any_call("latest_run_human_next_step=run_again_next_trading_day")
        mock_print.assert_any_call("safety_verdict=operator_safety_warning")

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
        self.assertEqual(
            "confirmation_required", result["operator_run_record"].ai_review_action
        )
        self.assertEqual(0, result["operator_run_record"].ai_calls_made)
        mock_print.assert_any_call("ai_review_requested=yes")
        mock_print.assert_any_call("ai_review_confirmed=no")
        mock_print.assert_any_call("ai_calls_made=0")
        mock_print.assert_any_call("ai_review_action=confirmation_required")
        mock_print.assert_any_call("ai_review=confirmation_required")
        mock_print.assert_any_call("Latest AI Review After Operator")
        mock_print.assert_any_call("ai_review_source=confirmation_required")
        mock_print.assert_any_call("AI Review Freshness After Operator")
        mock_print.assert_any_call(
            "ai_review_suggested_action_after_operator=request_fresh_ai_review"
        )
        mock_print.assert_any_call("ai_review_suggested_action=request_fresh_ai_review")

    def test_confirmed_ai_review_delegates_and_reports_duplicate(self):
        existing_review = SimpleNamespace(
            demo_daily_ai_review_id="ddair-existing",
            reviewed_at=datetime.now(timezone.utc),
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
        self.assertEqual(
            "duplicate_latest_state", result["operator_run_record"].ai_review_action
        )
        mock_print.assert_any_call("ai_review_confirmed=yes")
        mock_print.assert_any_call("skipped_existing=1")
        mock_print.assert_any_call("ai_review_action=duplicate_latest_state")
        mock_print.assert_any_call("ai_review=duplicate_latest_state")
        mock_print.assert_any_call("Latest AI Review After Operator")
        mock_print.assert_any_call("latest_ai_review_id=ddair-existing")
        mock_print.assert_any_call("ai_review_source=existing_latest_state")
        mock_print.assert_any_call("ai_review_freshness_after_operator=current")
        mock_print.assert_any_call("ai_review_suggested_action_after_operator=none")
        mock_print.assert_any_call("ai_review_suggested_action=none")

    def test_confirmed_ai_review_summary_reports_reviewed_when_created(self):
        ai_review = Mock(
            return_value={
                "records_modified": True,
                "ai_calls_made": 1,
                "daily_reviews_created": 1,
                "skipped_existing": 0,
                "review": SimpleNamespace(
					reviewed_at=datetime.now(timezone.utc),
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
        self.assertEqual("reviewed", result["operator_run_record"].ai_review_action)
        self.assertEqual(1, result["operator_run_record"].ai_calls_made)
        mock_print.assert_any_call("ai_review_action=reviewed")
        mock_print.assert_any_call("ai_review=reviewed")
        mock_print.assert_any_call("Latest AI Review After Operator")
        mock_print.assert_any_call("ai_review_source=created_this_run")
        mock_print.assert_any_call("AI Review Freshness After Operator")
        mock_print.assert_any_call("ai_review_freshness_after_operator=current")
        mock_print.assert_any_call("ai_review_suggested_action_after_operator=none")
        mock_print.assert_any_call("decision=continue_monitoring")
        mock_print.assert_any_call("ai_review_suggested_action=none")
        mock_print.assert_any_call("human_next_step=run_again_next_trading_day")

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

    def test_operator_decision_packet_prioritizes_exit_then_promotion_then_ai(self):
        health = _healthy_system_health()
        summary = {
            "staleness_status": "fresh",
            "evaluation_progress": "2/5 trading_days",
            "evaluation_days_remaining": 3,
            "exit_action": "exit_candidate",
            "new_entry_action": "no_new_entry",
            "ai_review_action": "not_requested",
            "ai_review_freshness": "behind_latest_snapshot",
            "ai_review_suggested_action": "request_fresh_ai_review",
        }
        dashboard = _dashboard_result()
        dashboard.hypotheses = (
            SimpleNamespace(board_recommendation="review_later", promotion_readiness="not_ready"),
        )
        exit_packet = _operator_decision_packet(
            health_result=health, dashboard_result=dashboard, decision_summary=summary
        )
        self.assertEqual("review_exit_candidate", exit_packet["decision"])

        summary["exit_action"] = "continue_monitoring"
        promotion_packet = _operator_decision_packet(
            health_result=health, dashboard_result=dashboard, decision_summary=summary
        )
        self.assertEqual("review_promotion_candidate", promotion_packet["decision"])

        dashboard.hypotheses = ()
        ai_packet = _operator_decision_packet(
            health_result=health, dashboard_result=dashboard, decision_summary=summary
        )
        self.assertEqual("request_fresh_ai_review", ai_packet["decision"])

        summary["ai_review_freshness"] = "current"
        summary["ai_review_suggested_action"] = "none"
        continue_packet = _operator_decision_packet(
            health_result=health, dashboard_result=dashboard, decision_summary=summary
        )
        self.assertEqual("continue_monitoring", continue_packet["decision"])
        self.assertEqual("run_again_next_trading_day", continue_packet["human_next_step"])

    def test_operator_decision_packet_blocks_unhealthy_or_stale_state(self):
        summary = {
            "staleness_status": "stale",
            "evaluation_progress": "unknown",
            "evaluation_days_remaining": "unknown",
            "exit_action": "continue_monitoring",
            "new_entry_action": "no_new_entry",
            "ai_review_action": "not_requested",
            "ai_review_freshness": "current",
            "ai_review_suggested_action": "none",
        }
        packet = _operator_decision_packet(
            health_result=_healthy_system_health(),
            dashboard_result=_dashboard_result(),
            decision_summary=summary,
        )
        self.assertEqual("blocked", packet["decision"])

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