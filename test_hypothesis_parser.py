import json
import unittest
from datetime import datetime, timezone

from research.hypothesis import Hypothesis, HypothesisStatus
from research.parser import parse_hypotheses


class HypothesisParserTests(unittest.TestCase):
    def test_parser_returns_hypothesis_objects(self):
        created_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc).isoformat()
        updated_at = datetime(2026, 8, 3, 0, 15, tzinfo=timezone.utc).isoformat()

        response = json.dumps(
            {
                "hypotheses": [
                    {
                        "hypothesis_id": "hyp-001",
                        "symbol": "NVDA",
                        "title": "Momentum continuation",
                        "description": "Price strength may continue after an earnings-driven breakout.",
                        "status": "active",
                        "confidence": 0.75,
                        "source_observation_ids": ["obs-1", "obs-2"],
                        "parent_hypothesis_id": "hyp-root",
                        "lineage_hypothesis_ids": ["hyp-root", "hyp-parent"],
                        "experiment_refs": ["exp-1", "exp-2"],
                        "created_at": created_at,
                        "updated_at": updated_at,
                    }
                ]
            }
        )

        hypotheses = parse_hypotheses("NVDA", response)

        self.assertEqual(1, len(hypotheses))
        self.assertIsInstance(hypotheses[0], Hypothesis)
        self.assertEqual("hyp-001", hypotheses[0].hypothesis_id)
        self.assertEqual("NVDA", hypotheses[0].symbol)
        self.assertEqual("Momentum continuation", hypotheses[0].title)
        self.assertEqual(
            "Price strength may continue after an earnings-driven breakout.",
            hypotheses[0].description,
        )
        self.assertEqual(HypothesisStatus.ACTIVE, hypotheses[0].status)
        self.assertEqual(0.75, hypotheses[0].confidence)
        self.assertEqual(("obs-1", "obs-2"), hypotheses[0].source_observation_ids)
        self.assertEqual("hyp-root", hypotheses[0].parent_hypothesis_id)
        self.assertEqual(("hyp-root", "hyp-parent"), hypotheses[0].lineage_hypothesis_ids)
        self.assertEqual(("exp-1", "exp-2"), hypotheses[0].experiment_refs)
        self.assertEqual(created_at, hypotheses[0].created)
        self.assertEqual(updated_at, hypotheses[0].updated)

    def test_parser_rejects_malformed_input(self):
        with self.assertRaisesRegex(ValueError, "hypotheses\\[0\\]\\.title is required"):
            parse_hypotheses(
                "NVDA",
                {
                    "hypotheses": [
                        {
                            "hypothesis_id": "hyp-001",
                            "symbol": "NVDA",
                            "description": "Missing title should fail.",
                            "created_at": "2026-08-03T00:00:00+00:00",
                            "updated_at": "2026-08-03T00:00:00+00:00",
                        }
                    ]
                },
            )

        with self.assertRaisesRegex(ValueError, "hypothesis response must be valid JSON"):
            parse_hypotheses("NVDA", "not-json")


if __name__ == "__main__":
    unittest.main()