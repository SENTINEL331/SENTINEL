import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from research.demo_status_dashboard import build_demo_status_dashboard
from research.runner import _build_arg_parser, run_manual_demo_status_dashboard


def _snapshot(**overrides):
    values = {
        "performance_snapshot_id": "dpsp-NVDA-new",
        "symbol": "NVDA",
        "order_intent_id": "doi-001",
        "broker_order_id": "br-001",
        "demo_trade_candidate_id": "dtc-001",
        "source_hypothesis_id": "hyp-001",
        "snapshot_at": datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        "status": "open",
        "side": "long",
        "filled_avg_price": 100.0,
        "current_price": 100.2,
        "entry_value": 200.0,
        "current_value": 200.4,
        "unrealized_pl": 0.4,
        "unrealized_plpc": 0.002,
        "demo_only": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _position(**overrides):
    values = {
        "position_snapshot_id": "pos-001",
        "symbol": "NVDA",
        "synced_at": datetime(2026, 8, 13, 13, 0, tzinfo=timezone.utc),
        "status": "open",
        "qty": 2.0,
        "market_value": 200.4,
        "cost_basis": 200.0,
        "unrealized_pl": 0.4,
        "unrealized_plpc": 0.002,
        "current_price": 100.2,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _evaluation(**overrides):
    values = {
        "demo_trade_evaluation_id": "eval-001",
        "symbol": "NVDA",
        "performance_snapshot_id": "dpsp-NVDA-new",
        "order_intent_id": "doi-001",
        "broker_order_id": "br-001",
        "source_hypothesis_id": "hyp-001",
        "evaluated_at": datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc),
        "evaluation_status": "needs_more_time",
        "recommended_action": "continue_monitoring",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _summary(**overrides):
    values = {
        "demo_hypothesis_summary_id": "summary-001",
        "symbol": "NVDA",
        "source_hypothesis_id": "hyp-001",
        "summarized_at": datetime(2026, 8, 13, 15, 0, tzinfo=timezone.utc),
        "trades_evaluated": 1,
        "evaluation_window_complete_count": 0,
        "risk_breach_count": 0,
        "current_summary_rating": "needs_more_time",
        "promotion_readiness": "not_ready",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _storage(*, snapshots=(), positions=(), evaluations=(), summaries=()):
    storage = Mock()
    storage.load_demo_trade_performance_snapshots.return_value = list(snapshots)
    storage.load_demo_position_snapshots.return_value = list(positions)
    storage.load_demo_trade_evaluations.return_value = list(evaluations)
    storage.load_demo_hypothesis_performance_summaries.return_value = list(summaries)
    storage.load_demo_trade_candidates.return_value = []
    storage.load_demo_order_intents.return_value = []
    return storage


class DemoStatusDashboardTests(unittest.TestCase):
    def test_cli_help_includes_status_dashboard(self):
        self.assertIn("demo-status-dashboard", _build_arg_parser().format_help())

    def test_combines_latest_local_records(self):
        result = build_demo_status_dashboard(
            symbol="NVDA",
            storage=_storage(
                snapshots=[
                    _snapshot(
                        performance_snapshot_id="old",
                        snapshot_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
                        current_price=105.0,
                    ),
                    _snapshot(),
                ],
                positions=[_position()],
                evaluations=[
                    _evaluation(
                        demo_trade_evaluation_id="eval-old",
                        evaluated_at=datetime(2026, 8, 13, 13, 0, tzinfo=timezone.utc),
                        evaluation_status="unknown",
                    ),
                    _evaluation(),
                ],
                summaries=[_summary()],
            ),
        )

        self.assertEqual(1, len(result.trades))
        self.assertEqual(100.2, result.trades[0].current_price)
        self.assertEqual("needs_more_time", result.trades[0].trade_evaluation_status)
        self.assertEqual("continue_monitoring", result.trades[0].trade_recommended_action)
        self.assertEqual("not_ready", result.trades[0].board_recommendation)
        self.assertEqual("not_ready", result.trades[0].current_opportunity_rating)
        self.assertEqual("needs_more_time", result.trades[0].exit_readiness)
        self.assertEqual("evaluation_window_incomplete", result.trades[0].exit_reason)
        self.assertEqual("continue_monitoring", result.trades[0].exit_action)
        self.assertEqual(1, result.rating_counts["exit_needs_more_time"])
        self.assertEqual(0, result.rating_counts["exit_candidate"])
        self.assertEqual(0, result.rating_counts["risk_exit_candidate"])
        self.assertEqual(1, result.open_demo_trades)
        self.assertEqual(200.0, result.total_entry_value)
        self.assertEqual(200.4, result.total_current_value)

    def test_is_read_only_and_makes_no_network_calls(self):
        storage = _storage()
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = build_demo_status_dashboard(symbol="NVDA", storage=storage)

        mock_urlopen.assert_not_called()
        self.assertFalse(result.records_modified)
        self.assertTrue(all(call[0].startswith("load_") for call in storage.method_calls))

    def test_handles_missing_local_state_safely(self):
        result = build_demo_status_dashboard(symbol="NVDA", storage=_storage())

        self.assertIsNone(result.position_snapshot)
        self.assertEqual((), result.trades)
        self.assertEqual((), result.hypotheses)
        self.assertEqual(0, result.open_demo_trades)

    def test_runner_prints_read_only_contract(self):
        result = SimpleNamespace(
            position_snapshot=None,
            trades=(),
            hypotheses=(),
            open_demo_trades=0,
            total_entry_value=0.0,
            total_current_value=0.0,
            total_unrealized_pl=0.0,
            total_unrealized_plpc=0.0,
            rating_counts={},
        )
        with patch("builtins.print") as mock_print:
            run_manual_demo_status_dashboard(
                symbol="NVDA", dashboard_fn=Mock(return_value=result)
            )

        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("Broker Calls Allowed : no")
        mock_print.assert_any_call("Market Data Calls Allowed : no")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Position Close Allowed : no")
        mock_print.assert_any_call("Promotion Actions Taken : 0")


if __name__ == "__main__":
    unittest.main()