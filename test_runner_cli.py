import unittest
from unittest.mock import patch

from research.runner import DEFAULT_SYMBOL, main


class RunnerCliTests(unittest.TestCase):
    def test_help_does_not_dispatch_generation(self):
        with patch("research.runner.run_manual_hypothesis_generation") as mock_hypotheses, patch(
            "research.runner.run_manual_experiment_request_generation"
        ) as mock_experiment_requests, patch(
            "research.runner.run_manual_experiment_execution"
        ) as mock_experiment_execution, patch(
            "research.runner.run_manual_hypothesis_evaluation"
        ) as mock_hypothesis_evaluation, patch(
            "research.runner.run_manual_hypothesis_reviews"
        ) as mock_hypothesis_reviews, patch(
            "research.runner.run_manual_hypothesis_lifecycle"
        ) as mock_hypothesis_lifecycle, patch(
            "research.runner.run_manual_hypothesis_revisions"
        ) as mock_hypothesis_revisions, patch(
            "research.runner.run_manual_research_plan"
        ) as mock_research_plan:
            with self.assertRaises(SystemExit) as context:
                main(["--help"])

        self.assertEqual(0, context.exception.code)
        mock_hypotheses.assert_not_called()
        mock_experiment_requests.assert_not_called()
        mock_experiment_execution.assert_not_called()
        mock_hypothesis_evaluation.assert_not_called()
        mock_hypothesis_reviews.assert_not_called()
        mock_hypothesis_lifecycle.assert_not_called()
        mock_hypothesis_revisions.assert_not_called()
        mock_research_plan.assert_not_called()

    def test_hypotheses_command_dispatches_to_hypothesis_runner(self):
        with patch("research.runner.run_manual_hypothesis_generation") as mock_hypotheses, patch(
            "research.runner.run_manual_experiment_request_generation"
        ) as mock_experiment_requests:
            exit_code = main(["hypotheses", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_hypotheses.assert_called_once_with(symbol="NVDA")
        mock_experiment_requests.assert_not_called()

    def test_experiment_requests_command_dispatches_to_experiment_runner(self):
        with patch("research.runner.run_manual_hypothesis_generation") as mock_hypotheses, patch(
            "research.runner.run_manual_experiment_request_generation"
        ) as mock_experiment_requests:
            exit_code = main(["experiment-requests", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_experiment_requests.assert_called_once_with(symbol="NVDA", planned_only=False)
        mock_hypotheses.assert_not_called()

    def test_experiment_requests_command_with_planned_only_sets_flag(self):
        with patch("research.runner.run_manual_experiment_request_generation") as mock_experiment_requests:
            exit_code = main(["experiment-requests", "NVDA", "--planned-only"])

        self.assertEqual(0, exit_code)
        mock_experiment_requests.assert_called_once_with(symbol="NVDA", planned_only=True)

    def test_experiment_execution_command_dispatches_to_execution_runner(self):
        with patch("research.runner.run_manual_hypothesis_generation") as mock_hypotheses, patch(
            "research.runner.run_manual_experiment_request_generation"
        ) as mock_experiment_requests, patch(
            "research.runner.run_manual_experiment_execution"
        ) as mock_experiment_execution:
            exit_code = main(["experiment-execution", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_experiment_execution.assert_called_once_with(symbol="NVDA")
        mock_hypotheses.assert_not_called()
        mock_experiment_requests.assert_not_called()

    def test_empty_argv_shows_help_without_dispatch(self):
        with patch("research.runner.run_manual_hypothesis_generation") as mock_hypotheses, patch(
            "research.runner.run_manual_experiment_request_generation"
        ) as mock_experiment_requests, patch(
            "research.runner.run_manual_experiment_execution"
        ) as mock_experiment_execution, patch(
            "research.runner.run_manual_hypothesis_evaluation"
        ) as mock_hypothesis_evaluation, patch(
            "research.runner.run_manual_hypothesis_reviews"
        ) as mock_hypothesis_reviews, patch(
            "research.runner.run_manual_hypothesis_lifecycle"
        ) as mock_hypothesis_lifecycle, patch(
            "research.runner.run_manual_hypothesis_revisions"
        ) as mock_hypothesis_revisions, patch(
            "research.runner.run_manual_research_plan"
        ) as mock_research_plan, patch("argparse.ArgumentParser.print_help") as mock_help:
            exit_code = main([])

        self.assertEqual(0, exit_code)
        mock_help.assert_called_once()
        mock_hypotheses.assert_not_called()
        mock_experiment_requests.assert_not_called()
        mock_experiment_execution.assert_not_called()
        mock_hypothesis_evaluation.assert_not_called()
        mock_hypothesis_reviews.assert_not_called()
        mock_hypothesis_lifecycle.assert_not_called()
        mock_hypothesis_revisions.assert_not_called()
        mock_research_plan.assert_not_called()

    def test_hypotheses_command_uses_default_symbol(self):
        with patch("research.runner.run_manual_hypothesis_generation") as mock_hypotheses:
            exit_code = main(["hypotheses"])

        self.assertEqual(0, exit_code)
        mock_hypotheses.assert_called_once_with(symbol=DEFAULT_SYMBOL)

    def test_experiment_requests_command_uses_default_symbol(self):
        with patch("research.runner.run_manual_experiment_request_generation") as mock_experiment_requests:
            exit_code = main(["experiment-requests"])

        self.assertEqual(0, exit_code)
        mock_experiment_requests.assert_called_once_with(symbol=DEFAULT_SYMBOL, planned_only=False)

    def test_experiment_execution_command_uses_default_symbol(self):
        with patch("research.runner.run_manual_experiment_execution") as mock_experiment_execution:
            exit_code = main(["experiment-execution"])

        self.assertEqual(0, exit_code)
        mock_experiment_execution.assert_called_once_with(symbol=DEFAULT_SYMBOL)

    def test_hypothesis_evaluation_command_dispatches_to_hypothesis_evaluation_runner(self):
        with patch("research.runner.run_manual_hypothesis_generation") as mock_hypotheses, patch(
            "research.runner.run_manual_experiment_request_generation"
        ) as mock_experiment_requests, patch(
            "research.runner.run_manual_experiment_execution"
        ) as mock_experiment_execution, patch(
            "research.runner.run_manual_hypothesis_evaluation"
        ) as mock_hypothesis_evaluation:
            exit_code = main(["hypothesis-evaluation", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_hypothesis_evaluation.assert_called_once_with(symbol="NVDA")
        mock_hypotheses.assert_not_called()
        mock_experiment_requests.assert_not_called()
        mock_experiment_execution.assert_not_called()

    def test_hypothesis_evaluation_command_uses_default_symbol(self):
        with patch("research.runner.run_manual_hypothesis_evaluation") as mock_hypothesis_evaluation:
            exit_code = main(["hypothesis-evaluation"])

        self.assertEqual(0, exit_code)
        mock_hypothesis_evaluation.assert_called_once_with(symbol=DEFAULT_SYMBOL)

    def test_hypothesis_reviews_command_dispatches_to_hypothesis_reviews_runner(self):
        with patch("research.runner.run_manual_hypothesis_generation") as mock_hypotheses, patch(
            "research.runner.run_manual_experiment_request_generation"
        ) as mock_experiment_requests, patch(
            "research.runner.run_manual_experiment_execution"
        ) as mock_experiment_execution, patch(
            "research.runner.run_manual_hypothesis_evaluation"
        ) as mock_hypothesis_evaluation, patch(
            "research.runner.run_manual_hypothesis_reviews"
        ) as mock_hypothesis_reviews, patch(
            "research.runner.run_manual_hypothesis_lifecycle"
        ) as mock_hypothesis_lifecycle, patch(
            "research.runner.run_manual_hypothesis_revisions"
        ) as mock_hypothesis_revisions:
            exit_code = main(["hypothesis-reviews", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_hypothesis_reviews.assert_called_once_with(symbol="NVDA")
        mock_hypotheses.assert_not_called()
        mock_experiment_requests.assert_not_called()
        mock_experiment_execution.assert_not_called()
        mock_hypothesis_evaluation.assert_not_called()
        mock_hypothesis_lifecycle.assert_not_called()
        mock_hypothesis_revisions.assert_not_called()

    def test_hypothesis_reviews_command_uses_default_symbol(self):
        with patch("research.runner.run_manual_hypothesis_reviews") as mock_hypothesis_reviews:
            exit_code = main(["hypothesis-reviews"])

        self.assertEqual(0, exit_code)
        mock_hypothesis_reviews.assert_called_once_with(symbol=DEFAULT_SYMBOL)

    def test_hypothesis_lifecycle_command_dispatches_to_hypothesis_lifecycle_runner(self):
        with patch("research.runner.run_manual_hypothesis_generation") as mock_hypotheses, patch(
            "research.runner.run_manual_experiment_request_generation"
        ) as mock_experiment_requests, patch(
            "research.runner.run_manual_experiment_execution"
        ) as mock_experiment_execution, patch(
            "research.runner.run_manual_hypothesis_evaluation"
        ) as mock_hypothesis_evaluation, patch(
            "research.runner.run_manual_hypothesis_reviews"
        ) as mock_hypothesis_reviews, patch(
            "research.runner.run_manual_hypothesis_lifecycle"
        ) as mock_hypothesis_lifecycle:
            exit_code = main(["hypothesis-lifecycle", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_hypothesis_lifecycle.assert_called_once_with(symbol="NVDA")
        mock_hypotheses.assert_not_called()
        mock_experiment_requests.assert_not_called()
        mock_experiment_execution.assert_not_called()
        mock_hypothesis_evaluation.assert_not_called()
        mock_hypothesis_reviews.assert_not_called()

    def test_hypothesis_revisions_command_dispatches_to_hypothesis_revisions_runner(self):
        with patch("research.runner.run_manual_hypothesis_generation") as mock_hypotheses, patch(
            "research.runner.run_manual_experiment_request_generation"
        ) as mock_experiment_requests, patch(
            "research.runner.run_manual_experiment_execution"
        ) as mock_experiment_execution, patch(
            "research.runner.run_manual_hypothesis_evaluation"
        ) as mock_hypothesis_evaluation, patch(
            "research.runner.run_manual_hypothesis_reviews"
        ) as mock_hypothesis_reviews, patch(
            "research.runner.run_manual_hypothesis_lifecycle"
        ) as mock_hypothesis_lifecycle, patch(
            "research.runner.run_manual_hypothesis_revisions"
        ) as mock_hypothesis_revisions:
            exit_code = main(["hypothesis-revisions", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_hypothesis_revisions.assert_called_once_with(symbol="NVDA")
        mock_hypotheses.assert_not_called()
        mock_experiment_requests.assert_not_called()
        mock_experiment_execution.assert_not_called()
        mock_hypothesis_evaluation.assert_not_called()
        mock_hypothesis_reviews.assert_not_called()
        mock_hypothesis_lifecycle.assert_not_called()

    def test_hypothesis_lifecycle_command_uses_default_symbol(self):
        with patch("research.runner.run_manual_hypothesis_lifecycle") as mock_hypothesis_lifecycle:
            exit_code = main(["hypothesis-lifecycle"])

        self.assertEqual(0, exit_code)
        mock_hypothesis_lifecycle.assert_called_once_with(symbol=DEFAULT_SYMBOL)

    def test_hypothesis_revisions_command_uses_default_symbol(self):
        with patch("research.runner.run_manual_hypothesis_revisions") as mock_hypothesis_revisions:
            exit_code = main(["hypothesis-revisions"])

        self.assertEqual(0, exit_code)
        mock_hypothesis_revisions.assert_called_once_with(symbol=DEFAULT_SYMBOL)

    def test_research_plan_command_dispatches_to_research_plan_runner(self):
        with patch("research.runner.run_manual_research_plan") as mock_research_plan:
            exit_code = main(["research-plan", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_research_plan.assert_called_once_with(symbol="NVDA")

    def test_research_plan_command_uses_default_symbol(self):
        with patch("research.runner.run_manual_research_plan") as mock_research_plan:
            exit_code = main(["research-plan"])

        self.assertEqual(0, exit_code)
        mock_research_plan.assert_called_once_with(symbol=DEFAULT_SYMBOL)

    def test_hypothesis_revision_apply_command_dispatches_to_runner_in_dry_run_mode(self):
        with patch(
            "research.runner.run_manual_hypothesis_revision_apply"
        ) as mock_hypothesis_revision_apply:
            exit_code = main(["hypothesis-revision-apply", "NVDA", "hyprevp-001", "--dry-run"])

        self.assertEqual(0, exit_code)
        mock_hypothesis_revision_apply.assert_called_once_with(
            symbol="NVDA",
            proposal_id="hyprevp-001",
            apply_changes=False,
        )

    def test_hypothesis_revision_apply_command_dispatches_to_runner_in_apply_mode(self):
        with patch(
            "research.runner.run_manual_hypothesis_revision_apply"
        ) as mock_hypothesis_revision_apply:
            exit_code = main(["hypothesis-revision-apply", "NVDA", "hyprevp-001", "--apply"])

        self.assertEqual(0, exit_code)
        mock_hypothesis_revision_apply.assert_called_once_with(
            symbol="NVDA",
            proposal_id="hyprevp-001",
            apply_changes=True,
        )

    def test_hypothesis_revision_apply_command_defaults_to_dry_run_when_mode_is_omitted(self):
        with patch(
            "research.runner.run_manual_hypothesis_revision_apply"
        ) as mock_hypothesis_revision_apply:
            exit_code = main(["hypothesis-revision-apply", "NVDA", "hyprevp-001"])

        self.assertEqual(0, exit_code)
        mock_hypothesis_revision_apply.assert_called_once_with(
            symbol="NVDA",
            proposal_id="hyprevp-001",
            apply_changes=False,
        )


if __name__ == "__main__":
    unittest.main()