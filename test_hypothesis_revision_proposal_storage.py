import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ai.storage import Storage
from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_revision_proposal import HypothesisRevisionProposal
from research.hypothesis_revision_proposal import HypothesisRevisionProposalType


class HypothesisRevisionProposalStorageTests(unittest.TestCase):
    def test_save_and_load_hypothesis_revision_proposals_for_symbol(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            created_at = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)
            proposal = HypothesisRevisionProposal(
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                source_review_id="hyprev-001",
                lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
                proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
                proposed_title="Refined title",
                proposed_description="Refined description",
                rationale="Need narrower setup definition.",
                confidence=0.63,
                created_at=created_at,
            )

            storage.save_hypothesis_revision_proposals("NVDA", [proposal])

            loaded = storage.load_hypothesis_revision_proposals("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertIsInstance(loaded[0], HypothesisRevisionProposal)
            self.assertEqual("hyprevp-001", loaded[0].proposal_id)
            self.assertEqual(HypothesisLifecycleAction.REFINE_CANDIDATE, loaded[0].lifecycle_action)
            self.assertEqual(
                HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
                loaded[0].proposal_type,
            )
            self.assertEqual(0.63, loaded[0].confidence)
            self.assertEqual(created_at, loaded[0].created_at)

            proposals_file = Path(tmp_dir) / "hypotheses" / "revision_proposals" / "NVDA.json"
            self.assertTrue(proposals_file.exists())

    def test_save_hypothesis_revision_proposals_is_append_only_by_identity(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            created_at = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)

            first = HypothesisRevisionProposal(
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                source_review_id=None,
                lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
                proposal_type=HypothesisRevisionProposalType.REQUEST_MORE_TESTS,
                proposed_title="",
                proposed_description="",
                rationale="Need more tests first.",
                confidence=0.55,
                created_at=created_at,
            )

            duplicate = HypothesisRevisionProposal(
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                source_review_id=None,
                lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
                proposal_type=HypothesisRevisionProposalType.NO_REVISION,
                proposed_title="",
                proposed_description="",
                rationale="Duplicate should be ignored.",
                confidence=0.20,
                created_at=created_at,
            )

            storage.save_hypothesis_revision_proposals("NVDA", [first])
            storage.save_hypothesis_revision_proposals("NVDA", [duplicate])

            loaded = storage.load_hypothesis_revision_proposals("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertEqual(
                HypothesisRevisionProposalType.REQUEST_MORE_TESTS,
                loaded[0].proposal_type,
            )


if __name__ == "__main__":
    unittest.main()
