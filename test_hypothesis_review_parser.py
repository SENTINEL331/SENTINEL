import json
import unittest
from datetime import datetime, timezone

from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation
from research.parser import parse_hypothesis_reviews


class HypothesisReviewParserTests(unittest.TestCase):
    def test_parser_returns_hypothesis_review_objects(self):
        created_at = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc).isoformat()

        response = json.dumps(
            {
                "hypothesis_reviews": [
                    {
                        "review_id": "hyprev-001",
                        "hypothesis_id": "hyp-001",
                        "symbol": "NVDA",
                        "recommendation": "keep",
                        "rationale": "Completed experiments show stable positive outcomes.",
                        "confidence": 0.72,
                        "created_at": created_at,
                    }
                ]
            }
        )

        reviews = parse_hypothesis_reviews("NVDA", response)

        self.assertEqual(1, len(reviews))
        self.assertIsInstance(reviews[0], HypothesisReview)
        self.assertEqual("hyprev-001", reviews[0].review_id)
        self.assertEqual("hyp-001", reviews[0].hypothesis_id)
        self.assertEqual("NVDA", reviews[0].symbol)
        self.assertEqual(HypothesisReviewRecommendation.KEEP, reviews[0].recommendation)
        self.assertEqual(0.72, reviews[0].confidence)
        self.assertEqual(created_at, reviews[0].created_at.isoformat())

    def test_parser_rejects_malformed_input(self):
        with self.assertRaisesRegex(
            ValueError,
            "hypothesis_reviews\\[0\\]\\.recommendation is required",
        ):
            parse_hypothesis_reviews(
                "NVDA",
                {
                    "hypothesis_reviews": [
                        {
                            "review_id": "hyprev-001",
                            "hypothesis_id": "hyp-001",
                            "symbol": "NVDA",
                            "rationale": "Needs recommendation.",
                            "confidence": 0.5,
                        }
                    ]
                },
            )

        with self.assertRaisesRegex(ValueError, "hypothesis review response must be valid JSON"):
            parse_hypothesis_reviews("NVDA", "not-json")

    def test_parser_assigns_current_utc_timestamp_when_created_at_is_missing_or_date_only(self):
        before = datetime.now(timezone.utc)

        reviews = parse_hypothesis_reviews(
            "NVDA",
            {
                "hypothesis_reviews": [
                    {
                        "review_id": "hyprev-missing-created",
                        "hypothesis_id": "hyp-001",
                        "symbol": "NVDA",
                        "recommendation": "keep",
                        "rationale": "Missing created_at should use current UTC time.",
                        "confidence": 0.6,
                    },
                    {
                        "review_id": "hyprev-date-only-created",
                        "hypothesis_id": "hyp-002",
                        "symbol": "NVDA",
                        "recommendation": "needs_more_tests",
                        "rationale": "Date-only created_at should not coerce to midnight.",
                        "confidence": 0.5,
                        "created_at": "2026-08-04",
                    },
                ]
            },
        )

        after = datetime.now(timezone.utc)

        self.assertEqual(2, len(reviews))
        self.assertIsNotNone(reviews[0].created_at.tzinfo)
        self.assertIsNotNone(reviews[1].created_at.tzinfo)
        self.assertGreaterEqual(reviews[0].created_at, before)
        self.assertLessEqual(reviews[0].created_at, after)
        self.assertGreaterEqual(reviews[1].created_at, before)
        self.assertLessEqual(reviews[1].created_at, after)


if __name__ == "__main__":
    unittest.main()
