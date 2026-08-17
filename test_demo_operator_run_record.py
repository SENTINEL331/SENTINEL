import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai.storage import Storage
from research.demo_operator_run_record import new_demo_operator_run_record
from research.runner import (
    _filter_demo_operator_run_records,
		_operator_run_decision_trend,
    _operator_run_history_metrics,
		_print_demo_operator_run_detail,
        _print_demo_operator_latest_brief,
        run_manual_demo_operator_latest,
		run_manual_demo_operator_runs,
)


def _packet():
    return {
        "decision": "continue_monitoring",
        "decision_reason": "monitoring_state_requires_no_action",
        "position_state": "open_demo_position",
        "demo_trade_state": "positive_open",
        "evaluation_state": "incomplete",
        "evaluation_progress": "2/5 trading_days",
        "evaluation_days_remaining": 3,
        "exit_action": "continue_monitoring",
        "new_entry_action": "no_new_entry",
        "promotion_action": "no_promotion",
        "ai_review_action": "not_requested",
        "ai_review_suggested_action": "none",
        "freshness_state": "fresh",
        "human_next_step": "run_again_next_trading_day",
        "blocked_actions": "orders,cancellations,position_closes,promotions,live_trading",
    }


class DemoOperatorRunRecordStorageTests(unittest.TestCase):
    def test_appends_and_loads_final_packet_and_ledger(self):
        record = new_demo_operator_run_record(
            symbol="NVDA",
            operator_status="completed",
            system_health="healthy",
            system_blocked=False,
            monitoring_cycle_status="completed",
            dashboard_displayed=True,
            ai_review_requested=False,
            ai_review_confirmed=False,
            ai_calls_made=0,
            daily_ai_reviews_created=0,
            decision_packet=_packet(),
            action_ledger={
                "monitoring": "performed",
                "orders": "blocked_by_demo_operator_policy",
                "ledger_status": "complete",
            },
        )
        storage = Storage()
        with tempfile.TemporaryDirectory() as temp_dir:
            storage.base = Path(temp_dir)
            self.assertTrue(storage.save_demo_operator_run_record(record))
            self.assertTrue(storage.save_demo_operator_run_record(record))
            records = storage.load_demo_operator_run_records(symbol="NVDA")

        self.assertEqual(2, len(records))
        self.assertTrue(records[0].demo_only)
        self.assertEqual("continue_monitoring", records[0].decision)
        self.assertEqual("positive_open", records[0].demo_trade_state)
        self.assertEqual("complete", records[0].action_ledger["ledger_status"])
        self.assertEqual("blocked_by_demo_operator_policy", records[0].action_ledger["orders"])

    def test_history_metrics_counts_mixed_runs_and_clean_safety_totals(self):
        records = [
            SimpleNamespace(
                decision="continue_monitoring",
                human_next_step="run_again_next_trading_day",
                ai_review_action="reviewed",
                operator_status="completed",
                orders_submitted=0,
                orders_cancelled=0,
                positions_closed=0,
                promotions_performed=0,
                demo_only=True,
				run_id="dor-latest",
				created_at=datetime(2026, 8, 17, tzinfo=timezone.utc),
            ),
            SimpleNamespace(
                decision="request_fresh_ai_review",
                human_next_step="optionally_run_confirmed_ai_review",
                ai_review_action="confirmation_required",
                operator_status="completed_with_warnings",
                orders_submitted=0,
                orders_cancelled=0,
                positions_closed=0,
                promotions_performed=0,
                demo_only=True,
            ),
            SimpleNamespace(
                decision="blocked",
                human_next_step="resolve_system_health_or_refresh_required_snapshots",
                ai_review_action="not_requested",
                operator_status="completed",
                orders_submitted=0,
                orders_cancelled=0,
                positions_closed=0,
                promotions_performed=0,
                demo_only=True,
            ),
        ]

        metrics = _operator_run_history_metrics(records)

        self.assertEqual(3, metrics["runs_loaded"])
        self.assertEqual(1, metrics["reviewed_runs"])
        self.assertEqual(1, metrics["confirmation_required_runs"])
        self.assertEqual(1, metrics["not_requested_runs"])
        self.assertEqual(1, metrics["request_fresh_ai_review_runs"])
        self.assertEqual(1, metrics["continue_monitoring_runs"])
        self.assertEqual(1, metrics["blocked_runs"])
        self.assertEqual(2, metrics["completed_runs"])
        self.assertEqual(1, metrics["completed_with_warnings_runs"])
        self.assertEqual(0, metrics["orders_submitted_total"])
        self.assertEqual(True, metrics["latest_run_demo_only"])
        self.assertEqual("clean", metrics["history_health"])
        self.assertEqual(3, metrics["records_checked"])
        self.assertEqual(3, metrics["demo_only_records"])
        self.assertEqual(0, metrics["missing_demo_only_records"])
        self.assertEqual(0, metrics["non_demo_only_records"])
        self.assertEqual(0, metrics["records_with_order_actions"])
        self.assertEqual("dor-latest", metrics["latest_run_id"])
        self.assertEqual("2026-08-17T00:00:00+00:00", metrics["latest_run_created_at"])
        self.assertEqual("continue_monitoring", metrics["latest_run_decision"])
        self.assertEqual("no_operator_safety_violations", metrics["safety_verdict"])

    def test_history_metrics_handles_warning_blocked_and_unknown_safely(self):
        warning = _operator_run_history_metrics(
            [SimpleNamespace(decision="unknown", human_next_step="unknown")]
        )
        non_demo = _operator_run_history_metrics(
            [
                SimpleNamespace(
                    decision="unknown",
                    human_next_step="unknown",
                    demo_only=False,
                    orders_submitted=0,
                    orders_cancelled=0,
                    positions_closed=0,
                    promotions_performed=0,
                )
            ]
        )
        blocked = _operator_run_history_metrics(
            [
                SimpleNamespace(
                    decision="unknown",
                    human_next_step="unknown",
                    demo_only=True,
                    orders_submitted=1,
                    orders_cancelled=0,
                    positions_closed=0,
                    promotions_performed=0,
                )
            ]
        )
        unknown = _operator_run_history_metrics([])

        self.assertEqual("warning", warning["history_health"])
        self.assertEqual("unknown", warning["latest_run_demo_only"])
        self.assertEqual(1, warning["missing_demo_only_records"])
        self.assertEqual("operator_safety_warning", warning["safety_verdict"])
        self.assertEqual("blocked", non_demo["history_health"])
        self.assertEqual(1, non_demo["non_demo_only_records"])
        self.assertEqual("operator_safety_blocked", non_demo["safety_verdict"])
        self.assertEqual("blocked", blocked["history_health"])
        self.assertEqual(1, blocked["orders_submitted_total"])
        self.assertEqual(1, blocked["records_with_order_actions"])
        self.assertEqual("unknown", unknown["history_health"])
        self.assertEqual(0, unknown["records_checked"])
        self.assertEqual("unknown", unknown["safety_verdict"])

    def test_filters_apply_before_display_and_summary_metrics(self):
        records = [
            SimpleNamespace(
                run_id="newest",
                decision="continue_monitoring",
                ai_review_action="reviewed",
                operator_status="completed",
            ),
            SimpleNamespace(
                run_id="middle",
                decision="request_fresh_ai_review",
                ai_review_action="confirmation_required",
                operator_status="completed_with_warnings",
            ),
            SimpleNamespace(
                run_id="oldest",
                decision="request_fresh_ai_review",
                ai_review_action="not_requested",
                operator_status="completed",
            ),
        ]

        limited = _filter_demo_operator_run_records(records=records, limit=2)
        by_decision = _filter_demo_operator_run_records(
            records=records, decision="request_fresh_ai_review"
        )
        by_ai_review = _filter_demo_operator_run_records(
            records=records, ai_review_action="reviewed"
        )
        by_status = _filter_demo_operator_run_records(
            records=records, status="completed_with_warnings"
        )
        combined = _filter_demo_operator_run_records(
            records=records,
            decision="request_fresh_ai_review",
            ai_review_action="confirmation_required",
            status="completed_with_warnings",
            limit=1,
        )

        self.assertEqual(["newest", "middle"], [record.run_id for record in limited])
        self.assertEqual(["middle", "oldest"], [record.run_id for record in by_decision])
        self.assertEqual(["newest"], [record.run_id for record in by_ai_review])
        self.assertEqual(["middle"], [record.run_id for record in by_status])
        self.assertEqual(["middle"], [record.run_id for record in combined])
        self.assertEqual(1, _operator_run_history_metrics(combined)["runs_loaded"])

    def test_unknown_filters_and_nonpositive_limit_return_empty_history(self):
        records = [SimpleNamespace(run_id="only", decision="continue_monitoring")]

        unknown = _filter_demo_operator_run_records(records=records, decision="unknown")
        invalid_limit = _filter_demo_operator_run_records(records=records, limit=0)

        self.assertEqual([], unknown)
        self.assertEqual([], invalid_limit)
        self.assertEqual("unknown", _operator_run_history_metrics(unknown)["history_health"])

    def test_decision_trend_is_stable_for_matching_recent_records(self):
        records = [
            SimpleNamespace(
                decision="continue_monitoring",
                ai_review_action="reviewed",
                human_next_step="run_again_next_trading_day",
                operator_status="completed",
                created_at=datetime(2026, 8, 17, 12, tzinfo=timezone.utc),
            ),
            SimpleNamespace(
                decision="continue_monitoring",
                ai_review_action="reviewed",
                human_next_step="run_again_next_trading_day",
                operator_status="completed",
                created_at=datetime(2026, 8, 17, 11, tzinfo=timezone.utc),
            ),
        ]

        trend = _operator_run_decision_trend(records)

        self.assertEqual(2, trend["trend_records"])
        self.assertEqual("no", trend["decision_changed"])
        self.assertEqual("no", trend["ai_review_action_changed"])
        self.assertEqual("stable", trend["trend_summary"])

    def test_decision_trend_reports_changed_fields_and_filtered_history(self):
        records = [
            SimpleNamespace(
                decision="request_fresh_ai_review",
                ai_review_action="reviewed",
                human_next_step="optionally_run_confirmed_ai_review",
                operator_status="completed",
                created_at=datetime(2026, 8, 17, 12, tzinfo=timezone.utc),
            ),
            SimpleNamespace(
                decision="continue_monitoring",
                ai_review_action="not_requested",
                human_next_step="run_again_next_trading_day",
                operator_status="completed",
                created_at=datetime(2026, 8, 17, 11, tzinfo=timezone.utc),
            ),
            SimpleNamespace(
                decision="continue_monitoring",
                ai_review_action="not_requested",
                human_next_step="run_again_next_trading_day",
                operator_status="completed",
                created_at=datetime(2026, 8, 17, 10, tzinfo=timezone.utc),
            ),
        ]

        changed = _operator_run_decision_trend(records)
        limited = _operator_run_decision_trend(
            _filter_demo_operator_run_records(records=records, limit=1)
        )

        self.assertEqual("yes", changed["decision_changed"])
        self.assertEqual("yes", changed["ai_review_action_changed"])
        self.assertEqual("changed", changed["trend_summary"])
        self.assertEqual("insufficient_history", limited["trend_summary"])
        self.assertEqual("unknown", limited["decision_changed"])

    def test_run_detail_renders_full_audit_record(self):
        record = SimpleNamespace(
            run_id="dor-detail",
            symbol="NVDA",
            created_at=datetime(2026, 8, 17, tzinfo=timezone.utc),
            operator_status="completed",
            system_health="healthy",
            system_blocked=False,
            monitoring_cycle_status="completed",
            dashboard_displayed=True,
            ai_review_requested=False,
            ai_review_confirmed=False,
            ai_calls_made=0,
            daily_ai_reviews_created=0,
            orders_submitted=0,
            orders_cancelled=0,
            positions_closed=0,
            promotions_performed=0,
            decision="continue_monitoring",
            decision_reason="monitoring_state_requires_no_action",
            position_state="open_demo_position",
            demo_trade_state="positive_open",
            evaluation_state="incomplete",
            evaluation_progress="2/5 trading_days",
            evaluation_days_remaining=3,
            exit_action="continue_monitoring",
            new_entry_action="no_new_entry",
            promotion_action="no_promotion",
            ai_review_action="not_requested",
            ai_review_suggested_action="none",
            freshness_state="fresh",
            human_next_step="run_again_next_trading_day",
            blocked_actions="orders,cancellations,position_closes,promotions,live_trading",
            action_ledger={"monitoring": "performed", "ledger_status": "complete"},
            demo_only=True,
        )
        with patch("builtins.print") as mock_print:
            result = _print_demo_operator_run_detail(symbol="NVDA", record=record)

        self.assertIs(record, result)
        mock_print.assert_any_call("Manual Demo Operator Run Detail: NVDA")
        mock_print.assert_any_call("Run Identity")
        mock_print.assert_any_call("operator_run_id=dor-detail")
        mock_print.assert_any_call("Operator Summary")
        mock_print.assert_any_call("Decision Packet")
        mock_print.assert_any_call("Action Ledger")
        mock_print.assert_any_call("Safety Verdict")
        mock_print.assert_any_call("run_safety=clean")

    def test_run_detail_missing_record_returns_safely(self):
        with patch("builtins.print") as mock_print:
            result = _print_demo_operator_run_detail(symbol="NVDA", record=None)

        self.assertIsNone(result)
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("No matching operator run found.")

    def test_run_detail_mode_loads_locally_for_match_and_missing_id(self):
        record = SimpleNamespace(
            run_id="dor-match",
            created_at=datetime(2026, 8, 17, tzinfo=timezone.utc),
            symbol="NVDA",
            demo_only=True,
            orders_submitted=0,
            orders_cancelled=0,
            positions_closed=0,
            promotions_performed=0,
            action_ledger={},
        )
        storage = Mock()
        storage.load_demo_operator_run_records.return_value = [record]
        with patch("builtins.print") as mock_print, patch(
            "urllib.request.urlopen"
        ) as mock_urlopen:
            matched = run_manual_demo_operator_runs(
                symbol="NVDA", storage=storage, run_id="dor-match"
            )
            missing = run_manual_demo_operator_runs(
                symbol="NVDA", storage=storage, run_id="dor-missing"
            )

        self.assertIs(record, matched)
        self.assertIsNone(missing)
        self.assertEqual(2, storage.load_demo_operator_run_records.call_count)
        self.assertTrue(all(call[0].startswith("load_") for call in storage.method_calls))
        mock_urlopen.assert_not_called()
        mock_print.assert_any_call("Manual Demo Operator Run Detail: NVDA")
        mock_print.assert_any_call("operator_run_id=dor-match")
        mock_print.assert_any_call("No matching operator run found.")

    def test_latest_brief_renders_newest_record_and_ledger(self):
        record = SimpleNamespace(
            run_id="dor-latest",
            symbol="NVDA",
            created_at=datetime(2026, 8, 17, 12, tzinfo=timezone.utc),
            decision="continue_monitoring",
            decision_reason="monitoring_state_requires_no_action",
            operator_status="completed",
            system_health="healthy",
            position_state="open_demo_position",
            demo_trade_state="positive_open",
            evaluation_state="incomplete",
            evaluation_progress="2/5 trading_days",
            evaluation_days_remaining=3,
            exit_action="continue_monitoring",
            new_entry_action="no_new_entry",
            promotion_action="no_promotion",
            ai_review_action="not_requested",
            ai_review_suggested_action="none",
            human_next_step="run_again_next_trading_day",
            orders_submitted=0,
            orders_cancelled=0,
            positions_closed=0,
            promotions_performed=0,
            demo_only=True,
            action_ledger={
                "monitoring": "performed",
                "ai_review": "not_requested",
                "orders": "blocked_by_demo_operator_policy",
                "live_trading": "blocked_by_policy",
            },
        )
        with patch("builtins.print") as mock_print:
            result = _print_demo_operator_latest_brief(symbol="NVDA", record=record)

        self.assertIs(record, result)
        mock_print.assert_any_call("Manual Demo Operator Latest Brief: NVDA")
        mock_print.assert_any_call("Latest Operator Brief")
        mock_print.assert_any_call("operator_run_id=dor-latest")
        mock_print.assert_any_call("Action Status")
        mock_print.assert_any_call("monitoring=performed")
        mock_print.assert_any_call("orders=blocked_by_demo_operator_policy")
        mock_print.assert_any_call("Latest Safety")
        mock_print.assert_any_call("run_safety=clean")
        mock_print.assert_any_call("safety_verdict=no_operator_safety_violations")

    def test_latest_brief_loads_newest_record_and_handles_empty_history_read_only(self):
        older = SimpleNamespace(run_id="dor-old", created_at=datetime(2026, 8, 17, 11, tzinfo=timezone.utc))
        newer = SimpleNamespace(
            run_id="dor-new",
            created_at=datetime(2026, 8, 17, 12, tzinfo=timezone.utc),
            demo_only=True,
            orders_submitted=0,
            orders_cancelled=0,
            positions_closed=0,
            promotions_performed=0,
            action_ledger={},
        )
        storage = Mock()
        storage.load_demo_operator_run_records.return_value = [older, newer]
        with patch("builtins.print") as mock_print, patch("urllib.request.urlopen") as mock_urlopen:
            result = run_manual_demo_operator_latest(symbol="NVDA", storage=storage)
            storage.load_demo_operator_run_records.return_value = []
            empty = run_manual_demo_operator_latest(symbol="NVDA", storage=storage)

        self.assertIs(newer, result)
        self.assertIsNone(empty)
        self.assertEqual(2, storage.load_demo_operator_run_records.call_count)
        self.assertTrue(all(call[0].startswith("load_") for call in storage.method_calls))
        mock_urlopen.assert_not_called()
        mock_print.assert_any_call("operator_run_id=dor-new")
        mock_print.assert_any_call("No operator runs found.")


if __name__ == "__main__":
    unittest.main()