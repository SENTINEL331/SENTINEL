import unittest
from datetime import datetime, timezone

from research.experiment import ExperimentRequest
from research.experiment import ExperimentRequestStatus
from research.experiment import ExperimentTestType
from research.experiment_result import ExperimentMetrics
from research.experiment_result import ExperimentResult
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import Hypothesis
from research.hypothesis import HypothesisStatus
from research.hypothesis_evaluation import evaluate_hypothesis_evidence
from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_lifecycle import recommend_hypothesis_lifecycle_actions
from research.hypothesis_lifecycle import select_latest_hypothesis_reviews
from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation
from research.hypothesis_revision_application import HypothesisRevisionApplication
from research.hypothesis_revision_application import HypothesisRevisionApplicationStatus
from research.hypothesis_revision_proposal import HypothesisRevisionProposal
from research.hypothesis_revision_proposal import HypothesisRevisionProposalType
from research.research_plan import ResearchPlanAction
from research.research_plan import ResearchPlanPriority
from research.research_plan import build_research_plan


class ResearchPlanTests(unittest.TestCase):
    def _build_plan(
        self,
        hypotheses,
        experiment_requests=(),
        experiment_results=(),
        reviews=(),
        proposals=(),
        applications=(),
    ):
        evidence_summaries = evaluate_hypothesis_evidence(
            hypotheses=hypotheses,
            experiment_results=experiment_results,
            experiment_requests=experiment_requests,
        )
        latest_reviews_by_hypothesis_id = select_latest_hypothesis_reviews(reviews)
        lifecycle_recommendations = recommend_hypothesis_lifecycle_actions(
            hypotheses=hypotheses,
            evidence_summaries=evidence_summaries,
            latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
        )

        return build_research_plan(
            symbol="NVDA",
            hypotheses=hypotheses,
            experiment_requests=experiment_requests,
            experiment_results=experiment_results,
            evidence_summaries=evidence_summaries,
            latest_reviews_by_hypothesis_id=latest_reviews_by_hypothesis_id,
            lifecycle_recommendations=lifecycle_recommendations,
            revision_proposals=proposals,
            revision_applications=applications,
        )

    def test_child_hypothesis_without_completed_experiments_recommends_experiment_request(self):
        child = Hypothesis(
            hypothesis_id="hyp-child-001",
            symbol="NVDA",
            title="Child hypothesis",
            description="Child description.",
            parent_hypothesis_id="hyp-parent-001",
            lineage_hypothesis_ids=("hyp-parent-001",),
            source_revision_proposal_id="hyprevp-001",
        )

        plan = self._build_plan([child])

        self.assertEqual(1, len(plan.items))
        item = plan.items[0]
        self.assertEqual(ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST, item.recommended_action)
        self.assertEqual(ResearchPlanPriority.HIGH, item.priority)
        self.assertEqual("child hypothesis has not been tested yet", item.reason)

    def test_parent_with_applied_child_recommends_skip_parent_refined(self):
        parent = Hypothesis(
            hypothesis_id="hyp-parent-001",
            symbol="NVDA",
            title="Parent hypothesis",
            description="Parent description.",
            status=HypothesisStatus.ACTIVE,
        )
        child = Hypothesis(
            hypothesis_id="hyp-child-001",
            symbol="NVDA",
            title="Child hypothesis",
            description="Child description.",
            parent_hypothesis_id="hyp-parent-001",
            lineage_hypothesis_ids=("hyp-parent-001",),
            source_revision_proposal_id="hyprevp-001",
            created_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
        )
        proposal = HypothesisRevisionProposal(
            proposal_id="hyprevp-001",
            symbol="NVDA",
            parent_hypothesis_id="hyp-parent-001",
            source_review_id=None,
            lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
            proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
            proposed_title="Child hypothesis",
            proposed_description="Child description.",
            rationale="Refine parent into a child.",
            confidence=0.7,
            created_at=datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc),
        )
        application = HypothesisRevisionApplication(
            application_id="hypreva-001",
            proposal_id="hyprevp-001",
            symbol="NVDA",
            parent_hypothesis_id="hyp-parent-001",
            status=HypothesisRevisionApplicationStatus.APPLIED,
            apply_mode=True,
            child_hypothesis_id="hyp-child-001",
            message="proposal applied",
            created_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
        )

        plan = self._build_plan([parent, child], proposals=[proposal], applications=[application])

        parent_item = next(item for item in plan.items if item.hypothesis_id == "hyp-parent-001")
        self.assertEqual(ResearchPlanAction.SKIP_PARENT_REFINED, parent_item.recommended_action)
        self.assertEqual(ResearchPlanPriority.LOW, parent_item.priority)
        self.assertEqual("hyp-child-001", parent_item.related_child_hypothesis_id)

    def test_refine_candidate_without_proposal_recommends_revision_proposal(self):
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Refine candidate",
            description="Needs narrower setup.",
        )
        results = [
            ExperimentResult(
                experiment_result_id="expr-001",
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
                metrics=ExperimentMetrics(
                    trade_count=0,
                    average_return=0.0,
                    win_rate=0.0,
                ),
                created_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
                updated_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
            ),
            ExperimentResult(
                experiment_result_id="expr-002",
                experiment_request_id="expreq-002",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 8, 2, 0, 20, tzinfo=timezone.utc),
                metrics=ExperimentMetrics(
                    trade_count=0,
                    average_return=0.0,
                    win_rate=0.0,
                ),
                created_at=datetime(2026, 8, 2, 0, 20, tzinfo=timezone.utc),
                updated_at=datetime(2026, 8, 2, 0, 20, tzinfo=timezone.utc),
            ),
        ]
        reviews = [
            HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.REFINE,
                rationale="Zero-trade outcomes suggest narrowing the setup.",
                confidence=0.7,
                created_at=datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc),
            )
        ]

        plan = self._build_plan([hypothesis], experiment_results=results, reviews=reviews)

        item = plan.items[0]
        self.assertEqual(ResearchPlanAction.GENERATE_REVISION_PROPOSAL, item.recommended_action)
        self.assertEqual(ResearchPlanPriority.HIGH, item.priority)
        self.assertEqual(HypothesisLifecycleAction.REFINE_CANDIDATE, item.lifecycle_action)

    def test_refine_candidate_with_proposal_but_no_application_recommends_apply_candidate(self):
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Refine candidate",
            description="Needs narrower setup.",
        )
        results = [
            ExperimentResult(
                experiment_result_id="expr-001",
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
                metrics=ExperimentMetrics(
                    trade_count=0,
                    average_return=0.0,
                    win_rate=0.0,
                ),
                created_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
                updated_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
            ),
            ExperimentResult(
                experiment_result_id="expr-002",
                experiment_request_id="expreq-002",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 8, 2, 0, 20, tzinfo=timezone.utc),
                metrics=ExperimentMetrics(
                    trade_count=0,
                    average_return=0.0,
                    win_rate=0.0,
                ),
                created_at=datetime(2026, 8, 2, 0, 20, tzinfo=timezone.utc),
                updated_at=datetime(2026, 8, 2, 0, 20, tzinfo=timezone.utc),
            ),
        ]
        reviews = [
            HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.REFINE,
                rationale="Zero-trade outcomes suggest narrowing the setup.",
                confidence=0.7,
                created_at=datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc),
            )
        ]
        proposal = HypothesisRevisionProposal(
            proposal_id="hyprevp-001",
            symbol="NVDA",
            parent_hypothesis_id="hyp-001",
            source_review_id="hyprev-001",
            lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
            proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
            proposed_title="Refined candidate",
            proposed_description="Refined description.",
            rationale="Need a narrower setup.",
            confidence=0.72,
            created_at=datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc),
        )

        plan = self._build_plan([hypothesis], experiment_results=results, reviews=reviews, proposals=[proposal])

        item = plan.items[0]
        self.assertEqual(ResearchPlanAction.APPLY_REVISION_PROPOSAL_CANDIDATE, item.recommended_action)
        self.assertEqual(ResearchPlanPriority.MEDIUM, item.priority)
        self.assertEqual("hyprevp-001", item.related_proposal_id)

    def test_needs_more_tests_without_experiment_request_recommends_experiment_request(self):
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Needs more tests",
            description="Needs additional evidence.",
        )
        results = [
            ExperimentResult(
                experiment_result_id="expr-001",
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
                metrics=ExperimentMetrics(
                    trade_count=10,
                    average_return=0.01,
                    win_rate=0.5,
                ),
                created_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
                updated_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
            )
        ]
        reviews = [
            HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.NEEDS_MORE_TESTS,
                rationale="Need a broader sample.",
                confidence=0.55,
                created_at=datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc),
            )
        ]

        plan = self._build_plan([hypothesis], experiment_results=results, reviews=reviews)

        item = plan.items[0]
        self.assertEqual(ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST, item.recommended_action)
        self.assertEqual(ResearchPlanPriority.MEDIUM, item.priority)

    def test_needs_more_tests_with_existing_executable_request_recommends_no_action(self):
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Needs more tests",
            description="Needs additional evidence.",
        )
        results = [
            ExperimentResult(
                experiment_result_id="expr-001",
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
                metrics=ExperimentMetrics(
                    trade_count=10,
                    average_return=0.01,
                    win_rate=0.5,
                ),
                created_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
                updated_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
            )
        ]
        reviews = [
            HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.NEEDS_MORE_TESTS,
                rationale="Need a broader sample.",
                confidence=0.55,
                created_at=datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc),
            )
        ]
        request = ExperimentRequest(
            experiment_request_id="expreq-002",
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

        plan = self._build_plan([hypothesis], experiment_requests=[request], experiment_results=results, reviews=reviews)

        item = plan.items[0]
        self.assertEqual(ResearchPlanAction.NO_ACTION, item.recommended_action)
        self.assertEqual(ResearchPlanPriority.LOW, item.priority)

    def test_completed_result_newer_than_latest_review_recommends_hypothesis_review(self):
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Needs review",
            description="Has new evidence.",
        )
        results = [
            ExperimentResult(
                experiment_result_id="expr-001",
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 8, 3, 0, 20, tzinfo=timezone.utc),
                metrics=ExperimentMetrics(
                    trade_count=25,
                    average_return=0.02,
                    win_rate=0.6,
                ),
                created_at=datetime(2026, 8, 3, 0, 20, tzinfo=timezone.utc),
                updated_at=datetime(2026, 8, 3, 0, 20, tzinfo=timezone.utc),
            )
        ]
        reviews = [
            HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.KEEP,
                rationale="Older review.",
                confidence=0.5,
                created_at=datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc),
            )
        ]

        plan = self._build_plan([hypothesis], experiment_results=results, reviews=reviews)

        item = plan.items[0]
        self.assertEqual(ResearchPlanAction.GENERATE_HYPOTHESIS_REVIEW, item.recommended_action)
        self.assertEqual(ResearchPlanPriority.MEDIUM, item.priority)

    def test_child_with_reviewed_completed_experiments_recommends_monitor_existing_child(self):
        child = Hypothesis(
            hypothesis_id="hyp-child-001",
            symbol="NVDA",
            title="Child hypothesis",
            description="Child description.",
            parent_hypothesis_id="hyp-parent-001",
            lineage_hypothesis_ids=("hyp-parent-001",),
            source_revision_proposal_id="hyprevp-001",
        )
        results = [
            ExperimentResult(
                experiment_result_id="expr-001",
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-child-001",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc),
                completed_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
                metrics=ExperimentMetrics(
                    trade_count=30,
                    average_return=0.01,
                    win_rate=0.55,
                ),
                created_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
                updated_at=datetime(2026, 8, 1, 0, 20, tzinfo=timezone.utc),
            )
        ]
        reviews = [
            HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-child-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.KEEP,
                rationale="Current framing is still adequate.",
                confidence=0.6,
                created_at=datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc),
            )
        ]

        plan = self._build_plan([child], experiment_results=results, reviews=reviews)

        item = plan.items[0]
        self.assertEqual(ResearchPlanAction.MONITOR_EXISTING_CHILD, item.recommended_action)
        self.assertEqual(ResearchPlanPriority.LOW, item.priority)

    def test_planning_does_not_mutate_hypothesis(self):
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Untested hypothesis",
            description="Still untouched.",
            status=HypothesisStatus.ACTIVE,
            confidence=0.25,
        )
        original_status = hypothesis.status
        original_confidence = hypothesis.confidence

        plan = self._build_plan([hypothesis])

        self.assertEqual(original_status, hypothesis.status)
        self.assertEqual(original_confidence, hypothesis.confidence)
        self.assertEqual(1, len(plan.items))


if __name__ == "__main__":
    unittest.main()
