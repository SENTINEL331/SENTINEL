import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai.storage import Storage
from research.demo_operator_run_record import new_demo_operator_run_record
from research.runner import _operator_run_history_metrics


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

    def test_history_metrics_handles_warning_blocked_and_unknown_safely(self):
        warning = _operator_run_history_metrics(
            [SimpleNamespace(decision="unknown", human_next_step="unknown")]
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
        self.assertEqual("blocked", blocked["history_health"])
        self.assertEqual(1, blocked["orders_submitted_total"])
        self.assertEqual("unknown", unknown["history_health"])


if __name__ == "__main__":
    unittest.main()