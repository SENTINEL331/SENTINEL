import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from research.demo_current_opportunity_rating import build_demo_current_opportunity_ratings
from research.runner import _build_arg_parser, run_manual_demo_current_opportunity_rating


def _snapshot(**overrides):
    values = {
        "performance_snapshot_id": "dpsp-NVDA-001",
        "symbol": "NVDA",
        "order_intent_id": "doi-NVDA-001",
        "broker_order_id": "br-001",
        "demo_trade_candidate_id": "dtc-001",
        "source_hypothesis_id": "hyp-001",
        "snapshot_at": datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        "status": "open",
        "filled_avg_price": 100.0,
        "current_price": 100.2,
        "unrealized_plpc": 0.002,
        "demo_only": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _position(**overrides):
    values = {
        "position_snapshot_id": "dps-NVDA-001",
        "symbol": "NVDA",
        "synced_at": datetime(2026, 8, 13, 13, 0, tzinfo=timezone.utc),
        "status": "open",
        "current_price": 100.2,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _summary(**overrides):
    values = {
        "demo_hypothesis_summary_id": "dhps-NVDA-001",
        "symbol": "NVDA",
        "source_hypothesis_id": "hyp-001",
        "summarized_at": datetime(2026, 8, 13, 14, 0, tzinfo=timezone.utc),
        "trades_evaluated": 3,
        "evaluation_window_complete_count": 1,
        "successful_window_count": 1,
        "risk_breach_count": 0,
        "current_summary_rating": "promising_demo",
        "promotion_readiness": "review_later",
        "total_unrealized_pl": 0.6,
        "total_unrealized_plpc": 0.002,
        "risk_breach_rate": 0.0,
        "completion_rate": 1 / 3,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _storage(*, snapshots=(), positions=(), summaries=(), candidates=(), intents=()):
    storage = Mock()
    storage.load_demo_trade_performance_snapshots.return_value = list(snapshots)
    storage.load_demo_position_snapshots.return_value = list(positions)
    storage.load_demo_hypothesis_performance_summaries.return_value = list(summaries)
    storage.load_demo_trade_candidates.return_value = list(candidates)
    storage.load_demo_order_intents.return_value = list(intents)
    return storage


class DemoCurrentOpportunityRatingTests(unittest.TestCase):
    def test_cli_help_includes_command(self):
        self.assertIn("demo-current-opportunity-rating", _build_arg_parser().format_help())

    def test_is_read_only_and_makes_no_broker_or_market_data_calls(self):
        storage = _storage(snapshots=[_snapshot()], positions=[_position()])
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = build_demo_current_opportunity_ratings(symbol="NVDA", storage=storage)

        mock_urlopen.assert_not_called()
        self.assertFalse(result.records_modified)
        self.assertTrue(storage.method_calls)
        self.assertTrue(all(call[0].startswith("load_") for call in storage.method_calls))

    def test_uses_latest_performance_snapshot_and_separates_ratings(self):
        result = build_demo_current_opportunity_ratings(
            symbol="NVDA",
            storage=_storage(
                snapshots=[
                    _snapshot(
                        performance_snapshot_id="old",
                        snapshot_at=datetime(2026, 8, 12, tzinfo=timezone.utc),
                        current_price=101.0,
                        unrealized_plpc=0.01,
                    ),
                    _snapshot(
                        performance_snapshot_id="new",
                        snapshot_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
                        current_price=100.2,
                        unrealized_plpc=0.002,
                    ),
                ],
                positions=[_position(current_price=100.2)],
            ),
        )

        rating = result.ratings[0]
        self.assertEqual(1, result.ratings_displayed)
        self.assertEqual(100.2, rating.latest_current_price)
        self.assertEqual("flat_open", rating.entry_performance_rating)
        self.assertEqual("caution_new_entry", rating.current_opportunity_rating)

    def test_board_not_ready_and_risk_breach_take_precedence(self):
        not_ready = build_demo_current_opportunity_ratings(
            symbol="NVDA",
            storage=_storage(snapshots=[_snapshot()], positions=[_position()], summaries=[
                _summary(trades_evaluated=1, evaluation_window_complete_count=0, successful_window_count=0, current_summary_rating="needs_more_time", promotion_readiness="not_ready")
            ]),
        )
        self.assertEqual("not_ready", not_ready.ratings[0].current_opportunity_rating)

        blocked = build_demo_current_opportunity_ratings(
            symbol="NVDA",
            storage=_storage(snapshots=[_snapshot()], positions=[_position()], summaries=[_summary(risk_breach_count=1, current_summary_rating="risk_breach")]),
        )
        self.assertEqual("blocked", blocked.ratings[0].current_opportunity_rating)

    def test_open_trade_is_conservative_and_attractive_requires_positive_evidence(self):
        positive_open = build_demo_current_opportunity_ratings(
            symbol="NVDA",
            storage=_storage(snapshots=[_snapshot(current_price=101.0, unrealized_plpc=0.01)], positions=[_position(current_price=101.0)], summaries=[_summary()]),
        )
        self.assertEqual("avoid_new_entry", positive_open.ratings[0].current_opportunity_rating)

        completed_setup = build_demo_current_opportunity_ratings(
            symbol="NVDA",
            storage=_storage(snapshots=[_snapshot(status="closed", current_price=100.2)], positions=[_position(current_price=100.2)], summaries=[_summary()]),
        )
        self.assertEqual("attractive_now", completed_setup.ratings[0].current_opportunity_rating)

    def test_handles_no_snapshots_safely(self):
        result = build_demo_current_opportunity_ratings(symbol="NVDA", storage=_storage())
        self.assertEqual(0, result.ratings_displayed)
        self.assertEqual(0, result.rating_counts["unknown"])

    def test_runner_prints_read_only_contract(self):
        result = SimpleNamespace(ratings_displayed=0, ratings=(), rating_counts={})
        with patch("builtins.print") as mock_print:
            run_manual_demo_current_opportunity_rating(
                symbol="NVDA", rating_fn=Mock(return_value=result)
            )

        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("Broker Calls Allowed : no")
        mock_print.assert_any_call("Market Data Calls Allowed : no")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Position Close Allowed : no")


if __name__ == "__main__":
    unittest.main()