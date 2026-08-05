import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from research.experiment import ExperimentRequest
from research.experiment import ExperimentRequestStatus
from research.experiment import ExperimentTestType
from research.experiment_result import ExperimentMetrics
from research.experiment_result import ExperimentResult
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation
from research.runner import DEFAULT_SYMBOL
from research.runner import run_manual_research_cycle


class ManualResearchCycleRunnerTests(unittest.TestCase):
    def _build_storage(self, experiment_requests=None, experiment_results=None):
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
        storage.load_observations.return_value = []
        storage.load_experiment_requests.return_value = experiment_requests or []
        storage.load_experiment_results.return_value = experiment_results or []
        storage.load_hypothesis_reviews.return_value = []
        storage.load_hypothesis_revision_proposals.return_value = []
        storage.load_hypothesis_revision_applications.return_value = []
        return storage

    def _build_completed_result(self):
        now = datetime.now(timezone.utc)
        return ExperimentResult(
            experiment_result_id="expres-001",
            experiment_request_id="expr-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(
                trade_count=10,
                average_return=0.012,
                win_rate=0.6,
            ),
            summary="Completed",
            failure_reason=None,
            created_at=now,
            updated_at=now,
        )

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

    def test_reviews_mode_generates_reviews_for_candidates_and_prints_mode_flags(self):
        storage = self._build_storage(experiment_results=[self._build_completed_result()])
        generated_reviews = [
            HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.KEEP,
                rationale="Evidence is directionally supportive.",
                confidence=0.7,
            )
        ]
        review_service = Mock()
        review_service.generate_for_symbol.return_value = generated_reviews
        storage.load_hypothesis_reviews.side_effect = [
            [],
            generated_reviews,
        ]

        with patch("builtins.print") as mock_print, patch(
            "research.runner.ExperimentRequestService"
        ) as mock_experiment_request_service, patch(
            "research.runner.HypothesisRevisionService"
        ) as mock_hypothesis_revision_service, patch(
            "research.runner.HypothesisRevisionApplicationService"
        ) as mock_hypothesis_revision_application_service, patch(
            "research.runner.ExperimentExecutor"
        ) as mock_experiment_executor:
            plan = run_manual_research_cycle(
                symbol="NVDA",
                dry_run=False,
                reviews=True,
                storage=storage,
                hypothesis_review_service=review_service,
            )

        self.assertEqual("NVDA", plan.symbol)
        review_service.generate_for_symbol.assert_called_once()
        called_kwargs = review_service.generate_for_symbol.call_args.kwargs
        self.assertEqual("NVDA", called_kwargs["symbol"])
        self.assertEqual(1, len(called_kwargs["hypotheses"]))
        self.assertEqual("hyp-001", called_kwargs["hypotheses"][0].hypothesis_id)
        mock_experiment_request_service.assert_not_called()
        mock_hypothesis_revision_service.assert_not_called()
        mock_hypothesis_revision_application_service.assert_not_called()
        mock_experiment_executor.assert_not_called()
        storage.save_experiment_requests.assert_not_called()
        storage.save_hypothesis_revision_proposals.assert_not_called()
        storage.save_hypothesis_revision_applications.assert_not_called()
        mock_print.assert_any_call("Manual Research Cycle: NVDA")
        mock_print.assert_any_call("Mode : reviews")
        mock_print.assert_any_call("Records Modified : yes")
        mock_print.assert_any_call("AI Calls Allowed : yes")
        mock_print.assert_any_call("Hypotheses Loaded : 1")
        mock_print.assert_any_call("Review Candidates : 1")
        mock_print.assert_any_call("Reviews Generated : 1")
        mock_print.assert_any_call("Research Plan Items : 1")
        mock_print.assert_any_call("Final Status : completed")

    def test_reviews_mode_no_candidates_prints_noop_and_skips_ai_calls(self):
        storage = self._build_storage()
        review_service = Mock()

        with patch("builtins.print") as mock_print:
            plan = run_manual_research_cycle(
                symbol="NVDA",
                dry_run=False,
                reviews=True,
                storage=storage,
                hypothesis_review_service=review_service,
            )

        self.assertEqual("NVDA", plan.symbol)
        review_service.generate_for_symbol.assert_not_called()
        mock_print.assert_any_call("Review Candidates : 0")
        mock_print.assert_any_call("Reviews Generated : 0")
        mock_print.assert_any_call("Final Status : no-op")
        mock_print.assert_any_call("No-op: no hypotheses currently require review generation.")

    def test_research_cycle_rejects_conflicting_modes(self):
        storage = self._build_storage()

        with self.assertRaises(ValueError):
            run_manual_research_cycle(
                symbol="NVDA",
                dry_run=True,
                reviews=True,
                storage=storage,
            )

    def test_planned_experiments_mode_generates_requests_for_selected_hypotheses_and_prints_flags(self):
        storage = self._build_storage()
        generated_requests = [
            ExperimentRequest(
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                hypothesis_version_id="hyp-001:v1",
                symbol="NVDA",
                title="Validate momentum continuation",
                objective="Test initial evidence.",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                entry_conditions="Entry",
                machine_readable_entry_conditions=(
                    {"field": "Close", "operator": ">", "value": 100.0},
                ),
                exit_conditions="Exit",
                time_horizon="5D",
                forward_horizon=5,
                status=ExperimentRequestStatus.PROPOSED,
            )
        ]
        storage.load_experiment_requests.side_effect = [
            [],
            generated_requests,
        ]
        experiment_request_service = Mock()
        experiment_request_service.generate_for_symbol.return_value = generated_requests
        journal = Mock()
        journal.build.return_value = "Research Journal: NVDA"

        with patch("builtins.print") as mock_print, patch(
            "research.runner.ExperimentExecutor"
        ) as mock_experiment_executor, patch(
            "research.runner.HypothesisReviewService"
        ) as mock_hypothesis_review_service, patch(
            "research.runner.HypothesisRevisionService"
        ) as mock_hypothesis_revision_service, patch(
            "research.runner.HypothesisRevisionApplicationService"
        ) as mock_hypothesis_revision_application_service:
            plan = run_manual_research_cycle(
                symbol="NVDA",
                dry_run=False,
                planned_experiments=True,
                storage=storage,
                experiment_request_service=experiment_request_service,
                journal=journal,
            )

        self.assertEqual("NVDA", plan.symbol)
        experiment_request_service.generate_for_symbol.assert_called_once()
        called_kwargs = experiment_request_service.generate_for_symbol.call_args.kwargs
        self.assertEqual("NVDA", called_kwargs["symbol"])
        self.assertEqual(1, len(called_kwargs["hypotheses"]))
        self.assertEqual("hyp-001", called_kwargs["hypotheses"][0].hypothesis_id)
        mock_experiment_executor.assert_not_called()
        mock_hypothesis_review_service.assert_not_called()
        mock_hypothesis_revision_service.assert_not_called()
        mock_hypothesis_revision_application_service.assert_not_called()
        storage.save_hypothesis_reviews.assert_not_called()
        storage.save_hypothesis_revision_proposals.assert_not_called()
        storage.save_hypothesis_revision_applications.assert_not_called()
        mock_print.assert_any_call("Manual Research Cycle: NVDA")
        mock_print.assert_any_call("Mode : planned-experiments")
        mock_print.assert_any_call("Records Modified : yes")
        mock_print.assert_any_call("AI Calls Allowed : yes")
        mock_print.assert_any_call("Hypotheses Loaded : 1")
        mock_print.assert_any_call("Hypotheses Selected By Plan : 1")
        mock_print.assert_any_call("Hypotheses Skipped By Plan : 0")
        mock_print.assert_any_call("Experiment Requests Generated : 1")
        mock_print.assert_any_call("Research Plan Items : 1")
        mock_print.assert_any_call("Final Status : completed")

    def test_planned_experiments_mode_no_candidates_prints_noop_and_skips_ai_calls(self):
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Already has request",
            description="Not a planned experiment candidate.",
            status=HypothesisStatus.ACTIVE,
            confidence=0.4,
        )
        existing_request = ExperimentRequest(
            experiment_request_id="expreq-existing",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Existing request",
            objective="Objective",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Entry",
            machine_readable_entry_conditions=(
                {"field": "Close", "operator": ">", "value": 100.0},
            ),
            exit_conditions="Exit",
            time_horizon="5D",
            forward_horizon=5,
            status=ExperimentRequestStatus.PROPOSED,
        )
        storage = self._build_storage(experiment_requests=[existing_request])
        storage.load_hypotheses.return_value = [hypothesis]
        experiment_request_service = Mock()
        journal = Mock()

        with patch("builtins.print") as mock_print:
            plan = run_manual_research_cycle(
                symbol="NVDA",
                dry_run=False,
                planned_experiments=True,
                storage=storage,
                experiment_request_service=experiment_request_service,
                journal=journal,
            )

        self.assertEqual("NVDA", plan.symbol)
        experiment_request_service.generate_for_symbol.assert_not_called()
        journal.build.assert_not_called()
        mock_print.assert_any_call("Hypotheses Selected By Plan : 0")
        mock_print.assert_any_call("Hypotheses Skipped By Plan : 1")
        mock_print.assert_any_call("Experiment Requests Generated : 0")
        mock_print.assert_any_call("Final Status : no-op")
        mock_print.assert_any_call("No-op: no hypotheses currently require planned experiment requests.")

    def test_research_cycle_rejects_reviews_and_planned_experiments_together(self):
        storage = self._build_storage()

        with self.assertRaises(ValueError):
            run_manual_research_cycle(
                symbol="NVDA",
                dry_run=False,
                reviews=True,
                planned_experiments=True,
                storage=storage,
            )

    def test_run_experiments_mode_executes_executable_requests_and_prints_counts(self):
        executable_request = ExperimentRequest(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Executable request",
            objective="Objective",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Entry",
            machine_readable_entry_conditions=(
                {"field": "Close", "operator": ">", "value": 100.0},
            ),
            exit_conditions="Exit",
            time_horizon="5D",
            forward_horizon=5,
            status=ExperimentRequestStatus.PROPOSED,
        )
        storage = self._build_storage(experiment_requests=[executable_request])
        execution_result = self._build_completed_result()
        storage.load_experiment_results.side_effect = [
            [],
            [execution_result],
        ]
        storage.load_experiment_requests.side_effect = [
            [executable_request],
            [executable_request],
            [executable_request],
        ]
        executor = Mock()
        executor.execute.return_value = execution_result

        with patch("builtins.print") as mock_print, patch(
            "research.runner.ExperimentRequestService"
        ) as mock_experiment_request_service, patch(
            "research.runner.HypothesisReviewService"
        ) as mock_hypothesis_review_service, patch(
            "research.runner.HypothesisRevisionService"
        ) as mock_hypothesis_revision_service, patch(
            "research.runner.HypothesisRevisionApplicationService"
        ) as mock_hypothesis_revision_application_service:
            plan = run_manual_research_cycle(
                symbol="NVDA",
                dry_run=False,
                run_experiments=True,
                storage=storage,
                executor=executor,
            )

        self.assertEqual("NVDA", plan.symbol)
        executor.execute.assert_called_once_with(executable_request)
        storage.save_experiment_results.assert_called_once_with("NVDA", [execution_result])
        mock_experiment_request_service.assert_not_called()
        mock_hypothesis_review_service.assert_not_called()
        mock_hypothesis_revision_service.assert_not_called()
        mock_hypothesis_revision_application_service.assert_not_called()
        storage.save_experiment_requests.assert_not_called()
        storage.save_hypothesis_reviews.assert_not_called()
        storage.save_hypothesis_revision_proposals.assert_not_called()
        storage.save_hypothesis_revision_applications.assert_not_called()
        mock_print.assert_any_call("Manual Research Cycle: NVDA")
        mock_print.assert_any_call("Mode : run-experiments")
        mock_print.assert_any_call("Records Modified : yes")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Requests Loaded : 1")
        mock_print.assert_any_call("Requests Executed : 1")
        mock_print.assert_any_call("Requests Skipped : 0")
        mock_print.assert_any_call("Results Saved : 1")
        mock_print.assert_any_call("Not Implemented : 0")
        mock_print.assert_any_call("Research Plan Items : 1")
        mock_print.assert_any_call("Final Status : completed")

    def test_run_experiments_mode_no_executable_requests_prints_noop(self):
        non_executable_request = ExperimentRequest(
            experiment_request_id="expreq-legacy-001",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Legacy request",
            objective="Objective",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Legacy entry",
            exit_conditions="Legacy exit",
            time_horizon="5D",
            status=ExperimentRequestStatus.PROPOSED,
        )
        storage = self._build_storage(experiment_requests=[non_executable_request])
        storage.load_experiment_results.side_effect = [
            [],
            [],
        ]
        storage.load_experiment_requests.side_effect = [
            [non_executable_request],
            [non_executable_request],
            [non_executable_request],
        ]
        executor = Mock()

        with patch("builtins.print") as mock_print:
            plan = run_manual_research_cycle(
                symbol="NVDA",
                dry_run=False,
                run_experiments=True,
                storage=storage,
                executor=executor,
            )

        self.assertEqual("NVDA", plan.symbol)
        executor.execute.assert_not_called()
        storage.save_experiment_results.assert_not_called()
        mock_print.assert_any_call("Mode : run-experiments")
        mock_print.assert_any_call("Requests Loaded : 1")
        mock_print.assert_any_call("Requests Executed : 0")
        mock_print.assert_any_call("Requests Skipped : 1")
        mock_print.assert_any_call("Results Saved : 0")
        mock_print.assert_any_call("Final Status : no-op")
        mock_print.assert_any_call("No-op: no executable experiment requests currently available for this symbol.")

    def test_research_cycle_rejects_reviews_and_run_experiments_together(self):
        storage = self._build_storage()

        with self.assertRaises(ValueError):
            run_manual_research_cycle(
                symbol="NVDA",
                dry_run=False,
                reviews=True,
                run_experiments=True,
                storage=storage,
            )


if __name__ == "__main__":
    unittest.main()
