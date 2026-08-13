import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ai.storage import Storage
from research.demo_trade_queue import DemoTradeQueueItem
from research.demo_trade_queue import DemoTradeQueueStatus


def _queue_item(*, queue_item_id: str, symbol: str):
    return DemoTradeQueueItem(
        queue_item_id=queue_item_id,
        symbol=symbol,
        demo_trade_candidate_id=f"dtc-{queue_item_id}",
        source_hypothesis_id=f"hyp-{queue_item_id}",
        created_at=datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        status=DemoTradeQueueStatus.QUEUED,
        demo_only=True,
        queue_reason="candidate_passed_demo_trade_gate",
        risk_summary="limited_experiment_count",
        requested_action="prepare_demo_order",
        created_by="sentinel",
    )


class DemoTradeQueueStorageTests(unittest.TestCase):
    def test_storage_appends_and_loads_queue_items(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)
            first = _queue_item(queue_item_id="dtq-001", symbol="NVDA")
            second = _queue_item(queue_item_id="dtq-002", symbol="AAPL")

            storage.save_demo_trade_queue_item(first)
            storage.save_demo_trade_queue_item(second)

            loaded = storage.load_demo_trade_queue_items()

            self.assertEqual(2, len(loaded))
            self.assertEqual("dtq-001", loaded[0].queue_item_id)
            self.assertEqual("dtq-002", loaded[1].queue_item_id)

    def test_symbol_filter_works(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)
            storage.save_demo_trade_queue_item(_queue_item(queue_item_id="dtq-001", symbol="NVDA"))
            storage.save_demo_trade_queue_item(_queue_item(queue_item_id="dtq-002", symbol="AAPL"))

            loaded = storage.load_demo_trade_queue_items(symbol="NVDA")

            self.assertEqual(1, len(loaded))
            self.assertEqual("NVDA", loaded[0].symbol)


if __name__ == "__main__":
    unittest.main()