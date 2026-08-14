import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from research.demo_trade_performance_dashboard import (
    build_demo_trade_performance_dashboard,
    rate_unrealized_plpc,
)
from research.runner import _build_arg_parser, run_manual_demo_trade_performance_dashboard


def _performance_snapshot(**overrides):
    base = {
        "performance_snapshot_id": "dpsp-NVDA-001",
        "symbol": "NVDA",
        "order_intent_id": "doi-NVDA-001",
        "broker_order_id": "br-001",
        "broker_order_record_id": "br-001",
        "queue_item_id": "dtq-NVDA-001",
        "demo_trade_candidate_id": "dtc-001",
        "source_hypothesis_id": "hyp-001",
        "snapshot_at": datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        "status": "open",
        "side": "long",
        "filled_qty": 2.0,
        "filled_avg_price": 100.0,
        "current_price": 110.0,
        "entry_value": 200.0,
        "current_value": 220.0,
        "unrealized_pl": 20.0,
        "unrealized_plpc": 0.1,
        "position_snapshot_id": "dps-NVDA-001",
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
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _candidate(**overrides):
    base = {
        "trade_candidate_id": "dtc-001",
        "symbol": "NVDA",
        "source_hypothesis_id": "hyp-001",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _storage(snapshots=(), intents=(), candidates=(), positions=()):
    storage = Mock()
    storage.load_demo_trade_performance_snapshots.return_value = list(snapshots)
    storage.load_demo_order_intents.return_value = list(intents)
    storage.load_demo_trade_candidates.return_value = list(candidates)
    storage.load_demo_position_snapshots.return_value = list(positions)
    return storage


class DemoTradePerformanceDashboardTests(unittest.TestCase):
    def test_cli_help_includes_dashboard_command(self):
        parser = _build_arg_parser()

        self.assertIn("demo-trade-performance-dashboard", parser.format_help())

    def test_is_read_only_and_writes_nothing(self):
        storage = _storage(
            snapshots=[_performance_snapshot()],
            intents=[_intent()],
            candidates=[_candidate()],
            positions=[_position_snapshot()],
        )

        build_demo_trade_performance_dashboard(symbol="NVDA", storage=storage)

        called_methods = {call[0] for call in storage.method_calls}
        self.assertTrue(called_methods)
        for name in called_methods:
            self.assertTrue(name.startswith("load_"), name)

    def test_makes_no_broker_or_http_calls(self):
        storage = _storage(
            snapshots=[_performance_snapshot()],
            positions=[_position_snapshot()],
        )

        with patch("urllib.request.urlopen") as mock_urlopen:
            result = build_demo_trade_performance_dashboard(symbol="NVDA", storage=storage)

        mock_urlopen.assert_not_called()
        self.assertFalse(result.records_modified)

    def test_uses_latest_performance_snapshot_per_broker_order(self):
        storage = _storage(
            snapshots=[
                _performance_snapshot(
                    performance_snapshot_id="dpsp-NVDA-old",
                    snapshot_at=datetime(2026, 8, 13, 11, 0, tzinfo=timezone.utc),
                    unrealized_plpc=-0.05,
                    unrealized_pl=-10.0,
                    current_value=190.0,
                ),
                _performance_snapshot(
                    performance_snapshot_id="dpsp-NVDA-new",
                    snapshot_at=datetime(2026, 8, 13, 13, 0, tzinfo=timezone.utc),
                ),
            ],
            positions=[_position_snapshot()],
        )

        result = build_demo_trade_performance_dashboard(symbol="NVDA", storage=storage)

        self.assertEqual(2, result.performance_snapshots_loaded)
        self.assertEqual(1, result.latest_trades_displayed)
        self.assertEqual(0.1, result.trades[0].unrealized_plpc)
        self.assertEqual("positive_open", result.trades[0].current_rating)

    def test_groups_by_order_intent_id_when_broker_order_id_missing(self):
        storage = _storage(
            snapshots=[
                _performance_snapshot(broker_order_id="", snapshot_at=datetime(2026, 8, 13, 11, 0, tzinfo=timezone.utc)),
                _performance_snapshot(broker_order_id="", snapshot_at=datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)),
            ],
        )

        result = build_demo_trade_performance_dashboard(symbol="NVDA", storage=storage)

        self.assertEqual(1, result.latest_trades_displayed)
        self.assertEqual("doi-NVDA-001", result.trades[0].order_intent_id)

    def test_calculates_hypothesis_summary_totals(self):
        storage = _storage(
            snapshots=[
                _performance_snapshot(),
                _performance_snapshot(
                    performance_snapshot_id="dpsp-NVDA-002",
                    broker_order_id="br-002",
                    order_intent_id="doi-NVDA-002",
                    entry_value=300.0,
                    current_value=280.0,
                    unrealized_pl=-20.0,
                    unrealized_plpc=-0.0667,
                ),
            ],
            positions=[_position_snapshot()],
        )

        result = build_demo_trade_performance_dashboard(symbol="NVDA", storage=storage)

        self.assertEqual(1, result.hypotheses_displayed)
        summary = result.hypotheses[0]
        self.assertEqual("hyp-001", summary.source_hypothesis_id)
        self.assertEqual(2, summary.trades)
        self.assertEqual(500.0, summary.total_entry_value)
        self.assertEqual(500.0, summary.total_current_value)
        self.assertEqual(0.0, summary.total_unrealized_pl)
        self.assertEqual(0.0, summary.total_unrealized_plpc)
        self.assertEqual("flat_open", summary.current_rating)
        self.assertEqual("not_evaluated", summary.promotion_status)

    def test_assigns_ratings_deterministically(self):
        self.assertEqual("risk_breach", rate_unrealized_plpc(-0.02))
        self.assertEqual("risk_breach", rate_unrealized_plpc(-0.05))
        self.assertEqual("weak_open", rate_unrealized_plpc(-0.01))
        self.assertEqual("flat_open", rate_unrealized_plpc(-0.005))
        self.assertEqual("flat_open", rate_unrealized_plpc(0.0))
        self.assertEqual("flat_open", rate_unrealized_plpc(0.005))
        self.assertEqual("positive_open", rate_unrealized_plpc(0.01))
        self.assertEqual("unknown", rate_unrealized_plpc(None))

    def test_missing_performance_data_is_unknown(self):
        storage = _storage(snapshots=[_performance_snapshot(unrealized_plpc=None)])

        result = build_demo_trade_performance_dashboard(symbol="NVDA", storage=storage)

        self.assertEqual("unknown", result.trades[0].current_rating)

    def test_handles_no_performance_snapshots_safely(self):
        storage = _storage(positions=[_position_snapshot()])

        result = build_demo_trade_performance_dashboard(symbol="NVDA", storage=storage)

        self.assertEqual(0, result.performance_snapshots_loaded)
        self.assertEqual(0, result.latest_trades_displayed)
        self.assertEqual(0, result.hypotheses_displayed)
        self.assertEqual((), result.trades)
        self.assertEqual((), result.hypotheses)

    def test_handles_missing_position_snapshot_safely(self):
        storage = _storage(snapshots=[_performance_snapshot()])

        result = build_demo_trade_performance_dashboard(symbol="NVDA", storage=storage)

        self.assertIsNone(result.position_snapshot)
        self.assertEqual(1, result.latest_trades_displayed)

    def test_uses_latest_position_snapshot(self):
        storage = _storage(
            positions=[
                _position_snapshot(position_snapshot_id="dps-old", synced_at=datetime(2026, 8, 13, 10, 0, tzinfo=timezone.utc)),
                _position_snapshot(position_snapshot_id="dps-new", synced_at=datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc)),
            ],
        )

        result = build_demo_trade_performance_dashboard(symbol="NVDA", storage=storage)

        self.assertEqual("dps-new", result.position_snapshot.position_snapshot_id)

    def test_runner_prints_read_only_dashboard(self):
        storage = _storage(
            snapshots=[_performance_snapshot()],
            intents=[_intent()],
            candidates=[_candidate()],
            positions=[_position_snapshot()],
        )

        with patch("builtins.print") as mock_print:
            run_manual_demo_trade_performance_dashboard(symbol="NVDA", storage=storage)

        mock_print.assert_any_call("Manual Demo Trade Performance Dashboard: NVDA")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Broker Calls Allowed : no")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Order Cancellation Allowed : no")
        mock_print.assert_any_call("Position Close Allowed : no")
        mock_print.assert_any_call("Live Mode Allowed : no")
        mock_print.assert_any_call("Performance Snapshots Loaded : 1")
        mock_print.assert_any_call("Latest Trades Displayed : 1")
        mock_print.assert_any_call("Hypotheses Displayed : 1")
        mock_print.assert_any_call("position_snapshot_id=dps-NVDA-001")
        mock_print.assert_any_call("- source_hypothesis_id=hyp-001")
        mock_print.assert_any_call("  demo_trade_candidate_id=dtc-001")
        mock_print.assert_any_call("  order_intent_id=doi-NVDA-001")
        mock_print.assert_any_call("  broker_order_id=br-001")
        mock_print.assert_any_call("  current_rating=positive_open")
        mock_print.assert_any_call("  promotion_status=not_evaluated")
        mock_print.assert_any_call("  note=Current mark-to-market only. Not a promotion decision.")
        mock_print.assert_any_call("  demo_only=True")

    def test_runner_handles_empty_state(self):
        storage = _storage()

        with patch("builtins.print") as mock_print:
            run_manual_demo_trade_performance_dashboard(symbol="NVDA", storage=storage)

        mock_print.assert_any_call("No position snapshot is available locally.")
        mock_print.assert_any_call("No demo trade performance snapshots are available locally.")
        mock_print.assert_any_call("No hypotheses have demo trade performance data locally.")


if __name__ == "__main__":
    unittest.main()
