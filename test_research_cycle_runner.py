import unittest
from unittest.mock import Mock, patch

from research.experiment import ExperimentRequest
from research.experiment import ExperimentRequestStatus
from research.experiment import ExperimentTestType
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.runner import DEFAULT_SYMBOL
from research.runner import run_manual_research_cycle


class ManualResearchCycleRunnerTests(unittest.TestCase):
    def _build_storage(self, experiment_requests=None):
        storage = Mock()
        storage.load_hypotheses.return_value = [
            Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Untested momentum hypothesis",
                description="Initial evidence only.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.42,
            )
        ]
        storage.load_experiment_requests.return_value = experiment_requests or []
        storage.load_experiment_results.return_value = []
        storage.load_hypothesis_reviews.return_value = []
        storage.load_hypothesis_revision_proposals.return_value = []
        storage.load_hypothesis_revision_applications.return_value = []
        return storage

    def test_dry_run_preview_prints_current_state_and_plan(self):
        storage = self._build_storage()

        with patch("builtins.print") as mock_print:
            plan = run_manual_research_cycle(symbol="NVDA", storage=storage)

        self.assertEqual("NVDA", plan.symbol)
        self.assertGreaterEqual(len(plan.items), 1)
        mock_print.assert_any_call("Manual Research Cycle: NVDA")
        mock_print.assert_any_call("Mode : dry-run")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Hypotheses Loaded : 1")
        mock_print.assert_any_call("Experiment Requests Loaded : 0")
        mock_print.assert_any_call("Completed Results Loaded : 0")
        mock_print.assert_any_call("Research Plan Items : 1")
        mock_print.assert_any_call("Planned Actions")
        mock_print.assert_any_call("Research Plan")
        mock_print.assert_any_call("Dry run complete. No records were modified.")
        mock_print.assert_any_call(
            "- hyp-001 action=generate_experiment_request priority=medium"
        )

    def test_dry_run_does_not_call_ai_or_write_records(self):
        storage = self._build_storage()

        with patch("research.runner.ExperimentRequestService") as mock_experiment_request_service, patch(
            "research.runner.HypothesisReviewService"
        ) as mock_hypothesis_review_service, patch(
            "research.runner.HypothesisRevisionService"
        ) as mock_hypothesis_revision_service, patch(
            "builtins.print"
        ):
            run_manual_research_cycle(symbol="NVDA", storage=storage)

        mock_experiment_request_service.assert_not_called()
        mock_hypothesis_review_service.assert_not_called()
        mock_hypothesis_revision_service.assert_not_called()
        storage.save_experiment_requests.assert_not_called()
        storage.save_hypothesis_reviews.assert_not_called()
        storage.save_hypothesis_revision_proposals.assert_not_called()
        storage.save_hypothesis_revision_applications.assert_not_called()

    def test_runner_uses_default_symbol_when_omitted(self):
        storage = self._build_storage()

        with patch("builtins.print"):
            plan = run_manual_research_cycle(storage=storage)

        self.assertEqual(DEFAULT_SYMBOL, plan.symbol)


if __name__ == "__main__":
    unittest.main()
