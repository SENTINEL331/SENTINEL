import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation
from research.runner import DEFAULT_SYMBOL, run_manual_hypothesis_reviews


class ManualHypothesisReviewRunnerTests(unittest.TestCase):
    def test_runner_generates_and_prints_hypothesis_reviews(self):
        service = Mock()

        review = HypothesisReview(
            review_id="hyprev-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            recommendation=HypothesisReviewRecommendation.REFINE,
            rationale="Improve entry filter consistency across regimes.",
            confidence=0.67,
            created_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
        )
        service.generate_for_symbol.return_value = [review]

        with patch("builtins.print") as mock_print:
            reviews = run_manual_hypothesis_reviews(
                symbol="NVDA",
                storage=Mock(),
                hypothesis_review_service=service,
            )

        self.assertEqual([review], reviews)
        service.generate_for_symbol.assert_called_once_with(symbol="NVDA")

        mock_print.assert_any_call("Manual Hypothesis Reviews: NVDA")
        mock_print.assert_any_call("Hypothesis Reviews Generated : 1")
        mock_print.assert_any_call(
            "- hyp-001 recommendation=refine confidence=0.67 id=hyprev-001"
        )
        mock_print.assert_any_call("  rationale: Improve entry filter consistency across regimes.")

    def test_runner_handles_no_reviews(self):
        service = Mock()
        service.generate_for_symbol.return_value = []

        with patch("builtins.print") as mock_print:
            reviews = run_manual_hypothesis_reviews(
                symbol=DEFAULT_SYMBOL,
                storage=Mock(),
                hypothesis_review_service=service,
            )

        self.assertEqual([], reviews)
        service.generate_for_symbol.assert_called_once_with(symbol=DEFAULT_SYMBOL)
        mock_print.assert_any_call(f"Manual Hypothesis Reviews: {DEFAULT_SYMBOL}")
        mock_print.assert_any_call("Hypothesis Reviews Generated : 0")
        mock_print.assert_any_call("No hypothesis reviews generated.")


if __name__ == "__main__":
    unittest.main()
