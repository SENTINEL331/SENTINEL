import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from ai.storage import Storage
from research.demo_operator_run_record import new_demo_operator_run_record
from research.runner import (
    _filter_demo_operator_run_records,
    _operator_run_history_metrics,
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


if __name__ == "__main__":
    unittest.main()