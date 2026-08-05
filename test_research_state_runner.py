import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, call, patch

from research.experiment import ExperimentRequest
from research.experiment import ExperimentRequestStatus
from research.experiment import ExperimentTestType
from research.experiment_result import ExperimentMetrics
from research.experiment_result import ExperimentResult
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_revision_application import HypothesisRevisionApplication
from research.hypothesis_revision_application import HypothesisRevisionApplicationStatus
from research.hypothesis_revision_proposal import HypothesisRevisionProposal
from research.hypothesis_revision_proposal import HypothesisRevisionProposalType
from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation
from research.research_plan import ResearchPlan
from research.research_plan import ResearchPlanAction
from research.research_plan import ResearchPlanItem
from research.research_plan import ResearchPlanPriority
from research.runner import DEFAULT_SYMBOL
from research.runner import run_manual_research_state


class ManualResearchStateRunnerTests(unittest.TestCase):
    def _build_storage_with_lineage(self):
        now = datetime.now(timezone.utc)

        parent_one = Hypothesis(
            hypothesis_id="hyp-parent-001",
            symbol="NVDA",
            title="Parent one",
            description="Parent hypothesis one.",
            status=HypothesisStatus.ACTIVE,
            confidence=0.5,
            created_at=now,
            updated_at=now,
        )
        child_one = Hypothesis(
            hypothesis_id="hyp-child-001",
            symbol="NVDA",
            title="Child one",
            description="Child hypothesis.",
            status=HypothesisStatus.SUPPORTED,
            confidence=0.6,
            parent_hypothesis_id="hyp-parent-001",
            source_revision_proposal_id="hyprevp-001",
            created_at=now,
            updated_at=now,
        )
        parent_two = Hypothesis(
            hypothesis_id="hyp-parent-002",
            symbol="NVDA",
            title="Parent two",
            description="Parent hypothesis two.",
            status=HypothesisStatus.BLOCKED,
            confidence=0.4,
            created_at=now,
            updated_at=now,
        )

        executable_request = ExperimentRequest(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-parent-001",
            hypothesis_version_id="hyp-parent-001:v1",
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
        non_executable_request = ExperimentRequest(
            experiment_request_id="expreq-legacy-001",
            hypothesis_id="hyp-parent-002",
            hypothesis_version_id="hyp-parent-002:v1",
            symbol="NVDA",
            title="Non-executable request",
            objective="Objective",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions="Entry",
            exit_conditions="Exit",
            time_horizon="5D",
            status=ExperimentRequestStatus.PROPOSED,
        )

        completed_result = ExperimentResult(
            experiment_result_id="expr-001",
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-parent-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(
                trade_count=12,
                average_return=0.01,
                win_rate=0.6,
            ),
            summary="Completed",
            created_at=now,
            updated_at=now,
        )
        running_result = ExperimentResult(
            experiment_result_id="expr-002",
            experiment_request_id="expreq-legacy-001",
            hypothesis_id="hyp-parent-002",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.RUNNING,
            started_at=now,
            completed_at=None,
            metrics=ExperimentMetrics(),
            summary="Running",
            created_at=now,
            updated_at=now,
        )

        review_one = HypothesisReview(
            review_id="hyprev-001",
            hypothesis_id="hyp-parent-001",
            symbol="NVDA",
            recommendation=HypothesisReviewRecommendation.KEEP,
            rationale="Keep testing.",
            confidence=0.65,
            created_at=now,
        )
        review_two = HypothesisReview(
            review_id="hyprev-002",
            hypothesis_id="hyp-parent-002",
            symbol="NVDA",
            recommendation=HypothesisReviewRecommendation.REFINE,
            rationale="Refine approach.",
            confidence=0.58,
            created_at=now,
        )

        proposal = HypothesisRevisionProposal(
            proposal_id="hyprevp-001",
            symbol="NVDA",
            parent_hypothesis_id="hyp-parent-001",
            source_review_id="hyprev-001",
            lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
            proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
            proposed_title="Child one refined",
            proposed_description="Refined hypothesis",
            rationale="Zero trade cases suggest tighter trigger.",
            confidence=0.7,
            created_at=now,
        )

        application = HypothesisRevisionApplication(
            application_id="hypreva-001",
            proposal_id="hyprevp-001",
            symbol="NVDA",
            parent_hypothesis_id="hyp-parent-001",
            status=HypothesisRevisionApplicationStatus.DRY_RUN,
            apply_mode=False,
            message="Preview only",
            created_at=now,
        )

        storage = Mock()
        storage.load_hypotheses.return_value = [parent_one, child_one, parent_two]
        storage.load_experiment_requests.return_value = [
            executable_request,
            non_executable_request,
        ]
        storage.load_experiment_results.return_value = [completed_result, running_result]
        storage.load_hypothesis_reviews.return_value = [review_one, review_two]
        storage.load_hypothesis_revision_proposals.return_value = [proposal]
        storage.load_hypothesis_revision_applications.return_value = [application]

        return storage

    def test_research_state_output_includes_required_sections_and_read_only_flags(self):
        storage = self._build_storage_with_lineage()

        with patch("builtins.print") as mock_print, patch(
            "research.runner.ExperimentRequestService"
        ) as mock_experiment_request_service, patch(
            "research.runner.HypothesisReviewService"
        ) as mock_hypothesis_review_service, patch(
            "research.runner.HypothesisRevisionService"
        ) as mock_hypothesis_revision_service, patch(
            "research.runner.HypothesisRevisionApplicationService"
        ) as mock_hypothesis_revision_application_service, patch(
            "research.runner.ExperimentExecutor"
        ) as mock_experiment_executor:
            plan = run_manual_research_state(symbol="NVDA", storage=storage)

        self.assertEqual("NVDA", plan.symbol)
        mock_print.assert_any_call("Manual Research State: NVDA")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Object Counts")
        mock_print.assert_any_call("Hypothesis Status Summary")
        mock_print.assert_any_call("Evidence Summary")
        mock_print.assert_any_call("Research Plan Summary")
        mock_print.assert_any_call("Lineage Summary")
        mock_print.assert_any_call("Top Attention Items")
        mock_print.assert_any_call("Research state read complete. No records were modified.")

        mock_print.assert_any_call("- hypotheses : 3")
        mock_print.assert_any_call("- parent hypotheses : 2")
        mock_print.assert_any_call("- child hypotheses : 1")
        mock_print.assert_any_call("- experiment requests : 2")
        mock_print.assert_any_call("- executable experiment requests : 1")
        mock_print.assert_any_call("- completed experiment results : 1")
        mock_print.assert_any_call("- hypothesis reviews : 2")
        mock_print.assert_any_call("- revision proposals : 1")
        mock_print.assert_any_call("- revision applications : 1")
        mock_print.assert_any_call("- research plan items : 3")

        mock_experiment_request_service.assert_not_called()
        mock_hypothesis_review_service.assert_not_called()
        mock_hypothesis_revision_service.assert_not_called()
        mock_hypothesis_revision_application_service.assert_not_called()
        mock_experiment_executor.assert_not_called()

        storage.save_hypotheses.assert_not_called()
        storage.save_experiment_requests.assert_not_called()
        storage.save_experiment_results.assert_not_called()
        storage.save_hypothesis_reviews.assert_not_called()
        storage.save_hypothesis_revision_proposals.assert_not_called()
        storage.save_hypothesis_revision_applications.assert_not_called()

    def test_lineage_summary_shows_parent_child_relationships(self):
        storage = self._build_storage_with_lineage()

        with patch("builtins.print") as mock_print:
            run_manual_research_state(symbol="NVDA", storage=storage)

        mock_print.assert_any_call(
            "- parent_hypothesis_id=hyp-parent-001 child_hypothesis_id=hyp-child-001 source_revision_proposal_id=hyprevp-001"
        )

    def test_lineage_summary_prints_stable_empty_state_when_no_children_exist(self):
        now = datetime.now(timezone.utc)
        storage = Mock()
        storage.load_hypotheses.return_value = [
            Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Parent only",
                description="No child relationships.",
                status=HypothesisStatus.ACTIVE,
                confidence=0.5,
                created_at=now,
                updated_at=now,
            )
        ]
        storage.load_experiment_requests.return_value = []
        storage.load_experiment_results.return_value = []
        storage.load_hypothesis_reviews.return_value = []
        storage.load_hypothesis_revision_proposals.return_value = []
        storage.load_hypothesis_revision_applications.return_value = []

        with patch("builtins.print") as mock_print:
            run_manual_research_state(symbol="NVDA", storage=storage)

        mock_print.assert_any_call("No parent-child hypothesis lineage records found.")

    def test_top_attention_items_are_priority_ordered_and_limited_to_five(self):
        now = datetime.now(timezone.utc)
        storage = Mock()
        storage.load_hypotheses.return_value = [
            Hypothesis(
                hypothesis_id="hyp-001",
                symbol="NVDA",
                title="Hypothesis",
                description="Hypothesis",
                status=HypothesisStatus.ACTIVE,
                confidence=0.5,
                created_at=now,
                updated_at=now,
            )
        ]
        storage.load_experiment_requests.return_value = []
        storage.load_experiment_results.return_value = []
        storage.load_hypothesis_reviews.return_value = []
        storage.load_hypothesis_revision_proposals.return_value = []
        storage.load_hypothesis_revision_applications.return_value = []

        custom_plan = ResearchPlan(
            symbol="NVDA",
            items=(
                ResearchPlanItem(
                    symbol="NVDA",
                    hypothesis_id="hyp-low-001",
                    hypothesis_title="Low 1",
                    recommended_action=ResearchPlanAction.NO_ACTION,
                    priority=ResearchPlanPriority.LOW,
                    reason="Low reason 1",
                ),
                ResearchPlanItem(
                    symbol="NVDA",
                    hypothesis_id="hyp-high-001",
                    hypothesis_title="High 1",
                    recommended_action=ResearchPlanAction.GENERATE_REVISION_PROPOSAL,
                    priority=ResearchPlanPriority.HIGH,
                    reason="High reason 1",
                ),
                ResearchPlanItem(
                    symbol="NVDA",
                    hypothesis_id="hyp-medium-001",
                    hypothesis_title="Medium 1",
                    recommended_action=ResearchPlanAction.GENERATE_HYPOTHESIS_REVIEW,
                    priority=ResearchPlanPriority.MEDIUM,
                    reason="Medium reason 1",
                ),
                ResearchPlanItem(
                    symbol="NVDA",
                    hypothesis_id="hyp-high-002",
                    hypothesis_title="High 2",
                    recommended_action=ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST,
                    priority=ResearchPlanPriority.HIGH,
                    reason="High reason 2",
                ),
                ResearchPlanItem(
                    symbol="NVDA",
                    hypothesis_id="hyp-low-002",
                    hypothesis_title="Low 2",
                    recommended_action=ResearchPlanAction.MONITOR_EXISTING_CHILD,
                    priority=ResearchPlanPriority.LOW,
                    reason="Low reason 2",
                ),
                ResearchPlanItem(
                    symbol="NVDA",
                    hypothesis_id="hyp-medium-002",
                    hypothesis_title="Medium 2",
                    recommended_action=ResearchPlanAction.APPLY_REVISION_PROPOSAL_CANDIDATE,
                    priority=ResearchPlanPriority.MEDIUM,
                    reason="Medium reason 2",
                ),
            ),
        )

        with patch("builtins.print") as mock_print, patch(
            "research.runner.build_research_plan",
            return_value=custom_plan,
        ):
            run_manual_research_state(symbol="NVDA", storage=storage)

        mock_print.assert_has_calls(
            [
                call(
                    "- hypothesis_id=hyp-high-001 action=generate_revision_proposal priority=high"
                ),
                call("  reason: High reason 1"),
                call(
                    "- hypothesis_id=hyp-high-002 action=generate_experiment_request priority=high"
                ),
                call("  reason: High reason 2"),
                call(
                    "- hypothesis_id=hyp-medium-001 action=generate_hypothesis_review priority=medium"
                ),
                call("  reason: Medium reason 1"),
                call(
                    "- hypothesis_id=hyp-medium-002 action=apply_revision_proposal_candidate priority=medium"
                ),
                call("  reason: Medium reason 2"),
                call("- hypothesis_id=hyp-low-001 action=no_action priority=low"),
                call("  reason: Low reason 1"),
            ],
            any_order=False,
        )

        self.assertNotIn(
            call("- hypothesis_id=hyp-low-002 action=monitor_existing_child priority=low"),
            mock_print.mock_calls,
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
            plan = run_manual_research_state(storage=storage)

        self.assertEqual(DEFAULT_SYMBOL, plan.symbol)


if __name__ == "__main__":
    unittest.main()
