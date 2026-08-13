import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ai.storage import Storage
from research.demo_trade_performance_snapshot import DemoTradePerformanceSnapshot


def _snapshot(*, performance_snapshot_id: str, symbol: str):
    return DemoTradePerformanceSnapshot(
        performance_snapshot_id=performance_snapshot_id,
        symbol=symbol,
        order_intent_id=f"doi-{performance_snapshot_id}",
        broker_order_id=f"br-{performance_snapshot_id}",
        broker_order_record_id=f"br-{performance_snapshot_id}",
        queue_item_id=f"dtq-{performance_snapshot_id}",
        demo_trade_candidate_id=f"dtc-{performance_snapshot_id}",
        source_hypothesis_id=f"hyp-{performance_snapshot_id}",
        snapshot_at=datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        status="open",
        side="long",
        filled_qty=2.0,
        filled_avg_price=100.0,
        current_price=110.0,
        entry_value=200.0,
        current_value=220.0,
        unrealized_pl=20.0,
        unrealized_plpc=0.1,
        position_snapshot_id="dps-NVDA-001",
        demo_only=True,
        created_by="sentinel",
    )


class DemoTradePerformanceSnapshotStorageTests(unittest.TestCase):
    def test_storage_appends_and_loads_snapshots(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)
            storage.save_demo_trade_performance_snapshot(_snapshot(performance_snapshot_id="dpsp-001", symbol="NVDA"))
            storage.save_demo_trade_performance_snapshot(_snapshot(performance_snapshot_id="dpsp-002", symbol="AAPL"))

            loaded = storage.load_demo_trade_performance_snapshots()

            self.assertEqual(2, len(loaded))
            self.assertEqual("dpsp-001", loaded[0].performance_snapshot_id)
            self.assertEqual("dpsp-002", loaded[1].performance_snapshot_id)

    def test_symbol_filter_works(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)
            storage.save_demo_trade_performance_snapshot(_snapshot(performance_snapshot_id="dpsp-001", symbol="NVDA"))
            storage.save_demo_trade_performance_snapshot(_snapshot(performance_snapshot_id="dpsp-002", symbol="AAPL"))

            loaded = storage.load_demo_trade_performance_snapshots(symbol="NVDA")

            self.assertEqual(1, len(loaded))
            self.assertEqual("NVDA", loaded[0].symbol)

    def test_round_trip_preserves_metrics_fields(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)
            storage.save_demo_trade_performance_snapshot(_snapshot(performance_snapshot_id="dpsp-003", symbol="NVDA"))

            loaded = storage.load_demo_trade_performance_snapshots(symbol="NVDA")

            self.assertEqual(1, len(loaded))
            self.assertEqual(200.0, loaded[0].entry_value)
            self.assertEqual(220.0, loaded[0].current_value)
            self.assertEqual(20.0, loaded[0].unrealized_pl)
            self.assertEqual(0.1, loaded[0].unrealized_plpc)
            self.assertEqual("dps-NVDA-001", loaded[0].position_snapshot_id)


if __name__ == "__main__":
    unittest.main()