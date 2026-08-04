import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ai.storage import Storage
from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation


class HypothesisReviewStorageTests(unittest.TestCase):
    def test_save_and_load_hypothesis_reviews_for_symbol(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            created_at = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)
            review = HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.REFINE,
                rationale="Edge exists but setup definition is too broad.",
                confidence=0.64,
                created_at=created_at,
            )

            storage.save_hypothesis_reviews("NVDA", [review])

            loaded = storage.load_hypothesis_reviews("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertIsInstance(loaded[0], HypothesisReview)
            self.assertEqual("hyprev-001", loaded[0].review_id)
            self.assertEqual("hyp-001", loaded[0].hypothesis_id)
            self.assertEqual(HypothesisReviewRecommendation.REFINE, loaded[0].recommendation)
            self.assertEqual(0.64, loaded[0].confidence)
            self.assertEqual(created_at, loaded[0].created_at)

            reviews_file = Path(tmp_dir) / "hypotheses" / "reviews" / "NVDA.json"
            self.assertTrue(reviews_file.exists())

    def test_save_hypothesis_reviews_is_append_only_by_identity(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            created_at = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)

            first = HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.KEEP,
                rationale="Keep as-is.",
                confidence=0.7,
                created_at=created_at,
            )

            duplicate = HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.RETIRE,
                rationale="Duplicate should be ignored.",
                confidence=0.2,
                created_at=created_at,
            )

            storage.save_hypothesis_reviews("NVDA", [first])
            storage.save_hypothesis_reviews("NVDA", [duplicate])

            loaded = storage.load_hypothesis_reviews("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertEqual(HypothesisReviewRecommendation.KEEP, loaded[0].recommendation)


if __name__ == "__main__":
    unittest.main()
