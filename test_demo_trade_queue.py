import unittest
from datetime import datetime, timezone

from research.demo_trade_queue import DemoTradeQueueItem
from research.demo_trade_queue import DemoTradeQueueStatus


class DemoTradeQueueItemTests(unittest.TestCase):
    def test_queue_item_can_be_created(self):
        item = DemoTradeQueueItem(
            queue_item_id="dtq-NVDA-001",
            symbol="NVDA",
            demo_trade_candidate_id="dtc-001",
            source_hypothesis_id="hyp-001",
            created_at=datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
            status=DemoTradeQueueStatus.QUEUED,
            demo_only=True,
            queue_reason="candidate_passed_demo_trade_gate",
            risk_summary="limited_experiment_count",
            requested_action="prepare_demo_order",
            created_by="sentinel",
        )

        self.assertEqual("dtq-NVDA-001", item.queue_item_id)
        self.assertEqual(DemoTradeQueueStatus.QUEUED, item.status)
        self.assertTrue(item.demo_only)


if __name__ == "__main__":
    unittest.main()