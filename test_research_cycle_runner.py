import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from config import settings
from research.experiment import ExperimentRequest
from research.experiment import ExperimentRequestStatus
from research.experiment import ExperimentTestType
from research.experiment_result import ExperimentMetrics
from research.experiment_result import ExperimentResult
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_revision_proposal import HypothesisRevisionProposal
from research.hypothesis_revision_proposal import HypothesisRevisionProposalType
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
        executor.execute.assert_called_once_with(
            executable_request,
            period=settings.BACKTEST_PERIOD,
            interval=settings.BACKTEST_INTERVAL,
        )
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
        mock_print.assert_any_call(f"Backtest Period : {settings.BACKTEST_PERIOD}")
        mock_print.assert_any_call(f"Backtest Interval : {settings.BACKTEST_INTERVAL}")
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

    def test_revisions_mode_selects_only_revision_candidates_and_prints_mode_flags(self):
        now = datetime.now(timezone.utc)
        candidate_hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Refine candidate",
            description="Needs refinement after repeated zero-trade results.",
            status=HypothesisStatus.ACTIVE,
            confidence=0.4,
        )
        non_candidate_hypothesis = Hypothesis(
            hypothesis_id="hyp-002",
            symbol="NVDA",
            title="Needs tests",
            description="Needs experiment request.",
            status=HypothesisStatus.ACTIVE,
            confidence=0.3,
        )
        storage = self._build_storage(
            experiment_results=[
                ExperimentResult(
                    experiment_result_id="expr-001",
                    experiment_request_id="expreq-001",
                    hypothesis_id="hyp-001",
                    symbol="NVDA",
                    test_type=ExperimentTestType.INITIAL_BACKTEST,
                    status=ExperimentResultStatus.COMPLETED,
                    started_at=now,
                    completed_at=now,
                    metrics=ExperimentMetrics(trade_count=0, average_return=0.0, win_rate=0.0),
                    summary="Completed with zero trades.",
                    created_at=now,
                    updated_at=now,
                ),
                ExperimentResult(
                    experiment_result_id="expr-002",
                    experiment_request_id="expreq-002",
                    hypothesis_id="hyp-001",
                    symbol="NVDA",
                    test_type=ExperimentTestType.INITIAL_BACKTEST,
                    status=ExperimentResultStatus.COMPLETED,
                    started_at=now,
                    completed_at=now,
                    metrics=ExperimentMetrics(trade_count=0, average_return=0.0, win_rate=0.0),
                    summary="Completed with zero trades.",
                    created_at=now,
                    updated_at=now,
                ),
            ]
        )
        storage.load_hypotheses.return_value = [candidate_hypothesis, non_candidate_hypothesis]
        storage.load_hypothesis_reviews.return_value = [
            HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.NEEDS_MORE_TESTS,
                rationale="Additional targeted testing may be required.",
                confidence=0.6,
                created_at=now,
            )
        ]

        generated_proposals = [
            HypothesisRevisionProposal(
                proposal_id="hyprevp-001",
                symbol="NVDA",
                parent_hypothesis_id="hyp-001",
                source_review_id="hyprev-001",
                lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
                proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
                proposed_title="Refined setup",
                proposed_description="Narrow trigger conditions.",
                rationale="Repeated zero-trade outcomes suggest trigger refinement.",
                confidence=0.7,
                created_at=now,
            )
        ]
        storage.load_hypothesis_revision_proposals.side_effect = [
            [],
            generated_proposals,
        ]
        revision_service = Mock()
        revision_service.generate_for_symbol.return_value = generated_proposals

        with patch("builtins.print") as mock_print, patch(
            "research.runner.ExperimentRequestService"
        ) as mock_experiment_request_service, patch(
            "research.runner.HypothesisReviewService"
        ) as mock_hypothesis_review_service:
            plan = run_manual_research_cycle(
                symbol="NVDA",
                dry_run=False,
                revisions=True,
                storage=storage,
                hypothesis_revision_service=revision_service,
            )

        self.assertEqual("NVDA", plan.symbol)
        revision_service.generate_for_symbol.assert_called_once()
        called_kwargs = revision_service.generate_for_symbol.call_args.kwargs
        self.assertEqual("NVDA", called_kwargs["symbol"])
        self.assertEqual(1, len(called_kwargs["hypotheses"]))
        self.assertEqual("hyp-001", called_kwargs["hypotheses"][0].hypothesis_id)
        mock_experiment_request_service.assert_not_called()
        mock_hypothesis_review_service.assert_not_called()
        storage.save_experiment_results.assert_not_called()
        storage.save_experiment_requests.assert_not_called()
        storage.save_hypothesis_reviews.assert_not_called()
        storage.save_hypothesis_revision_applications.assert_not_called()
        mock_print.assert_any_call("Mode : revisions")
        mock_print.assert_any_call("Records Modified : yes")
        mock_print.assert_any_call("AI Calls Allowed : yes")
        mock_print.assert_any_call("Hypotheses Loaded : 2")
        mock_print.assert_any_call("Revision Candidates : 1")
        mock_print.assert_any_call("Revision Proposals Generated : 1")
        mock_print.assert_any_call("Final Status : completed")

    def test_revisions_mode_no_candidates_prints_noop_and_skips_ai_calls(self):
        storage = self._build_storage()
        revision_service = Mock()

        with patch("builtins.print") as mock_print:
            plan = run_manual_research_cycle(
                symbol="NVDA",
                dry_run=False,
                revisions=True,
                storage=storage,
                hypothesis_revision_service=revision_service,
            )

        self.assertEqual("NVDA", plan.symbol)
        revision_service.generate_for_symbol.assert_not_called()
        mock_print.assert_any_call("Mode : revisions")
        mock_print.assert_any_call("Revision Candidates : 0")
        mock_print.assert_any_call("Revision Proposals Generated : 0")
        mock_print.assert_any_call("Final Status : no-op")
        mock_print.assert_any_call("No-op: no hypotheses currently require revision proposal generation.")

    def test_full_safe_mode_runs_expected_orchestration_steps_in_order(self):
        now = datetime.now(timezone.utc)
        hypotheses = [
            Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Full-safe candidate",
                description="End-to-end safe orchestration candidate.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.5,
            )
        ]
        observations = []
        experiment_requests = []
        experiment_results = []
        hypothesis_reviews = []
        revision_proposals = []
        revision_applications = []

        storage = Mock()
        storage.load_hypotheses.side_effect = lambda symbol: list(hypotheses)
        storage.load_observations.side_effect = lambda symbol: list(observations)
        storage.load_experiment_requests.side_effect = lambda symbol: list(experiment_requests)
        storage.load_experiment_results.side_effect = lambda symbol: list(experiment_results)
        storage.load_hypothesis_reviews.side_effect = lambda symbol: list(hypothesis_reviews)
        storage.load_hypothesis_revision_proposals.side_effect = lambda symbol: list(revision_proposals)
        storage.load_hypothesis_revision_applications.side_effect = lambda symbol: list(revision_applications)
        storage.save_experiment_results.side_effect = lambda symbol, results: experiment_results.extend(results)

        step_calls = []
        generated_request_1 = ExperimentRequest(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Planned request 1",
            objective="Objective 1",
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
        generated_request_2 = ExperimentRequest(
            experiment_request_id="expreq-002",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Planned request 2",
            objective="Objective 2",
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
        generated_requests = [generated_request_1, generated_request_2]

        experiment_request_service = Mock()

        def _generate_requests(**kwargs):
            step_calls.append("step2_generate_experiment_requests")
            experiment_requests.extend(generated_requests)
            return generated_requests

        experiment_request_service.generate_for_symbol.side_effect = _generate_requests

        executor = Mock()
        execution_results_queue = [
            ExperimentResult(
                experiment_result_id="expr-001",
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=now,
                completed_at=now,
                metrics=ExperimentMetrics(trade_count=0, average_return=0.0, win_rate=0.0),
                summary="Completed",
                created_at=now,
                updated_at=now,
            ),
            ExperimentResult(
                experiment_result_id="expr-002",
                experiment_request_id="expreq-002",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=now,
                completed_at=now,
                metrics=ExperimentMetrics(trade_count=0, average_return=0.0, win_rate=0.0),
                summary="Completed",
                created_at=now,
                updated_at=now,
            ),
        ]

        def _execute_request(request, period, interval):
            step_calls.append("step3_execute_experiment")
            self.assertEqual(settings.BACKTEST_PERIOD, period)
            self.assertEqual(settings.BACKTEST_INTERVAL, interval)
            return execution_results_queue.pop(0)

        executor.execute.side_effect = _execute_request

        hypothesis_review_service = Mock()

        def _generate_reviews(**kwargs):
            step_calls.append("step5_generate_reviews")
            generated = [
                HypothesisReview(
                    review_id="hyprev-001",
                    hypothesis_id="hyp-001",
                    symbol="NVDA",
                    recommendation=HypothesisReviewRecommendation.NEEDS_MORE_TESTS,
                    rationale="Review generated after completed experiments.",
                    confidence=0.6,
                    created_at=datetime.now(timezone.utc),
                )
            ]
            hypothesis_reviews.extend(generated)
            return generated

        hypothesis_review_service.generate_for_symbol.side_effect = _generate_reviews

        hypothesis_revision_service = Mock()

        def _generate_revisions(**kwargs):
            step_calls.append("step7_generate_revisions")
            generated = [
                HypothesisRevisionProposal(
                    proposal_id="hyprevp-001",
                    symbol="NVDA",
                    parent_hypothesis_id="hyp-001",
                    source_review_id="hyprev-001",
                    lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
                    proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
                    proposed_title="Refined setup",
                    proposed_description="Narrow trigger conditions.",
                    rationale="Repeated zero-trade outcomes suggest refinement.",
                    confidence=0.7,
                    created_at=datetime.now(timezone.utc),
                )
            ]
            revision_proposals.extend(generated)
            return generated

        hypothesis_revision_service.generate_for_symbol.side_effect = _generate_revisions

        journal = Mock()
        journal.build.return_value = "Research Journal: NVDA"

        with patch("builtins.print") as mock_print:
            plan = run_manual_research_cycle(
                symbol="NVDA",
                dry_run=False,
                full_safe=True,
                storage=storage,
                experiment_request_service=experiment_request_service,
                executor=executor,
                hypothesis_review_service=hypothesis_review_service,
                hypothesis_revision_service=hypothesis_revision_service,
                journal=journal,
            )

        self.assertEqual("NVDA", plan.symbol)
        self.assertEqual(
            [
                "step2_generate_experiment_requests",
                "step3_execute_experiment",
                "step3_execute_experiment",
                "step5_generate_reviews",
                "step7_generate_revisions",
            ],
            step_calls,
        )
        storage.save_hypothesis_revision_applications.assert_not_called()
        mock_print.assert_any_call("Mode : full-safe")
        mock_print.assert_any_call("Records Modified : yes")
        mock_print.assert_any_call("AI Calls Allowed : yes")
        mock_print.assert_any_call("Initial Research Plan Items : 1")
        mock_print.assert_any_call("Planned Experiment Candidates : 1")
        mock_print.assert_any_call("Experiment Requests Generated : 2")
        mock_print.assert_any_call("Requests Executed : 2")
        mock_print.assert_any_call("Results Saved : 2")
        mock_print.assert_any_call("Review Candidates : 1")
        mock_print.assert_any_call("Reviews Generated : 1")
        mock_print.assert_any_call("Revision Candidates : 1")
        mock_print.assert_any_call("Revision Proposals Generated : 1")
        mock_print.assert_any_call("Final Status : completed")
        mock_print.assert_any_call("- No hypotheses were mutated.")
        mock_print.assert_any_call("- No revision proposals were applied.")
        mock_print.assert_any_call("- No child hypotheses were created.")
        mock_print.assert_any_call("- No trades were created or executed.")
        mock_print.assert_any_call("Revision proposals are not applied automatically.")

    def test_full_safe_mode_noop_steps_continue_and_print_safety_summary(self):
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
        experiment_request_service = Mock()
        hypothesis_review_service = Mock()
        hypothesis_revision_service = Mock()
        executor = Mock()

        with patch("builtins.print") as mock_print:
            plan = run_manual_research_cycle(
                symbol="NVDA",
                dry_run=False,
                full_safe=True,
                storage=storage,
                experiment_request_service=experiment_request_service,
                executor=executor,
                hypothesis_review_service=hypothesis_review_service,
                hypothesis_revision_service=hypothesis_revision_service,
                journal=Mock(),
            )

        self.assertEqual("NVDA", plan.symbol)
        experiment_request_service.generate_for_symbol.assert_not_called()
        hypothesis_review_service.generate_for_symbol.assert_not_called()
        hypothesis_revision_service.generate_for_symbol.assert_not_called()
        executor.execute.assert_not_called()
        mock_print.assert_any_call("Mode : full-safe")
        mock_print.assert_any_call("Planned Experiment Candidates : 0")
        mock_print.assert_any_call("Experiment Requests Generated : 0")
        mock_print.assert_any_call("Requests Executed : 0")
        mock_print.assert_any_call("Results Saved : 0")
        mock_print.assert_any_call("Review Candidates : 0")
        mock_print.assert_any_call("Reviews Generated : 0")
        mock_print.assert_any_call("Revision Candidates : 0")
        mock_print.assert_any_call("Revision Proposals Generated : 0")
        mock_print.assert_any_call("Safety Summary")

    def test_research_cycle_rejects_run_experiments_and_full_safe_together(self):
        storage = self._build_storage()

        with self.assertRaises(ValueError):
            run_manual_research_cycle(
                symbol="NVDA",
                dry_run=False,
                run_experiments=True,
                full_safe=True,
                storage=storage,
            )


if __name__ == "__main__":
    unittest.main()
