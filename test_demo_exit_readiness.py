import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from research.demo_exit_readiness import build_demo_exit_readiness
from research.runner import _build_arg_parser, run_manual_demo_exit_readiness


def _snapshot(**overrides):
    values = {
        "performance_snapshot_id": "perf-001",
        "symbol": "NVDA",
        "order_intent_id": "intent-001",
        "broker_order_id": "broker-001",
        "demo_trade_candidate_id": "candidate-001",
        "source_hypothesis_id": "hyp-001",
        "snapshot_at": datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        "status": "open",
        "filled_avg_price": 100.0,
        "current_price": 100.0,
        "unrealized_plpc": 0.0,
        "entry_value": 100.0,
        "current_value": 100.0,
        "unrealized_pl": 0.0,
        "demo_only": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _position(**overrides):
    values = {
        "position_snapshot_id": "position-001",
        "symbol": "NVDA",
        "synced_at": datetime(2026, 8, 13, 13, 0, tzinfo=timezone.utc),
        "status": "open",
        "qty": 1.0,
        "market_value": 100.0,
        "cost_basis": 100.0,
        "unrealized_pl": 0.0,
        "unrealized_plpc": 0.0,
        "current_price": 100.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _evaluation(**overrides):
    values = {
        "demo_trade_evaluation_id": "evaluation-001",
        "symbol": "NVDA",
        "performance_snapshot_id": "perf-001",
        "order_intent_id": "intent-001",
        "broker_order_id": "broker-001",
        "source_hypothesis_id": "hyp-001",
        "evaluated_at": datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc),
        "evaluation_status": "needs_more_time",
        "recommended_action": "continue_monitoring",
        "evaluation_window_complete": False,
        "current_rating": "flat_open",
        "risk_breached": False,
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


class DemoExitReadinessTests(unittest.TestCase):
    def test_cli_help_includes_exit_readiness(self):
        self.assertIn("demo-exit-readiness", _build_arg_parser().format_help())

    def test_is_read_only_and_makes_no_network_calls(self):
        storage = _storage(
            snapshots=[_snapshot()],
            positions=[_position()],
            evaluations=[_evaluation()],
            summaries=[_summary()],
        )
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = build_demo_exit_readiness(symbol="NVDA", storage=storage)

        mock_urlopen.assert_not_called()
        self.assertFalse(result.records_modified)
        self.assertTrue(all(call[0].startswith("load_") for call in storage.method_calls))

    def test_incomplete_evaluation_maps_to_needs_more_time(self):
        result = build_demo_exit_readiness(
            symbol="NVDA",
            storage=_storage(
                snapshots=[_snapshot()],
                positions=[_position()],
                evaluations=[_evaluation()],
                summaries=[_summary()],
            ),
        )

        item = result.items[0]
        self.assertEqual("needs_more_time", item.exit_readiness)
        self.assertEqual("continue_monitoring", item.action)

    def test_risk_breach_and_loss_threshold_map_to_risk_exit_candidate(self):
        for evaluation, snapshot in (
            (_evaluation(risk_breached=True), _snapshot()),
            (_evaluation(), _snapshot(unrealized_plpc=-0.02, current_price=98.0)),
        ):
            with self.subTest(snapshot=snapshot):
                result = build_demo_exit_readiness(
                    symbol="NVDA",
                    storage=_storage(
                        snapshots=[snapshot],
                        positions=[_position(current_price=98.0)],
                        evaluations=[evaluation],
                        summaries=[_summary()],
                    ),
                )
                self.assertEqual("risk_exit_candidate", result.items[0].exit_readiness)
                self.assertEqual("prepare_risk_exit_review_only", result.items[0].action)

    def test_weak_completed_evaluation_maps_to_exit_candidate(self):
        result = build_demo_exit_readiness(
            symbol="NVDA",
            storage=_storage(
                snapshots=[_snapshot()],
                positions=[_position()],
                evaluations=[
                    _evaluation(
                        evaluation_status="weak_window",
                        evaluation_window_complete=True,
                        current_rating="weak_open",
                    )
                ],
                summaries=[_summary()],
            ),
        )

        self.assertEqual("exit_candidate", result.items[0].exit_readiness)
        self.assertEqual("prepare_exit_review_only", result.items[0].action)

    def test_closed_trade_maps_to_no_position_and_empty_state_is_safe(self):
        closed = build_demo_exit_readiness(
            symbol="NVDA",
            storage=_storage(
                snapshots=[_snapshot(status="closed")],
                positions=[_position(status="no_position")],
                evaluations=[_evaluation()],
                summaries=[_summary()],
            ),
        )
        self.assertEqual("no_position", closed.items[0].exit_readiness)
        self.assertEqual("no_action", closed.items[0].action)

        empty = build_demo_exit_readiness(symbol="NVDA", storage=_storage())
        self.assertEqual(0, empty.readiness_displayed)
        self.assertEqual(0, empty.readiness_counts["unknown"])

    def test_runner_prints_read_only_contract(self):
        result = SimpleNamespace(items=(), readiness_counts={})
        with patch("builtins.print") as mock_print:
            run_manual_demo_exit_readiness(
                symbol="NVDA", readiness_fn=Mock(return_value=result)
            )

        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("Broker Calls Allowed : no")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Position Close Allowed : no")
        mock_print.assert_any_call("Exit Orders Created : 0")
        mock_print.assert_any_call("Positions Closed : 0")


if __name__ == "__main__":
    unittest.main()