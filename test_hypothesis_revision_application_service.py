import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ai.hypothesis_revision_application_service import HypothesisRevisionApplicationService
from ai.storage import Storage
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_revision_application import HypothesisRevisionApplicationStatus
from research.hypothesis_revision_proposal import HypothesisRevisionProposal
from research.hypothesis_revision_proposal import HypothesisRevisionProposalType


class HypothesisRevisionApplicationServiceTests(unittest.TestCase):
    def test_dry_run_does_not_create_child_hypothesis(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            parent = Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Parent",
                description="Parent hypothesis.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.6,
            )
            proposal = HypothesisRevisionProposal(
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                source_review_id="hyprev-001",
                lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
                proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
                proposed_title="Child",
                proposed_description="Child hypothesis.",
                rationale="Refine setup.",
                confidence=0.7,
                created_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
            )

            storage.save_hypotheses("NVDA", [parent])
            storage.save_hypothesis_revision_proposals("NVDA", [proposal])

            service = HypothesisRevisionApplicationService(storage=storage)
            application = service.apply_proposal(
                symbol="NVDA",
                proposal_id="hyprevp-001",
                apply_mode=False,
            )

            loaded_hypotheses = storage.load_hypotheses("NVDA")
            loaded_applications = storage.load_hypothesis_revision_applications("NVDA")

            self.assertEqual(HypothesisRevisionApplicationStatus.DRY_RUN, application.status)
            self.assertEqual(1, len(loaded_hypotheses))
            self.assertEqual(1, len(loaded_applications))
            self.assertEqual(HypothesisRevisionApplicationStatus.DRY_RUN, loaded_applications[0].status)

    def test_apply_creates_child_once_and_duplicate_apply_is_skipped(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            parent = Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Parent",
                description="Parent hypothesis.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.61,
                created_at=datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc),
            )
            proposal = HypothesisRevisionProposal(
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                source_review_id="hyprev-001",
                lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
                proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
                proposed_title="Child",
                proposed_description="Child hypothesis.",
                rationale="Refine setup.",
                confidence=0.72,
                created_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
            )

            storage.save_hypotheses("NVDA", [parent])
            storage.save_hypothesis_revision_proposals("NVDA", [proposal])

            service = HypothesisRevisionApplicationService(storage=storage)

            first_application = service.apply_proposal(
                symbol="NVDA",
                proposal_id="hyprevp-001",
                apply_mode=True,
            )
            second_application = service.apply_proposal(
                symbol="NVDA",
                proposal_id="hyprevp-001",
                apply_mode=True,
            )

            loaded_hypotheses = storage.load_hypotheses("NVDA")
            children = [
                hypothesis
                for hypothesis in loaded_hypotheses
                if hypothesis.source_revision_proposal_id == "hyprevp-001"
            ]
            loaded_applications = storage.load_hypothesis_revision_applications("NVDA")
            reloaded_parent = [
                hypothesis for hypothesis in loaded_hypotheses if hypothesis.hypothesis_id == "hyp-001"
            ][0]

            self.assertEqual(HypothesisRevisionApplicationStatus.APPLIED, first_application.status)
            self.assertEqual(HypothesisRevisionApplicationStatus.SKIPPED_DUPLICATE, second_application.status)
            self.assertEqual(1, len(children))
            self.assertEqual("hyp-001", children[0].parent_hypothesis_id)
            self.assertEqual(("hyp-001",), children[0].lineage_hypothesis_ids)
            self.assertEqual("hyprevp-001", children[0].source_revision_proposal_id)
            self.assertEqual(2, len(loaded_applications))

            # Parent record is preserved (append-only child creation only).
            self.assertEqual("Parent", reloaded_parent.title)
            self.assertEqual("Parent hypothesis.", reloaded_parent.description)
            self.assertEqual(0.61, reloaded_parent.confidence)
            self.assertEqual(HypothesisStatus.ACTIVE, reloaded_parent.status)

    def test_missing_proposal_is_rejected(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            service = HypothesisRevisionApplicationService(storage=storage)
            application = service.apply_proposal(
                symbol="NVDA",
                proposal_id="does-not-exist",
                apply_mode=True,
            )

            self.assertEqual(HypothesisRevisionApplicationStatus.REJECTED, application.status)
            self.assertIn("proposal not found", application.message)

    def test_non_child_proposal_type_is_rejected(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            parent = Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Parent",
                description="Parent hypothesis.",
            )
            proposal = HypothesisRevisionProposal(
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                source_review_id=None,
                lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
                proposal_type=HypothesisRevisionProposalType.REQUEST_MORE_TESTS,
                proposed_title="",
                proposed_description="",
                rationale="Need more tests.",
                confidence=0.5,
                created_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
            )

            storage.save_hypotheses("NVDA", [parent])
            storage.save_hypothesis_revision_proposals("NVDA", [proposal])

            service = HypothesisRevisionApplicationService(storage=storage)
            application = service.apply_proposal(
                symbol="NVDA",
                proposal_id="hyprevp-001",
                apply_mode=True,
            )

            loaded_hypotheses = storage.load_hypotheses("NVDA")

            self.assertEqual(HypothesisRevisionApplicationStatus.REJECTED, application.status)
            self.assertIn("unsupported proposal_type", application.message)
            self.assertEqual(1, len(loaded_hypotheses))

    def test_symbol_mismatch_is_rejected(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            parent = Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Parent",
                description="Parent hypothesis.",
            )
            # Stored under NVDA, but payload symbol mismatches requested symbol.
            proposal = HypothesisRevisionProposal(
                proposal_id="hyprevp-001",
                symbol="AAPL",
                parent_hypothesis_id="hyp-001",
                source_review_id=None,
                lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
                proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
                proposed_title="Child",
                proposed_description="Child hypothesis.",
                rationale="Refine setup.",
                confidence=0.6,
                created_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
            )

            storage.save_hypotheses("NVDA", [parent])
            storage.save_hypothesis_revision_proposals("NVDA", [proposal])

            service = HypothesisRevisionApplicationService(storage=storage)
            application = service.apply_proposal(
                symbol="NVDA",
                proposal_id="hyprevp-001",
                apply_mode=True,
            )

            self.assertEqual(HypothesisRevisionApplicationStatus.REJECTED, application.status)
            self.assertIn("symbol mismatch", application.message)


if __name__ == "__main__":
    unittest.main()
