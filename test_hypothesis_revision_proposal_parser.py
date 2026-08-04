import json
import unittest
from datetime import datetime, timezone

from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_revision_proposal import HypothesisRevisionProposal
from research.hypothesis_revision_proposal import HypothesisRevisionProposalType
from research.parser import parse_hypothesis_revision_proposals


class HypothesisRevisionProposalParserTests(unittest.TestCase):
    def test_parser_returns_hypothesis_revision_proposal_objects(self):
        created_at = datetime(2026, 8, 4, 1, 30, tzinfo=timezone.utc).isoformat()

        response = json.dumps(
            {
                "hypothesis_revision_proposals": [
                    {
                        "proposal_id": "hyprevp-001",
                        "symbol": "NVDA",
                        "parent_hypothesis_id": "hyp-001",
                        "source_review_id": "hyprev-001",
                        "lifecycle_action": "refine_candidate",
                        "proposal_type": "create_child_hypothesis",
                        "proposed_title": "Refined trend hypothesis",
                        "proposed_description": "Refine with volatility filter.",
                        "rationale": "Repeated no-trade outcomes suggest tighter setup.",
                        "confidence": 0.66,
                        "created_at": created_at,
                    }
                ]
            }
        )

        proposals = parse_hypothesis_revision_proposals("NVDA", response)

        self.assertEqual(1, len(proposals))
        self.assertIsInstance(proposals[0], HypothesisRevisionProposal)
        self.assertEqual("hyprevp-001", proposals[0].proposal_id)
        self.assertEqual(HypothesisLifecycleAction.REFINE_CANDIDATE, proposals[0].lifecycle_action)
        self.assertEqual(
            HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
            proposals[0].proposal_type,
        )
        self.assertEqual(created_at, proposals[0].created_at.isoformat())

    def test_parser_rejects_malformed_input(self):
        with self.assertRaisesRegex(
            ValueError,
            "hypothesis_revision_proposals\\[0\\]\\.proposal_type is required",
        ):
            parse_hypothesis_revision_proposals(
                "NVDA",
                {
                    "hypothesis_revision_proposals": [
                        {
                            "proposal_id": "hyprevp-001",
                            "parent_hypothesis_id": "hyp-001",
                            "lifecycle_action": "refine_candidate",
                            "rationale": "Need refined child.",
                            "confidence": 0.5,
                        }
                    ]
                },
            )

        with self.assertRaisesRegex(
            ValueError,
            "hypothesis revision proposal response must be valid JSON",
        ):
            parse_hypothesis_revision_proposals("NVDA", "not-json")


if __name__ == "__main__":
    unittest.main()
