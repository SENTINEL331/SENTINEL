import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from research.experiment_result import ExperimentMetrics
from research.experiment_result import ExperimentResult
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation
from research.runner import DEFAULT_SYMBOL, run_manual_research_plan


class ManualResearchPlanRunnerTests(unittest.TestCase):
    def test_runner_prints_human_readable_research_plan(self):
        storage = Mock()
        storage.load_hypotheses.return_value = [
            Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Untested hypothesis",
                description="Still untouched.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.3,
            )
        ]
        storage.load_experiment_requests.return_value = []
        storage.load_experiment_results.return_value = []
        storage.load_hypothesis_reviews.return_value = []
        storage.load_hypothesis_revision_proposals.return_value = []
        storage.load_hypothesis_revision_applications.return_value = []

        with patch("builtins.print") as mock_print:
            plan = run_manual_research_plan(symbol="NVDA", storage=storage)

        self.assertEqual("NVDA", plan.symbol)
        self.assertEqual(1, len(plan.items))
        mock_print.assert_any_call("Manual Research Plan: NVDA")
        mock_print.assert_any_call("Research plan only; no records were modified.")
        mock_print.assert_any_call("Research Plan")
        mock_print.assert_any_call("- hyp-001 action=generate_experiment_request priority=medium")
        mock_print.assert_any_call(
            "  reason: needs_more_tests hypothesis has no open or executable experiment request"
        )

    def test_runner_uses_default_symbol_when_omitted(self):
        storage = Mock()
        storage.load_hypotheses.return_value = []
        storage.load_experiment_requests.return_value = []
        storage.load_experiment_results.return_value = []
        storage.load_hypothesis_reviews.return_value = []
        storage.load_hypothesis_revision_proposals.return_value = []
        storage.load_hypothesis_revision_applications.return_value = []

        with patch("builtins.print"):
            plan = run_manual_research_plan(storage=storage)

        self.assertEqual(DEFAULT_SYMBOL, plan.symbol)


if __name__ == "__main__":
    unittest.main()
