import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from research.demo_promotion_board import build_demo_promotion_board
from research.runner import _build_arg_parser, run_manual_demo_promotion_board


def _summary(**overrides):
    values = {
        "demo_hypothesis_summary_id": "dhps-NVDA-001",
        "symbol": "NVDA",
        "source_hypothesis_id": "hyp-001",
        "summarized_at": datetime(2026, 8, 12, tzinfo=timezone.utc),
        "trades_evaluated": 3,
        "evaluation_window_complete_count": 1,
        "risk_breach_count": 0,
        "current_summary_rating": "promising_demo",
        "promotion_readiness": "review_later",
        "total_unrealized_pl": 20.0,
        "total_unrealized_plpc": 0.1,
        "risk_breach_rate": 0.0,
        "completion_rate": 1 / 3,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _storage(summaries=()):
    storage = Mock()
    storage.load_demo_hypothesis_performance_summaries.return_value = list(summaries)
    return storage


class DemoPromotionBoardTests(unittest.TestCase):
    def test_cli_help_includes_board_command(self):
        self.assertIn("demo-promotion-board", _build_arg_parser().format_help())

    def test_is_read_only_and_makes_no_broker_calls(self):
        storage = _storage([_summary()])
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = build_demo_promotion_board(symbol="NVDA", storage=storage)

        mock_urlopen.assert_not_called()
        self.assertFalse(result.records_modified)
        self.assertEqual(["load_demo_hypothesis_performance_summaries"], [call[0] for call in storage.method_calls])

    def test_uses_latest_summary_per_source_hypothesis(self):
        result = build_demo_promotion_board(
            symbol="NVDA",
            storage=_storage(
                [
                    _summary(demo_hypothesis_summary_id="old", summarized_at=datetime(2026, 8, 11, tzinfo=timezone.utc)),
                    _summary(demo_hypothesis_summary_id="new", summarized_at=datetime(2026, 8, 13, tzinfo=timezone.utc), trades_evaluated=4),
                ]
            ),
        )

        self.assertEqual(1, result.board_items_displayed)
        self.assertEqual("new", result.board_items[0].latest_summary_id)
        self.assertEqual(4, result.board_items[0].trades_evaluated)

    def test_recommendation_precedence_and_reasons(self):
        cases = [
            (_summary(risk_breach_count=1), "blocked", ("risk_breach_detected",)),
            (_summary(trades_evaluated=1, evaluation_window_complete_count=0), "not_ready", ("only_1_demo_trade", "no_completed_evaluation_window")),
            (_summary(trades_evaluated=3, evaluation_window_complete_count=0, current_summary_rating="needs_more_time", promotion_readiness="monitor"), "monitor", ("active_demo_needs_more_time",)),
            (_summary(promotion_readiness="review_later"), "review_later", ("limited_forward_evidence",)),
        ]

        for summary, expected_recommendation, expected_reasons in cases:
            with self.subTest(expected_recommendation=expected_recommendation):
                item = build_demo_promotion_board(symbol="NVDA", storage=_storage([summary])).board_items[0]
                self.assertEqual(expected_recommendation, item.board_recommendation)
                self.assertEqual(expected_reasons, item.board_reason)

    def test_missing_data_and_empty_state_are_safe(self):
        missing = _summary(current_summary_rating="", promotion_readiness="")
        result = build_demo_promotion_board(symbol="NVDA", storage=_storage([missing]))
        self.assertEqual("unknown", result.board_items[0].board_recommendation)
        self.assertEqual(("missing_demo_summary_data",), result.board_items[0].board_reason)

        empty = build_demo_promotion_board(symbol="NVDA", storage=_storage())
        self.assertEqual(0, empty.hypothesis_summaries_loaded)
        self.assertEqual(0, empty.board_items_displayed)

    def test_runner_prints_read_only_contract(self):
        with patch("builtins.print") as mock_print:
            run_manual_demo_promotion_board(symbol="NVDA", storage=_storage())

        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("Promotion Actions Taken : 0")
        mock_print.assert_any_call("Broker Calls Allowed : no")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Order Cancellation Allowed : no")
        mock_print.assert_any_call("Position Close Allowed : no")


if __name__ == "__main__":
    unittest.main()