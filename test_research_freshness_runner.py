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
from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_revision_proposal import HypothesisRevisionProposal
from research.hypothesis_revision_proposal import HypothesisRevisionProposalType
from research.observation import Observation
from research.research_freshness import ProposalFreshnessStatus
from research.research_freshness import ReviewFreshnessStatus
from research.runner import DEFAULT_SYMBOL
from research.runner import run_manual_research_freshness


class ManualResearchFreshnessRunnerTests(unittest.TestCase):
    def _build_storage(
        self,
        *,
        hypotheses,
        observations=None,
        experiment_requests=None,
        experiment_results=None,
        hypothesis_reviews=None,
        revision_proposals=None,
    ):
        storage = Mock()
        storage.load_hypotheses.return_value = hypotheses
        storage.load_observations.return_value = observations or []
        storage.load_experiment_requests.return_value = experiment_requests or []
        storage.load_experiment_results.return_value = experiment_results or []
        storage.load_hypothesis_reviews.return_value = hypothesis_reviews or []
        storage.load_hypothesis_revision_proposals.return_value = revision_proposals or []
        storage.load_hypothesis_revision_applications.return_value = []
        return storage

    def _build_executable_request(self, *, experiment_request_id, hypothesis_id):
        return ExperimentRequest(
            experiment_request_id=experiment_request_id,
            hypothesis_id=hypothesis_id,
            hypothesis_version_id=f"{hypothesis_id}:v1",
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

    def _build_completed_result(
        self,
        *,
        experiment_request_id,
        hypothesis_id,
        completed_at,
        trade_count=4,
    ):
        return ExperimentResult(
            experiment_result_id=f"expr-{experiment_request_id}",
            experiment_request_id=experiment_request_id,
            hypothesis_id=hypothesis_id,
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=completed_at,
            completed_at=completed_at,
            metrics=ExperimentMetrics(trade_count=trade_count, average_return=0.01, win_rate=0.6),
            summary="Completed",
            created_at=completed_at,
            updated_at=completed_at,
        )

    def test_command_dispatches_and_is_read_only(self):
        now = datetime.now(timezone.utc)
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Parent",
            description="Parent hypothesis.",
            status=HypothesisStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        storage = self._build_storage(hypotheses=[hypothesis])

        with patch("builtins.print") as mock_print:
            items = run_manual_research_freshness(symbol="NVDA", storage=storage)

        self.assertEqual(1, len(items))
        mock_print.assert_any_call("Manual Research Freshness: NVDA")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Hypotheses Loaded : 1")
        mock_print.assert_any_call("Freshness Items : 1")
        mock_print.assert_any_call("Research Freshness")
        mock_print.assert_any_call("Freshness Summary")
        mock_print.assert_any_call("Suggested Next Commands")
        mock_print.assert_any_call("Research freshness read complete. No records were modified.")

        storage.save_hypotheses.assert_not_called()
        storage.save_experiment_requests.assert_not_called()
        storage.save_experiment_results.assert_not_called()
        storage.save_hypothesis_reviews.assert_not_called()
        storage.save_hypothesis_revision_proposals.assert_not_called()
        storage.save_hypothesis_revision_applications.assert_not_called()

    def test_review_freshness_missing_when_completed_result_exists_without_review(self):
        now = datetime.now(timezone.utc)
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Parent",
            description="Parent hypothesis.",
            status=HypothesisStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        request = self._build_executable_request(experiment_request_id="expreq-001", hypothesis_id="hyp-001")
        result = self._build_completed_result(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            completed_at=now,
        )
        storage = self._build_storage(
            hypotheses=[hypothesis],
            experiment_requests=[request],
            experiment_results=[result],
        )

        with patch("builtins.print") as mock_print:
            run_manual_research_freshness(symbol="NVDA", storage=storage)

        mock_print.assert_any_call("- hyp-001 review_freshness=missing proposal_freshness=not_applicable")
        mock_print.assert_any_call("  rationale: completed experiment results exist without a review")
        mock_print.assert_any_call("- missing : 1")

    def test_review_freshness_stale_after_new_result_when_result_newer_than_review(self):
        observation_time = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
        review_time = datetime(2026, 8, 4, 13, 0, tzinfo=timezone.utc)
        result_time = datetime(2026, 8, 4, 14, 0, tzinfo=timezone.utc)
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Parent",
            description="Parent hypothesis.",
            status=HypothesisStatus.ACTIVE,
            created_at=review_time,
            updated_at=review_time,
        )
        observation = Observation(
            observation_id="obs-001",
            symbol_id="NVDA",
            statement="Observation",
            evidence_refs=["snapshot-001"],
            importance=1,
            effective_time=observation_time.isoformat(),
            created_at=observation_time.isoformat(),
            research_cycle_id="cycle-001",
            ai_call_id="ai-001",
            schema_version="1.0",
            duplicate_of=None,
        )
        request = self._build_executable_request(experiment_request_id="expreq-001", hypothesis_id="hyp-001")
        result = self._build_completed_result(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            completed_at=result_time,
        )
        review = HypothesisReview(
            review_id="hyprev-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            recommendation=HypothesisReviewRecommendation.KEEP,
            rationale="Keep.",
            confidence=0.6,
            created_at=review_time,
        )
        storage = self._build_storage(
            hypotheses=[hypothesis],
            observations=[observation],
            experiment_requests=[request],
            experiment_results=[result],
            hypothesis_reviews=[review],
        )

        with patch("builtins.print") as mock_print:
            run_manual_research_freshness(symbol="NVDA", storage=storage)

        mock_print.assert_any_call(
            "- hyp-001 review_freshness=stale_after_new_result proposal_freshness=not_applicable"
        )
        mock_print.assert_any_call(
            "  rationale: latest completed result is newer than the latest review"
        )

    def test_review_freshness_stale_after_new_observation_when_observation_newer_than_review_and_no_result(self):
        review_time = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
        observation_time = datetime(2026, 8, 4, 13, 0, tzinfo=timezone.utc)
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Parent",
            description="Parent hypothesis.",
            status=HypothesisStatus.ACTIVE,
            created_at=review_time,
            updated_at=review_time,
        )
        observation = Observation(
            observation_id="obs-001",
            symbol_id="NVDA",
            statement="Observation",
            evidence_refs=["snapshot-001"],
            importance=1,
            effective_time=observation_time.isoformat(),
            created_at=observation_time.isoformat(),
            research_cycle_id="cycle-001",
            ai_call_id="ai-001",
            schema_version="1.0",
            duplicate_of=None,
        )
        review = HypothesisReview(
            review_id="hyprev-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            recommendation=HypothesisReviewRecommendation.KEEP,
            rationale="Keep.",
            confidence=0.6,
            created_at=review_time,
        )
        storage = self._build_storage(
            hypotheses=[hypothesis],
            observations=[observation],
            hypothesis_reviews=[review],
        )

        with patch("builtins.print") as mock_print:
            run_manual_research_freshness(symbol="NVDA", storage=storage)

        mock_print.assert_any_call(
            "- hyp-001 review_freshness=stale_after_new_observation proposal_freshness=not_applicable"
        )
        mock_print.assert_any_call(
            "  rationale: latest observation is newer than the latest review"
        )

    def test_review_freshness_current_when_review_is_newest(self):
        observation_time = datetime(2026, 8, 4, 11, 0, tzinfo=timezone.utc)
        review_time = datetime(2026, 8, 4, 13, 0, tzinfo=timezone.utc)
        result_time = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Parent",
            description="Parent hypothesis.",
            status=HypothesisStatus.ACTIVE,
            created_at=review_time,
            updated_at=review_time,
        )
        observation = Observation(
            observation_id="obs-001",
            symbol_id="NVDA",
            statement="Observation",
            evidence_refs=["snapshot-001"],
            importance=1,
            effective_time=observation_time.isoformat(),
            created_at=observation_time.isoformat(),
            research_cycle_id="cycle-001",
            ai_call_id="ai-001",
            schema_version="1.0",
            duplicate_of=None,
        )
        request = self._build_executable_request(experiment_request_id="expreq-001", hypothesis_id="hyp-001")
        result = self._build_completed_result(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            completed_at=result_time,
        )
        review = HypothesisReview(
            review_id="hyprev-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            recommendation=HypothesisReviewRecommendation.KEEP,
            rationale="Keep.",
            confidence=0.6,
            created_at=review_time,
        )
        storage = self._build_storage(
            hypotheses=[hypothesis],
            observations=[observation],
            experiment_requests=[request],
            experiment_results=[result],
            hypothesis_reviews=[review],
        )

        with patch("builtins.print") as mock_print:
            run_manual_research_freshness(symbol="NVDA", storage=storage)

        mock_print.assert_any_call("- hyp-001 review_freshness=current proposal_freshness=not_applicable")

    def test_proposal_freshness_missing_for_refine_candidate_when_no_proposal_exists(self):
        now = datetime.now(timezone.utc)
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Parent",
            description="Parent hypothesis.",
            status=HypothesisStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        first_result = self._build_completed_result(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            completed_at=now,
            trade_count=0,
        )
        second_result = self._build_completed_result(
            experiment_request_id="expreq-002",
            hypothesis_id="hyp-001",
            completed_at=now,
            trade_count=0,
        )
        storage = self._build_storage(
            hypotheses=[hypothesis],
            experiment_requests=[
                self._build_executable_request(experiment_request_id="expreq-001", hypothesis_id="hyp-001"),
                self._build_executable_request(experiment_request_id="expreq-002", hypothesis_id="hyp-001"),
            ],
            experiment_results=[first_result, second_result],
        )

        with patch("builtins.print") as mock_print:
            run_manual_research_freshness(symbol="NVDA", storage=storage)

        mock_print.assert_any_call(
            "- hyp-001 review_freshness=missing proposal_freshness=missing_for_refine_candidate"
        )

    def test_proposal_freshness_stale_after_review_when_review_newer_than_proposal(self):
        review_time = datetime(2026, 8, 4, 14, 0, tzinfo=timezone.utc)
        proposal_time = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Parent",
            description="Parent hypothesis.",
            status=HypothesisStatus.ACTIVE,
            created_at=review_time,
            updated_at=review_time,
        )
        proposal = HypothesisRevisionProposal(
            proposal_id="hyprevp-001",
            symbol="NVDA",
            parent_hypothesis_id="hyp-001",
            source_review_id="hyprev-001",
            lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
            proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
            proposed_title="Refined",
            proposed_description="Refined description",
            rationale="Refinement rationale",
            confidence=0.6,
            created_at=proposal_time,
        )
        review = HypothesisReview(
            review_id="hyprev-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            recommendation=HypothesisReviewRecommendation.REFINE,
            rationale="Refine.",
            confidence=0.6,
            created_at=review_time,
        )
        storage = self._build_storage(
            hypotheses=[hypothesis],
            hypothesis_reviews=[review],
            revision_proposals=[proposal],
            experiment_requests=[
                self._build_executable_request(experiment_request_id="expreq-001", hypothesis_id="hyp-001"),
                self._build_executable_request(experiment_request_id="expreq-002", hypothesis_id="hyp-001"),
            ],
            experiment_results=[
                self._build_completed_result(
                    experiment_request_id="expreq-001",
                    hypothesis_id="hyp-001",
                    completed_at=proposal_time,
                    trade_count=0,
                ),
                self._build_completed_result(
                    experiment_request_id="expreq-002",
                    hypothesis_id="hyp-001",
                    completed_at=proposal_time,
                    trade_count=0,
                ),
            ],
        )

        with patch("builtins.print") as mock_print:
            run_manual_research_freshness(symbol="NVDA", storage=storage)

        mock_print.assert_any_call(
            "- hyp-001 review_freshness=current proposal_freshness=stale_after_review"
        )

    def test_proposal_freshness_current_when_proposal_is_current(self):
        review_time = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
        proposal_time = datetime(2026, 8, 4, 14, 0, tzinfo=timezone.utc)
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Parent",
            description="Parent hypothesis.",
            status=HypothesisStatus.ACTIVE,
            created_at=review_time,
            updated_at=review_time,
        )
        proposal = HypothesisRevisionProposal(
            proposal_id="hyprevp-001",
            symbol="NVDA",
            parent_hypothesis_id="hyp-001",
            source_review_id="hyprev-001",
            lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
            proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
            proposed_title="Refined",
            proposed_description="Refined description",
            rationale="Refinement rationale",
            confidence=0.6,
            created_at=proposal_time,
        )
        review = HypothesisReview(
            review_id="hyprev-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            recommendation=HypothesisReviewRecommendation.REFINE,
            rationale="Refine.",
            confidence=0.6,
            created_at=review_time,
        )
        storage = self._build_storage(
            hypotheses=[hypothesis],
            hypothesis_reviews=[review],
            revision_proposals=[proposal],
            experiment_requests=[
                self._build_executable_request(experiment_request_id="expreq-001", hypothesis_id="hyp-001"),
                self._build_executable_request(experiment_request_id="expreq-002", hypothesis_id="hyp-001"),
            ],
            experiment_results=[
                self._build_completed_result(
                    experiment_request_id="expreq-001",
                    hypothesis_id="hyp-001",
                    completed_at=proposal_time,
                    trade_count=0,
                ),
                self._build_completed_result(
                    experiment_request_id="expreq-002",
                    hypothesis_id="hyp-001",
                    completed_at=proposal_time,
                    trade_count=0,
                ),
            ],
        )

        with patch("builtins.print") as mock_print:
            run_manual_research_freshness(symbol="NVDA", storage=storage)

        mock_print.assert_any_call(
            "- hyp-001 review_freshness=stale_after_new_result proposal_freshness=current"
        )

    def test_suggested_commands_appear_for_stale_items_and_not_for_current_or_not_applicable(self):
        review_time = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
        result_time = datetime(2026, 8, 4, 13, 0, tzinfo=timezone.utc)
        proposal_time = datetime(2026, 8, 4, 11, 0, tzinfo=timezone.utc)
        stale_hypothesis = Hypothesis(
            hypothesis_id="hyp-stale-001",
            symbol="NVDA",
            title="Stale",
            description="Stale hypothesis.",
            status=HypothesisStatus.ACTIVE,
            created_at=review_time,
            updated_at=review_time,
        )
        fresh_hypothesis = Hypothesis(
            hypothesis_id="hyp-fresh-001",
            symbol="NVDA",
            title="Fresh",
            description="Fresh hypothesis.",
            status=HypothesisStatus.ACTIVE,
            created_at=review_time,
            updated_at=review_time,
        )
        not_applicable_hypothesis = Hypothesis(
            hypothesis_id="hyp-na-001",
            symbol="NVDA",
            title="No action",
            description="No action.",
            status=HypothesisStatus.ACTIVE,
            created_at=review_time,
            updated_at=review_time,
        )
        stale_result = self._build_completed_result(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-stale-001",
            completed_at=result_time,
            trade_count=0,
        )
        stale_result_two = self._build_completed_result(
            experiment_request_id="expreq-003",
            hypothesis_id="hyp-stale-001",
            completed_at=result_time,
            trade_count=0,
        )
        fresh_result = self._build_completed_result(
            experiment_request_id="expreq-002",
            hypothesis_id="hyp-fresh-001",
            completed_at=result_time,
            trade_count=4,
        )
        observation = Observation(
            observation_id="obs-001",
            symbol_id="NVDA",
            statement="Observation",
            evidence_refs=["snapshot-001"],
            importance=1,
            effective_time=review_time.isoformat(),
            created_at=review_time.isoformat(),
            research_cycle_id="cycle-001",
            ai_call_id="ai-001",
            schema_version="1.0",
            duplicate_of=None,
        )
        review = HypothesisReview(
            review_id="hyprev-001",
            hypothesis_id="hyp-stale-001",
            symbol="NVDA",
            recommendation=HypothesisReviewRecommendation.KEEP,
            rationale="Keep.",
            confidence=0.6,
            created_at=review_time,
        )
        proposal = HypothesisRevisionProposal(
            proposal_id="hyprevp-001",
            symbol="NVDA",
            parent_hypothesis_id="hyp-stale-001",
            source_review_id="hyprev-001",
            lifecycle_action=HypothesisLifecycleAction.REFINE_CANDIDATE,
            proposal_type=HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
            proposed_title="Refined",
            proposed_description="Refined description",
            rationale="Refinement rationale",
            confidence=0.6,
            created_at=proposal_time,
        )
        storage = self._build_storage(
            hypotheses=[stale_hypothesis, fresh_hypothesis, not_applicable_hypothesis],
            observations=[observation],
            experiment_requests=[
                self._build_executable_request(experiment_request_id="expreq-001", hypothesis_id="hyp-stale-001"),
                self._build_executable_request(experiment_request_id="expreq-003", hypothesis_id="hyp-stale-001"),
                self._build_executable_request(experiment_request_id="expreq-002", hypothesis_id="hyp-fresh-001"),
            ],
            experiment_results=[stale_result, stale_result_two, fresh_result],
            hypothesis_reviews=[review],
            revision_proposals=[proposal],
        )

        with patch("builtins.print") as mock_print:
            run_manual_research_freshness(symbol="NVDA", storage=storage)

        mock_print.assert_any_call(
            "- python -m research.runner research-cycle NVDA --reviews"
        )
        mock_print.assert_any_call(
            "- python -m research.runner research-cycle NVDA --revisions"
        )

    def test_no_suggested_commands_when_all_current_or_not_applicable(self):
        now = datetime.now(timezone.utc)
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Current",
            description="Current hypothesis.",
            status=HypothesisStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        review = HypothesisReview(
            review_id="hyprev-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            recommendation=HypothesisReviewRecommendation.KEEP,
            rationale="Keep.",
            confidence=0.6,
            created_at=now,
        )
        proposal = HypothesisRevisionProposal(
            proposal_id="hyprevp-001",
            symbol="NVDA",
            parent_hypothesis_id="hyp-001",
            source_review_id="hyprev-001",
            lifecycle_action=HypothesisLifecycleAction.NO_ACTION,
            proposal_type=HypothesisRevisionProposalType.NO_REVISION,
            proposed_title="",
            proposed_description="",
            rationale="No revision needed",
            confidence=0.5,
            created_at=now,
        )
        storage = self._build_storage(
            hypotheses=[hypothesis],
            hypothesis_reviews=[review],
            revision_proposals=[proposal],
            experiment_requests=[
                self._build_executable_request(experiment_request_id="expreq-001", hypothesis_id="hyp-001"),
                self._build_executable_request(experiment_request_id="expreq-002", hypothesis_id="hyp-001"),
            ],
            experiment_results=[
                self._build_completed_result(
                    experiment_request_id="expreq-001",
                    hypothesis_id="hyp-001",
                    completed_at=now,
                    trade_count=0,
                ),
                self._build_completed_result(
                    experiment_request_id="expreq-002",
                    hypothesis_id="hyp-001",
                    completed_at=now,
                    trade_count=0,
                ),
            ],
        )

        with patch("builtins.print") as mock_print:
            run_manual_research_freshness(symbol="NVDA", storage=storage)

        mock_print.assert_any_call("No suggested follow-up commands from current freshness state.")

    def test_runner_uses_default_symbol_when_omitted(self):
        storage = self._build_storage(hypotheses=[])

        with patch("builtins.print"):
            items = run_manual_research_freshness(storage=storage)

        self.assertEqual([], items)
        self.assertEqual(DEFAULT_SYMBOL, "NVDA")


if __name__ == "__main__":
    unittest.main()
