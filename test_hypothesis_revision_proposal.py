import unittest
from datetime import datetime, timezone

from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_revision_proposal import HypothesisRevisionProposal
from research.hypothesis_revision_proposal import HypothesisRevisionProposalType


class HypothesisRevisionProposalTests(unittest.TestCase):
    def test_construction_exposes_fields(self):
        created_at = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)

        proposal = HypothesisRevisionProposal(
            proposal_id="hyprevp-001",
            symbol="NVDA",
            parent_hypothesis_id="hyp-001",
            source_review_id="hyprev-001",
            lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
            proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
            proposed_title="Narrowed momentum continuation",
            proposed_description="Refine setup to include trend-strength filter.",
            rationale="Repeated zero-trade outcomes suggest narrower trigger definition.",
            confidence=0.72,
            created_at=created_at,
        )

        self.assertEqual("hyprevp-001", proposal.proposal_id)
        self.assertEqual("hyprevp-001", proposal.id)
        self.assertEqual("NVDA", proposal.symbol)
        self.assertEqual("hyp-001", proposal.parent_hypothesis_id)
        self.assertEqual("hyprev-001", proposal.source_review_id)
        self.assertEqual(HypothesisLifecycleAction.REFINE_CANDIDATE, proposal.lifecycle_action)
        self.assertEqual(
            HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
            proposal.proposal_type,
        )
        self.assertEqual("Narrowed momentum continuation", proposal.proposed_title)
        self.assertEqual(0.72, proposal.confidence)
        self.assertEqual(created_at, proposal.created_at)

    def test_rejects_invalid_confidence_and_requires_child_fields_for_child_type(self):
        created_at = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)

        with self.assertRaisesRegex(ValueError, "confidence must be between 0.0 and 1.0"):
            HypothesisRevisionProposal(
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                source_review_id=None,
                lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
                proposal_type=HypothesisRevisionProposalType.REQUEST_MORE_TESTS,
                proposed_title="",
                proposed_description="",
                rationale="Need additional evidence.",
                confidence=1.2,
                created_at=created_at,
            )

        with self.assertRaisesRegex(ValueError, "proposed_title is required"):
            HypothesisRevisionProposal(
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                source_review_id=None,
                lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
                proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
                proposed_title="",
                proposed_description="refined description",
                rationale="Need refined child.",
                confidence=0.5,
                created_at=created_at,
            )

        with self.assertRaisesRegex(ValueError, "created_at must be timezone-aware"):
            HypothesisRevisionProposal(
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                source_review_id=None,
                lifecycle_action=HypothesisLifecycleAction.NO_ACTION,
                proposal_type=HypothesisRevisionProposalType.NO_REVISION,
                proposed_title="",
                proposed_description="",
                rationale="No revision required.",
                confidence=0.5,
                created_at=datetime(2026, 8, 4, 0, 0),
            )


if __name__ == "__main__":
    unittest.main()
