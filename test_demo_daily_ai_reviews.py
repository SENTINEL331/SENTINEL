import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from research.runner import _build_arg_parser, run_manual_demo_daily_ai_reviews


def _review(review_id, reviewed_at, **overrides):
    values = {
        "demo_daily_ai_review_id": review_id,
        "symbol": "NVDA",
        "reviewed_at": reviewed_at,
        "ai_model": "test-model",
        "ai_review_type": "daily_light_demo_review",
        "overall_assessment": "Continue monitoring.",
        "demo_trade_assessment": "Early evidence.",
        "exit_assessment": "No exit evidence yet.",
        "promotion_assessment": "No promotion evidence yet.",
        "current_opportunity_assessment": "Not ready.",
        "deeper_ai_review_needed": False,
        "reason": "evaluation_window_incomplete",
        "confidence": "high",
        "demo_only": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class DemoDailyAIReviewsTests(unittest.TestCase):
    def test_cli_help_includes_history_command(self):
        self.assertIn("demo-daily-ai-reviews", _build_arg_parser().format_help())

    def test_displays_reviews_newest_first(self):
        storage = Mock()
        storage.load_demo_daily_ai_reviews.return_value = [
            _review("old", datetime(2026, 8, 14, tzinfo=timezone.utc)),
            _review("new", datetime(2026, 8, 15, tzinfo=timezone.utc), deeper_ai_review_needed=True, reason="risk_breach"),
        ]

        with patch("builtins.print") as mock_print:
            result = run_manual_demo_daily_ai_reviews(symbol="NVDA", storage=storage)

        self.assertEqual(["new", "old"], [review.demo_daily_ai_review_id for review in result["reviews"]])
        mock_print.assert_any_call("Daily Reviews Loaded : 2")
        mock_print.assert_any_call("Daily Reviews Displayed : 2")
        mock_print.assert_any_call("deeper_ai_review_needed_count=1")
        mock_print.assert_any_call("latest_reason=risk_breach")
        self.assertEqual(["load_demo_daily_ai_reviews"], [call[0] for call in storage.method_calls])

    def test_handles_no_reviews_and_is_read_only(self):
        storage = Mock()
        storage.load_demo_daily_ai_reviews.return_value = []
        with patch("urllib.request.urlopen") as mock_urlopen, patch("builtins.print") as mock_print:
            result = run_manual_demo_daily_ai_reviews(symbol="NVDA", storage=storage)

        mock_urlopen.assert_not_called()
        self.assertEqual(0, result["reviews_loaded"])
        self.assertEqual(0, result["reviews_displayed"])
        mock_print.assert_any_call("AI Calls Made : 0")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("No stored daily AI reviews are available.")


if __name__ == "__main__":
    unittest.main()