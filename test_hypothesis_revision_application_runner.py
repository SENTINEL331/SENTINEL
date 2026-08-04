import unittest
from unittest.mock import Mock, patch

from research.hypothesis_revision_application import HypothesisRevisionApplication
from research.hypothesis_revision_application import HypothesisRevisionApplicationStatus
from research.runner import run_manual_hypothesis_revision_apply


class ManualHypothesisRevisionApplyRunnerTests(unittest.TestCase):
    def test_runner_prints_dry_run_application_result(self):
        service = Mock()
        service.apply_proposal.return_value = HypothesisRevisionApplication(
            application_id="hypreva-001",
            proposal_id="hyprevp-001",
            symbol="NVDA",
            parent_hypothesis_id="hyp-001",
            status=HypothesisRevisionApplicationStatus.DRY_RUN,
            apply_mode=False,
            child_hypothesis_id="hyp-002",
            message="dry run preview",
        )

        with patch("builtins.print") as mock_print:
            application = run_manual_hypothesis_revision_apply(
                symbol="NVDA",
                proposal_id="hyprevp-001",
                apply_changes=False,
                storage=Mock(),
                hypothesis_revision_application_service=service,
            )

        self.assertEqual(HypothesisRevisionApplicationStatus.DRY_RUN, application.status)
        service.apply_proposal.assert_called_once_with(
            symbol="NVDA",
            proposal_id="hyprevp-001",
            apply_mode=False,
        )
        mock_print.assert_any_call("Manual Hypothesis Revision Apply: NVDA")
        mock_print.assert_any_call("Mode : dry-run")
        mock_print.assert_any_call("Application Status : dry_run")

    def test_runner_prints_apply_application_result(self):
        service = Mock()
        service.apply_proposal.return_value = HypothesisRevisionApplication(
            application_id="hypreva-002",
            proposal_id="hyprevp-001",
            symbol="NVDA",
            parent_hypothesis_id="hyp-001",
            status=HypothesisRevisionApplicationStatus.APPLIED,
            apply_mode=True,
            child_hypothesis_id="hyp-002",
            message="proposal applied",
        )

        with patch("builtins.print") as mock_print:
            application = run_manual_hypothesis_revision_apply(
                symbol="NVDA",
                proposal_id="hyprevp-001",
                apply_changes=True,
                storage=Mock(),
                hypothesis_revision_application_service=service,
            )

        self.assertEqual(HypothesisRevisionApplicationStatus.APPLIED, application.status)
        service.apply_proposal.assert_called_once_with(
            symbol="NVDA",
            proposal_id="hyprevp-001",
            apply_mode=True,
        )
        mock_print.assert_any_call("Mode : apply")
        mock_print.assert_any_call("Application Status : applied")


if __name__ == "__main__":
    unittest.main()
