import unittest
from datetime import datetime, timedelta, timezone
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
        "trading_days_elapsed": 2,
        "evaluation_window_trading_days": 5,
        "evaluation_window_complete": False,
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


def _storage(*, snapshots=(), positions=(), evaluations=(), summaries=(), reviews=()):
    storage = Mock()
    storage.load_demo_trade_performance_snapshots.return_value = list(snapshots)
    storage.load_demo_position_snapshots.return_value = list(positions)
    storage.load_demo_trade_evaluations.return_value = list(evaluations)
    storage.load_demo_hypothesis_performance_summaries.return_value = list(summaries)
    storage.load_demo_trade_candidates.return_value = []
    storage.load_demo_order_intents.return_value = []
    storage.load_demo_daily_ai_reviews.return_value = list(reviews)
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
        self.assertEqual(2, result.trades[0].trading_days_elapsed)
        self.assertEqual(5, result.trades[0].evaluation_window_trading_days)
        self.assertEqual(3, result.trades[0].evaluation_days_remaining)
        self.assertFalse(result.trades[0].evaluation_window_complete)
        self.assertEqual(0, result.rating_counts["completed_evaluation_windows"])
        self.assertEqual(1, result.rating_counts["incomplete_evaluation_windows"])
        self.assertEqual(3, result.rating_counts["min_evaluation_days_remaining"])
        self.assertEqual(3, result.rating_counts["max_evaluation_days_remaining"])
        self.assertEqual(1, result.open_demo_trades)
        self.assertEqual(200.0, result.total_entry_value)
        self.assertEqual(200.4, result.total_current_value)

    def test_includes_latest_stored_daily_ai_review(self):
        older = SimpleNamespace(
            demo_daily_ai_review_id="old-review",
            reviewed_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
            ai_model="old-model",
            overall_assessment="Old",
            deeper_ai_review_needed=True,
            reason="old_reason",
            confidence="low",
        )
        latest = SimpleNamespace(
            demo_daily_ai_review_id="latest-review",
            reviewed_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
            ai_model="latest-model",
            overall_assessment="Continue monitoring.",
            deeper_ai_review_needed=False,
            reason="evaluation_window_incomplete",
            confidence="high",
        )
        result = build_demo_status_dashboard(
            symbol="NVDA",
            storage=_storage(reviews=[older, latest]),
        )

        self.assertIs(latest, result.latest_daily_ai_review)

    def test_handles_no_stored_daily_ai_review(self):
        result = build_demo_status_dashboard(symbol="NVDA", storage=_storage())
        self.assertIsNone(result.latest_daily_ai_review)

    def test_freshness_uses_required_local_snapshots_without_ai_review(self):
        now = datetime.now(timezone.utc)
        result = build_demo_status_dashboard(
            symbol="NVDA",
            storage=_storage(
                positions=[_position(synced_at=now - timedelta(hours=1))],
                snapshots=[_snapshot(snapshot_at=now - timedelta(hours=2))],
                evaluations=[_evaluation(evaluated_at=now - timedelta(hours=3))],
            ),
        )

        self.assertEqual("fresh", result.staleness_status)
        self.assertEqual("latest_required_snapshots_fresh", result.freshness_reason)
        self.assertIsNone(result.latest_ai_review_at)
        self.assertIsNone(result.latest_ai_review_age_hours)
        self.assertEqual("missing", result.ai_review_freshness)
        self.assertEqual("no_stored_ai_review", result.ai_review_freshness_reason)
        self.assertEqual("no_review_available", result.ai_review_suggested_action)

    def test_ai_review_freshness_detects_behind_and_current_reviews(self):
        now = datetime.now(timezone.utc)
        common = {
            "positions": [_position(synced_at=now - timedelta(hours=2))],
            "snapshots": [_snapshot(snapshot_at=now - timedelta(hours=2))],
            "evaluations": [_evaluation(evaluated_at=now - timedelta(hours=1))],
        }
        behind = build_demo_status_dashboard(
            symbol="NVDA",
            storage=_storage(
                reviews=[SimpleNamespace(reviewed_at=now - timedelta(hours=3))],
                **common,
            ),
        )
        current = build_demo_status_dashboard(
            symbol="NVDA",
            storage=_storage(
                reviews=[SimpleNamespace(reviewed_at=now - timedelta(hours=1))],
                **common,
            ),
        )

        self.assertEqual("behind_latest_snapshot", behind.ai_review_freshness)
        self.assertEqual(
            "ai_review_older_than_latest_required_snapshot",
            behind.ai_review_freshness_reason,
        )
        self.assertEqual(2.0, behind.ai_review_lag_hours)
        self.assertEqual("request_fresh_ai_review", behind.ai_review_suggested_action)
        self.assertEqual(
            "latest_monitoring_snapshot_newer_than_ai_review",
            behind.ai_review_action_reason,
        )
        self.assertEqual("current", current.ai_review_freshness)
        self.assertEqual(0.0, current.ai_review_lag_hours)
        self.assertEqual("none", current.ai_review_suggested_action)

    def test_ai_review_freshness_is_unknown_for_invalid_review_timestamp(self):
        now = datetime.now(timezone.utc)
        result = build_demo_status_dashboard(
            symbol="NVDA",
            storage=_storage(
                positions=[_position(synced_at=now)],
                snapshots=[_snapshot(snapshot_at=now)],
                evaluations=[_evaluation(evaluated_at=now)],
                reviews=[SimpleNamespace(reviewed_at="not-a-timestamp")],
            ),
        )

        self.assertEqual("unknown", result.ai_review_freshness)
        self.assertEqual(
            "ai_review_or_required_snapshot_timestamp_invalid",
            result.ai_review_freshness_reason,
        )

    def test_freshness_warns_or_stales_for_old_required_snapshots(self):
        now = datetime.now(timezone.utc)
        common = {
            "positions": [_position(synced_at=now - timedelta(hours=1))],
            "evaluations": [_evaluation(evaluated_at=now - timedelta(hours=1))],
        }
        warning = build_demo_status_dashboard(
            symbol="NVDA",
            storage=_storage(
                snapshots=[_snapshot(snapshot_at=now - timedelta(hours=25))],
                **common,
            ),
        )
        stale = build_demo_status_dashboard(
            symbol="NVDA",
            storage=_storage(
                snapshots=[_snapshot(snapshot_at=now - timedelta(hours=49))],
                **common,
            ),
        )

        self.assertEqual("warning", warning.staleness_status)
        self.assertEqual("stale", stale.staleness_status)

    def test_freshness_is_unknown_for_missing_or_invalid_required_timestamps(self):
        result = build_demo_status_dashboard(
            symbol="NVDA",
            storage=_storage(
                positions=[_position(synced_at="not-a-timestamp")],
                snapshots=[_snapshot(snapshot_at=datetime.now(timezone.utc))],
                evaluations=[_evaluation(evaluated_at=datetime.now(timezone.utc))],
            ),
        )

        self.assertEqual("unknown", result.staleness_status)
        self.assertEqual(
            "required_snapshot_timestamp_missing_or_invalid", result.freshness_reason
        )

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
			ai_review_freshness="behind_latest_snapshot",
			ai_review_suggested_action="request_fresh_ai_review",
			ai_review_action_reason="latest_monitoring_snapshot_newer_than_ai_review",
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
        mock_print.assert_any_call("Snapshot Freshness")
        mock_print.assert_any_call("latest_ai_review_at=none")
        mock_print.assert_any_call("AI Review Freshness")
        mock_print.assert_any_call("ai_review_suggested_action=request_fresh_ai_review")
        mock_print.assert_any_call(
            "ai_review_action_reason=latest_monitoring_snapshot_newer_than_ai_review"
        )


if __name__ == "__main__":
    unittest.main()