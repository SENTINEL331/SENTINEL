import unittest
from datetime import datetime, timezone

from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation


class HypothesisReviewTests(unittest.TestCase):
    def test_construction_exposes_fields(self):
        created_at = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)

        review = HypothesisReview(
            review_id="hyprev-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            recommendation=HypothesisReviewRecommendation.KEEP,
            rationale="Completed experiments show stable positive edge.",
            confidence=0.78,
            created_at=created_at,
        )

        self.assertEqual("hyprev-001", review.review_id)
        self.assertEqual("hyprev-001", review.id)
        self.assertEqual("hyp-001", review.hypothesis_id)
        self.assertEqual("NVDA", review.symbol)
        self.assertEqual(HypothesisReviewRecommendation.KEEP, review.recommendation)
        self.assertEqual(0.78, review.confidence)
        self.assertEqual(created_at, review.created_at)

    def test_rejects_invalid_confidence_and_naive_timestamp(self):
        created_at = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)

        with self.assertRaisesRegex(ValueError, "confidence must be between 0.0 and 1.0"):
            HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.KEEP,
                rationale="Rationale",
                confidence=1.2,
                created_at=created_at,
            )

        with self.assertRaisesRegex(ValueError, "created_at must be timezone-aware"):
            HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.KEEP,
                rationale="Rationale",
                confidence=0.5,
                created_at=datetime(2026, 8, 4, 0, 0),
            )


if __name__ == "__main__":
    unittest.main()
