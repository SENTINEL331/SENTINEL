import tempfile
import unittest
from pathlib import Path

from ai.storage import Storage
from research.demo_operator_run_record import new_demo_operator_run_record


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


if __name__ == "__main__":
    unittest.main()