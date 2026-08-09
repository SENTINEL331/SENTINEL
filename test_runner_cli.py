import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from config import settings
from research.runner import DEFAULT_SYMBOL, main


class RunnerCliTests(unittest.TestCase):
    def test_help_does_not_dispatch_generation(self):
        buffer = io.StringIO()

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
            "research.runner.run_manual_research_cycle"
        ) as mock_research_cycle, patch(
            "research.runner.run_manual_research_plan"
        ) as mock_research_plan, patch(
            "research.runner.run_manual_research_dashboard"
        ) as mock_research_dashboard, redirect_stdout(buffer):
            with self.assertRaises(SystemExit) as context:
                main(["--help"])

        self.assertEqual(0, context.exception.code)
        self.assertIn("research-cycle", buffer.getvalue())
        self.assertIn("research-state", buffer.getvalue())
        self.assertIn("research-dashboard", buffer.getvalue())
        self.assertIn("research-freshness", buffer.getvalue())
        self.assertIn("promotion-candidates", buffer.getvalue())
        self.assertIn("trade-candidate-proposals", buffer.getvalue())
        mock_hypotheses.assert_not_called()
        mock_experiment_requests.assert_not_called()
        mock_experiment_execution.assert_not_called()
        mock_hypothesis_evaluation.assert_not_called()
        mock_hypothesis_reviews.assert_not_called()
        mock_hypothesis_lifecycle.assert_not_called()
        mock_hypothesis_revisions.assert_not_called()
        mock_research_cycle.assert_not_called()
        mock_research_plan.assert_not_called()
        mock_research_dashboard.assert_not_called()

    def test_research_freshness_command_dispatches_to_research_freshness_runner(self):
        with patch("research.runner.run_manual_research_freshness") as mock_research_freshness:
            exit_code = main(["research-freshness", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_research_freshness.assert_called_once_with(symbol="NVDA")

    def test_research_freshness_command_uses_default_symbol(self):
        with patch("research.runner.run_manual_research_freshness") as mock_research_freshness:
            exit_code = main(["research-freshness"])

        self.assertEqual(0, exit_code)
        mock_research_freshness.assert_called_once_with(symbol=DEFAULT_SYMBOL)

    def test_promotion_candidates_command_dispatches_to_runner(self):
        with patch("research.runner.run_manual_promotion_candidates") as mock_promotion_candidates:
            exit_code = main(["promotion-candidates", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_promotion_candidates.assert_called_once_with(symbol="NVDA")

    def test_promotion_candidates_command_uses_default_symbol(self):
        with patch("research.runner.run_manual_promotion_candidates") as mock_promotion_candidates:
            exit_code = main(["promotion-candidates"])

        self.assertEqual(0, exit_code)
        mock_promotion_candidates.assert_called_once_with(symbol=DEFAULT_SYMBOL)

    def test_trade_candidate_proposals_command_dispatches_to_runner(self):
        with patch("research.runner.run_manual_trade_candidate_proposals") as mock_trade_candidate_proposals:
            exit_code = main(["trade-candidate-proposals", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_trade_candidate_proposals.assert_called_once_with(symbol="NVDA")

    def test_trade_candidate_proposals_command_uses_default_symbol(self):
        with patch("research.runner.run_manual_trade_candidate_proposals") as mock_trade_candidate_proposals:
            exit_code = main(["trade-candidate-proposals"])

        self.assertEqual(0, exit_code)
        mock_trade_candidate_proposals.assert_called_once_with(symbol=DEFAULT_SYMBOL)

    def test_research_cycle_help_includes_new_mode_flags(self):
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            with self.assertRaises(SystemExit) as context:
                main(["research-cycle", "--help"])

        self.assertEqual(0, context.exception.code)
        help_text = buffer.getvalue()
        self.assertIn("--revisions", help_text)
        self.assertIn("--full-safe", help_text)

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

    def test_experiment_execution_command_accepts_period_override(self):
        with patch("research.runner.run_manual_experiment_execution") as mock_experiment_execution:
            exit_code = main(["experiment-execution", "NVDA", "--period", "18m"])

        self.assertEqual(0, exit_code)
        mock_experiment_execution.assert_called_once_with(symbol="NVDA", period="18m")

    def test_experiment_execution_command_accepts_interval_override(self):
        with patch("research.runner.run_manual_experiment_execution") as mock_experiment_execution:
            exit_code = main(["experiment-execution", "NVDA", "--interval", "1wk"])

        self.assertEqual(0, exit_code)
        mock_experiment_execution.assert_called_once_with(symbol="NVDA", interval="1wk")

    def test_experiment_execution_command_accepts_period_and_interval_overrides(self):
        with patch("research.runner.run_manual_experiment_execution") as mock_experiment_execution:
            exit_code = main(
                ["experiment-execution", "NVDA", "--period", "18m", "--interval", "1wk"]
            )

        self.assertEqual(0, exit_code)
        mock_experiment_execution.assert_called_once_with(
            symbol="NVDA",
            period="18m",
            interval="1wk",
        )

    def test_experiment_execution_help_mentions_backtest_defaults(self):
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            with self.assertRaises(SystemExit) as context:
                main(["experiment-execution", "--help"])

        self.assertEqual(0, context.exception.code)
        help_text = buffer.getvalue()
        self.assertIn("--period", help_text)
        self.assertIn("--interval", help_text)
        self.assertIn(settings.BACKTEST_PERIOD, help_text)
        self.assertIn(settings.BACKTEST_INTERVAL, help_text)

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
            "research.runner.run_manual_research_cycle"
        ) as mock_research_cycle, patch(
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
        mock_research_cycle.assert_not_called()
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

    def test_research_state_command_dispatches_to_research_state_runner(self):
        with patch("research.runner.run_manual_research_state") as mock_research_state:
            exit_code = main(["research-state", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_research_state.assert_called_once_with(symbol="NVDA")

    def test_research_state_command_uses_default_symbol(self):
        with patch("research.runner.run_manual_research_state") as mock_research_state:
            exit_code = main(["research-state"])

        self.assertEqual(0, exit_code)
        mock_research_state.assert_called_once_with(symbol=DEFAULT_SYMBOL)

    def test_research_dashboard_command_dispatches_with_watchlist_default(self):
        with patch("research.runner.run_manual_research_dashboard") as mock_research_dashboard:
            exit_code = main(["research-dashboard"])

        self.assertEqual(0, exit_code)
        mock_research_dashboard.assert_called_once_with(symbols=[])

    def test_research_dashboard_command_dispatches_with_explicit_symbols(self):
        with patch("research.runner.run_manual_research_dashboard") as mock_research_dashboard:
            exit_code = main(["research-dashboard", "NVDA", "AAPL"])

        self.assertEqual(0, exit_code)
        mock_research_dashboard.assert_called_once_with(symbols=["NVDA", "AAPL"])

    def test_research_cycle_command_dispatches_to_runner(self):
        with patch("research.runner.run_manual_research_cycle") as mock_research_cycle:
            exit_code = main(["research-cycle", "NVDA"])

        self.assertEqual(0, exit_code)
        mock_research_cycle.assert_called_once_with(
            symbol="NVDA",
            dry_run=True,
            reviews=False,
            planned_experiments=False,
            run_experiments=False,
            revisions=False,
            full_safe=False,
        )

    def test_research_cycle_command_with_dry_run_flag_dispatches_to_runner(self):
        with patch("research.runner.run_manual_research_cycle") as mock_research_cycle:
            exit_code = main(["research-cycle", "NVDA", "--dry-run"])

        self.assertEqual(0, exit_code)
        mock_research_cycle.assert_called_once_with(
            symbol="NVDA",
            dry_run=True,
            reviews=False,
            planned_experiments=False,
            run_experiments=False,
            revisions=False,
            full_safe=False,
        )

    def test_research_cycle_command_with_reviews_flag_dispatches_to_runner(self):
        with patch("research.runner.run_manual_research_cycle") as mock_research_cycle:
            exit_code = main(["research-cycle", "NVDA", "--reviews"])

        self.assertEqual(0, exit_code)
        mock_research_cycle.assert_called_once_with(
            symbol="NVDA",
            dry_run=False,
            reviews=True,
            planned_experiments=False,
            run_experiments=False,
            revisions=False,
            full_safe=False,
        )

    def test_research_cycle_command_with_planned_experiments_flag_dispatches_to_runner(self):
        with patch("research.runner.run_manual_research_cycle") as mock_research_cycle:
            exit_code = main(["research-cycle", "NVDA", "--planned-experiments"])

        self.assertEqual(0, exit_code)
        mock_research_cycle.assert_called_once_with(
            symbol="NVDA",
            dry_run=False,
            reviews=False,
            planned_experiments=True,
            run_experiments=False,
            revisions=False,
            full_safe=False,
        )

    def test_research_cycle_command_with_run_experiments_flag_dispatches_to_runner(self):
        with patch("research.runner.run_manual_research_cycle") as mock_research_cycle:
            exit_code = main(["research-cycle", "NVDA", "--run-experiments"])

        self.assertEqual(0, exit_code)
        mock_research_cycle.assert_called_once_with(
            symbol="NVDA",
            dry_run=False,
            reviews=False,
            planned_experiments=False,
            run_experiments=True,
            revisions=False,
            full_safe=False,
        )

    def test_research_cycle_command_with_revisions_flag_dispatches_to_runner(self):
        with patch("research.runner.run_manual_research_cycle") as mock_research_cycle:
            exit_code = main(["research-cycle", "NVDA", "--revisions"])

        self.assertEqual(0, exit_code)
        mock_research_cycle.assert_called_once_with(
            symbol="NVDA",
            dry_run=False,
            reviews=False,
            planned_experiments=False,
            run_experiments=False,
            revisions=True,
            full_safe=False,
        )

    def test_research_cycle_command_with_full_safe_flag_dispatches_to_runner(self):
        with patch("research.runner.run_manual_research_cycle") as mock_research_cycle:
            exit_code = main(["research-cycle", "NVDA", "--full-safe"])

        self.assertEqual(0, exit_code)
        mock_research_cycle.assert_called_once_with(
            symbol="NVDA",
            dry_run=False,
            reviews=False,
            planned_experiments=False,
            run_experiments=False,
            revisions=False,
            full_safe=True,
        )

    def test_research_cycle_command_rejects_dry_run_and_reviews_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--dry-run", "--reviews"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_dry_run_and_planned_experiments_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--dry-run", "--planned-experiments"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_reviews_and_planned_experiments_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--reviews", "--planned-experiments"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_dry_run_and_run_experiments_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--dry-run", "--run-experiments"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_reviews_and_run_experiments_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--reviews", "--run-experiments"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_planned_experiments_and_run_experiments_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--planned-experiments", "--run-experiments"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_dry_run_and_revisions_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--dry-run", "--revisions"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_reviews_and_revisions_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--reviews", "--revisions"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_planned_experiments_and_revisions_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--planned-experiments", "--revisions"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_run_experiments_and_revisions_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--run-experiments", "--revisions"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_dry_run_and_full_safe_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--dry-run", "--full-safe"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_reviews_and_full_safe_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--reviews", "--full-safe"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_planned_experiments_and_full_safe_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--planned-experiments", "--full-safe"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_run_experiments_and_full_safe_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--run-experiments", "--full-safe"])

        self.assertEqual(2, context.exception.code)

    def test_research_cycle_command_rejects_revisions_and_full_safe_together(self):
        with self.assertRaises(SystemExit) as context:
            main(["research-cycle", "NVDA", "--revisions", "--full-safe"])

        self.assertEqual(2, context.exception.code)

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