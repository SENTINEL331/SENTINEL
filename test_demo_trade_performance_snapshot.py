import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai.storage import Storage
from research.demo_trade_performance_snapshot import build_demo_trade_performance_snapshots
from research.runner import run_manual_demo_trade_performance_snapshot


def _record(**overrides):
    base = {
        "broker_order_id": "br-001",
        "order_intent_id": "doi-NVDA-001",
        "symbol": "NVDA",
        "queue_item_id": "dtq-NVDA-001",
        "demo_trade_candidate_id": "dtc-001",
        "source_hypothesis_id": "hyp-001",
        "created_at": datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        "status": "submitted",
        "demo_only": True,
        "side": "buy",
        "order_type": "market",
        "time_in_force": "day",
        "notional": 100.0,
        "quantity": None,
        "limit_price": None,
        "stop_price": None,
        "broker": "alpaca",
        "mode": "paper",
        "api_response_status": "accepted",
        "rationale": "Demo paper order submitted append-only.",
        "created_by": "sentinel",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _status(**overrides):
    base = {
        "broker_order_status_id": "bos-001",
        "broker_order_record_id": "br-001",
        "order_intent_id": "doi-NVDA-001",
        "symbol": "NVDA",
        "broker": "alpaca",
        "broker_mode": "paper",
        "broker_order_id": "br-001",
        "synced_at": datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        "status": "filled",
        "raw_status": "filled",
        "filled_qty": 2.0,
        "filled_avg_price": 100.0,
        "submitted_notional": 100.0,
        "submitted_quantity": None,
        "demo_only": True,
        "created_by": "sentinel",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _position_snapshot(**overrides):
    base = {
        "position_snapshot_id": "dps-NVDA-001",
        "symbol": "NVDA",
        "broker": "alpaca",
        "broker_mode": "paper",
        "synced_at": datetime(2026, 8, 13, 12, 5, tzinfo=timezone.utc),
        "status": "open",
        "qty": 2.0,
        "side": "long",
        "market_value": 220.0,
        "cost_basis": 200.0,
        "avg_entry_price": 100.0,
        "current_price": 110.0,
        "unrealized_pl": 20.0,
        "unrealized_plpc": 0.1,
        "asset_id": "asset-1",
        "exchange": "NASDAQ",
        "demo_only": True,
        "created_by": "sentinel",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _intent(**overrides):
    base = {
        "order_intent_id": "doi-NVDA-001",
        "symbol": "NVDA",
        "queue_item_id": "dtq-NVDA-001",
        "demo_trade_candidate_id": "dtc-001",
        "source_hypothesis_id": "hyp-001",
        "created_at": datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        "status": "submitted",
        "demo_only": True,
        "side": "buy",
        "order_type": "market",
        "time_in_force": "day",
        "notional": 100.0,
        "quantity": None,
        "limit_price": None,
        "stop_price": None,
        "max_loss_per_trade": 0.01,
        "max_portfolio_exposure": 0.05,
        "intent_reason": "queued_demo_trade_candidate",
        "created_by": "sentinel",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class DemoTradePerformanceSnapshotTests(unittest.TestCase):
    def test_no_http_or_broker_call(self):
        storage = Mock()
        storage.load_demo_broker_order_records.return_value = []
        storage.load_demo_broker_order_statuses.return_value = []
        storage.load_demo_position_snapshots.return_value = []
        storage.load_demo_order_intents.return_value = []

        with patch("research.demo_trade_performance_snapshot.settings.DEMO_BROKER_MODE", "paper"), patch(
            "builtins.print"
        ):
            result = build_demo_trade_performance_snapshots(symbol="NVDA", storage=storage)

        self.assertEqual(0, result.broker_orders_loaded)
        storage.save_demo_trade_performance_snapshot.assert_not_called()

    def test_builds_per_order_performance_from_filled_status_and_latest_position_snapshot(self):
        storage = Mock()
        storage.load_demo_broker_order_records.return_value = [_record()]
        storage.load_demo_broker_order_statuses.return_value = [_status()]
        storage.load_demo_position_snapshots.return_value = [_position_snapshot()]
        storage.load_demo_order_intents.return_value = [_intent()]

        with patch("research.demo_trade_performance_snapshot.settings.DEMO_BROKER_MODE", "paper"):
            result = build_demo_trade_performance_snapshots(symbol="NVDA", storage=storage)

        self.assertEqual(1, result.broker_orders_loaded)
        self.assertEqual(1, result.filled_orders_evaluated)
        self.assertEqual(1, result.performance_snapshots_created)
        self.assertEqual(20.0, result.total_unrealized_pl)
        self.assertEqual(220.0, result.total_current_value)
        self.assertEqual(200.0, result.total_entry_value)
        storage.save_demo_trade_performance_snapshot.assert_called_once()
        snapshot = storage.save_demo_trade_performance_snapshot.call_args.args[0]
        self.assertEqual("open", snapshot.status)
        self.assertEqual("long", snapshot.side)
        self.assertEqual(2.0, snapshot.filled_qty)
        self.assertEqual(100.0, snapshot.filled_avg_price)
        self.assertEqual(110.0, snapshot.current_price)

    def test_skips_not_filled_orders(self):
        storage = Mock()
        storage.load_demo_broker_order_records.return_value = [_record()]
        storage.load_demo_broker_order_statuses.return_value = [_status(status="submitted", raw_status="submitted")]
        storage.load_demo_position_snapshots.return_value = [_position_snapshot()]
        storage.load_demo_order_intents.return_value = [_intent()]

        with patch("research.demo_trade_performance_snapshot.settings.DEMO_BROKER_MODE", "paper"):
            result = build_demo_trade_performance_snapshots(symbol="NVDA", storage=storage)

        self.assertEqual(1, result.skipped_not_filled)
        self.assertEqual(0, result.performance_snapshots_created)
        storage.save_demo_trade_performance_snapshot.assert_not_called()

    def test_handles_missing_position_snapshot_safely(self):
        storage = Mock()
        storage.load_demo_broker_order_records.return_value = [_record()]
        storage.load_demo_broker_order_statuses.return_value = [_status()]
        storage.load_demo_position_snapshots.return_value = []
        storage.load_demo_order_intents.return_value = [_intent()]

        with patch("research.demo_trade_performance_snapshot.settings.DEMO_BROKER_MODE", "paper"):
            result = build_demo_trade_performance_snapshots(symbol="NVDA", storage=storage)

        self.assertEqual(1, result.skipped_missing_position)
        self.assertEqual(0, result.performance_snapshots_created)
        storage.save_demo_trade_performance_snapshot.assert_not_called()

    def test_handles_zero_entry_value_safely(self):
        storage = Mock()
        storage.load_demo_broker_order_records.return_value = [_record()]
        storage.load_demo_broker_order_statuses.return_value = [_status(filled_qty=0.0, filled_avg_price=100.0)]
        storage.load_demo_position_snapshots.return_value = [_position_snapshot(current_price=110.0)]
        storage.load_demo_order_intents.return_value = [_intent()]

        with patch("research.demo_trade_performance_snapshot.settings.DEMO_BROKER_MODE", "paper"):
            result = build_demo_trade_performance_snapshots(symbol="NVDA", storage=storage)

        self.assertEqual(0.0, result.total_entry_value)
        self.assertEqual(0.0, result.total_unrealized_plpc)
        snapshot = storage.save_demo_trade_performance_snapshot.call_args.args[0]
        self.assertEqual(0.0, snapshot.unrealized_plpc)

    def test_runner_prints_local_summary(self):
        result = Mock(
            broker_orders_loaded=1,
            filled_orders_evaluated=1,
            performance_snapshots_created=1,
            skipped_not_filled=0,
            skipped_missing_position=0,
            failed_calculations=0,
            records_modified=True,
            snapshots=(
                SimpleNamespace(
                    performance_snapshot_id="dpsp-NVDA-001",
                    order_intent_id="doi-NVDA-001",
                    broker_order_id="br-001",
                    source_hypothesis_id="hyp-001",
                    demo_trade_candidate_id="dtc-001",
                    status="open",
                    side="long",
                    filled_qty=2.0,
                    filled_avg_price=100.0,
                    current_price=110.0,
                    entry_value=200.0,
                    current_value=220.0,
                    unrealized_pl=20.0,
                    unrealized_plpc=0.1,
                    demo_only=True,
                ),
            ),
            total_entry_value=200.0,
            total_current_value=220.0,
            total_unrealized_pl=20.0,
            total_unrealized_plpc=0.1,
        )

        with patch("builtins.print") as mock_print:
            run_manual_demo_trade_performance_snapshot(performance_snapshot_fn=Mock(return_value=result))

        mock_print.assert_any_call("Manual Demo Trade Performance Snapshot: NVDA")
        mock_print.assert_any_call("Records Modified : yes")
        mock_print.assert_any_call("Broker Calls Allowed : no")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Order Cancellation Allowed : no")
        mock_print.assert_any_call("Position Close Allowed : no")
        mock_print.assert_any_call("Live Mode Allowed : no")
        mock_print.assert_any_call("Broker Orders Loaded : 1")
        mock_print.assert_any_call("Filled Orders Evaluated : 1")
        mock_print.assert_any_call("Performance Snapshots Created : 1")
        mock_print.assert_any_call("Skipped Not Filled : 0")
        mock_print.assert_any_call("Skipped Missing Position : 0")
        mock_print.assert_any_call("Failed Calculations : 0")
        mock_print.assert_any_call("- performance_snapshot_id=dpsp-NVDA-001")
        mock_print.assert_any_call("  order_intent_id=doi-NVDA-001")
        mock_print.assert_any_call("  broker_order_id=br-001")
        mock_print.assert_any_call("  source_hypothesis_id=hyp-001")
        mock_print.assert_any_call("  demo_trade_candidate_id=dtc-001")
        mock_print.assert_any_call("  status=open")
        mock_print.assert_any_call("  side=long")
        mock_print.assert_any_call("  filled_qty=2.0")
        mock_print.assert_any_call("  filled_avg_price=100.0")
        mock_print.assert_any_call("  current_price=110.0")
        mock_print.assert_any_call("  entry_value=200.0")
        mock_print.assert_any_call("  current_value=220.0")
        mock_print.assert_any_call("  unrealized_pl=20.0")
        mock_print.assert_any_call("  unrealized_plpc=0.1")
        mock_print.assert_any_call("  demo_only=True")
        mock_print.assert_any_call("total_entry_value=200.0")
        mock_print.assert_any_call("total_current_value=220.0")
        mock_print.assert_any_call("total_unrealized_pl=20.0")
        mock_print.assert_any_call("total_unrealized_plpc=0.1")


if __name__ == "__main__":
    unittest.main()