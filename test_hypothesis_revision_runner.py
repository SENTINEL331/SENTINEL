import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_revision_proposal import HypothesisRevisionProposal
from research.hypothesis_revision_proposal import HypothesisRevisionProposalType
from research.runner import DEFAULT_SYMBOL, run_manual_hypothesis_revisions


class ManualHypothesisRevisionRunnerTests(unittest.TestCase):
    def test_runner_generates_and_prints_hypothesis_revision_proposals(self):
        service = Mock()

        proposal = HypothesisRevisionProposal(
            proposal_id="hyprevp-001",
            symbol="NVDA",
            parent_hypothesis_id="hyp-001",
            source_review_id="hyprev-001",
            lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
            proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
            proposed_title="Refined momentum setup",
            proposed_description="Add trend-strength filter to reduce false positives.",
            rationale="Repeated zero-trade outcomes justify narrower trigger.",
            confidence=0.73,
            created_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
        )
        service.generate_for_symbol.return_value = [proposal]

        with patch("builtins.print") as mock_print:
            proposals = run_manual_hypothesis_revisions(
                symbol="NVDA",
                storage=Mock(),
                hypothesis_revision_service=service,
            )

        self.assertEqual([proposal], proposals)
        service.generate_for_symbol.assert_called_once_with(symbol="NVDA")

        mock_print.assert_any_call("Manual Hypothesis Revisions: NVDA")
        mock_print.assert_any_call("Proposals only; no hypotheses are mutated.")
        mock_print.assert_any_call("Hypothesis Revision Proposals Generated : 1")
        mock_print.assert_any_call(
            "- parent_id=hyp-001 proposal_type=create_child_hypothesis lifecycle_action=refine_candidate confidence=0.73 id=hyprevp-001"
        )
        mock_print.assert_any_call("  source_review_id: hyprev-001")

    def test_runner_handles_no_revision_proposals(self):
        service = Mock()
        service.generate_for_symbol.return_value = []

        with patch("builtins.print") as mock_print:
            proposals = run_manual_hypothesis_revisions(
                symbol=DEFAULT_SYMBOL,
                storage=Mock(),
                hypothesis_revision_service=service,
            )

        self.assertEqual([], proposals)
        service.generate_for_symbol.assert_called_once_with(symbol=DEFAULT_SYMBOL)
        mock_print.assert_any_call(f"Manual Hypothesis Revisions: {DEFAULT_SYMBOL}")
        mock_print.assert_any_call("Hypothesis Revision Proposals Generated : 0")
        mock_print.assert_any_call("No hypothesis revision proposals generated.")


if __name__ == "__main__":
    unittest.main()
