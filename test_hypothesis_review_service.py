import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from ai.hypothesis_review_service import HypothesisReviewService
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation


class HypothesisReviewServiceTests(unittest.TestCase):
    def test_generate_for_symbol_calls_ai_parses_and_saves(self):
        ai_client = Mock()
        storage = Mock()
        journal_builder = Mock()

        journal_builder.build.return_value = "Journal with deterministic hypothesis evidence."
        ai_client.hypothesis_review.return_value = """
        {
            "hypothesis_reviews": [
                {
                    "review_id": "hyprev-001",
                    "hypothesis_id": "hyp-001",
                    "symbol": "NVDA",
                    "recommendation": "keep",
                    "rationale": "Evidence remains positive and stable.",
                    "confidence": 0.76,
                    "created_at": "2026-08-04T00:00:00+00:00"
                }
            ]
        }
        """

        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Momentum continuation",
            description="Test whether momentum persists.",
            status=HypothesisStatus.ACTIVE,
            confidence=0.68,
        )
        storage.load_hypotheses.return_value = [hypothesis]

        service = HypothesisReviewService(
            ai_client=ai_client,
            storage=storage,
            journal_builder=journal_builder,
        )

        reviews = service.generate_for_symbol(symbol="NVDA")

        self.assertEqual(1, len(reviews))
        self.assertIsInstance(reviews[0], HypothesisReview)
        self.assertEqual("hyprev-001", reviews[0].review_id)
        self.assertEqual(HypothesisReviewRecommendation.KEEP, reviews[0].recommendation)
        self.assertEqual(0.76, reviews[0].confidence)
        self.assertEqual(datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc), reviews[0].created_at)

        storage.load_hypotheses.assert_called_once_with("NVDA")
        journal_builder.build.assert_called_once_with("NVDA")
        ai_client.hypothesis_review.assert_called_once()
        storage.save_hypothesis_reviews.assert_called_once_with("NVDA", reviews)

        call_kwargs = ai_client.hypothesis_review.call_args.kwargs
        self.assertEqual("NVDA", call_kwargs["symbol"])
        self.assertEqual("Journal with deterministic hypothesis evidence.", call_kwargs["journal"])
        self.assertIn("hyp-001", call_kwargs["hypotheses"])
        self.assertIn("Momentum continuation", call_kwargs["hypotheses"])

    def test_generate_for_symbol_rejects_invalid_hypothesis_inputs(self):
        service = HypothesisReviewService(
            ai_client=Mock(),
            storage=Mock(),
            journal_builder=Mock(),
        )

        with self.assertRaisesRegex(
            ValueError,
            "hypotheses must be a JSON string, dicts, or Hypothesis objects",
        ):
            service.generate_for_symbol(
                symbol="NVDA",
                journal="Journal context.",
                hypotheses=[123],
            )


if __name__ == "__main__":
    unittest.main()
