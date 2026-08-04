import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from ai.hypothesis_revision_service import HypothesisRevisionService
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


class HypothesisRevisionServiceTests(unittest.TestCase):
    def test_generate_for_symbol_calls_ai_parses_and_saves(self):
        ai_client = Mock()
        storage = Mock()
        journal_builder = Mock()
        journal_builder.build.return_value = "Research Journal: NVDA"

        ai_client.hypothesis_revision_proposals.return_value = """
        {
            "hypothesis_revision_proposals": [
                {
                    "proposal_id": "hyprevp-001",
                    "symbol": "NVDA",
                    "parent_hypothesis_id": "hyp-001",
                    "source_review_id": "hyprev-001",
                    "lifecycle_action": "refine_candidate",
                    "proposal_type": "create_child_hypothesis",
                    "proposed_title": "Refined momentum setup",
                    "proposed_description": "Refine by adding trend-strength filter.",
                    "rationale": "Repeated zero-trade outcomes justify narrower setup.",
                    "confidence": 0.74,
                    "created_at": "2026-08-04T00:00:00+00:00"
                }
            ]
        }
        """

        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Momentum continuation",
            description="Test whether momentum persists.",
            status=HypothesisStatus.ACTIVE,
            confidence=0.68,
        )

        now = datetime(2026, 8, 4, 0, 0, tzinfo=timezone.utc)
        request = ExperimentRequest(
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
        result = ExperimentResult(
            experiment_result_id="expr-001",
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(
                trade_count=0,
                average_return=0.0,
                win_rate=0.0,
            ),
            summary="Completed",
            created_at=now,
            updated_at=now,
        )
        second_result = ExperimentResult(
            experiment_result_id="expr-002",
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            metrics=ExperimentMetrics(
                trade_count=0,
                average_return=0.0,
                win_rate=0.0,
            ),
            summary="Completed",
            created_at=now,
            updated_at=now,
        )
        review = HypothesisReview(
            review_id="hyprev-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            recommendation=HypothesisReviewRecommendation.REFINE,
            rationale="Refine setup.",
            confidence=0.62,
            created_at=now,
        )

        storage.load_hypotheses.return_value = [hypothesis]
        storage.load_experiment_requests.return_value = [request]
        storage.load_experiment_results.return_value = [result, second_result]
        storage.load_hypothesis_reviews.return_value = [review]

        service = HypothesisRevisionService(
            ai_client=ai_client,
            storage=storage,
            journal_builder=journal_builder,
        )

        proposals = service.generate_for_symbol(symbol="NVDA")

        self.assertEqual(1, len(proposals))
        self.assertIsInstance(proposals[0], HypothesisRevisionProposal)
        self.assertEqual("hyprevp-001", proposals[0].proposal_id)
        self.assertEqual(HypothesisLifecycleAction.REFINE_CANDIDATE, proposals[0].lifecycle_action)
        self.assertEqual(
            HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS,
            proposals[0].proposal_type,
        )

        journal_builder.build.assert_called_once_with("NVDA")
        ai_client.hypothesis_revision_proposals.assert_called_once()
        storage.save_hypothesis_revision_proposals.assert_called_once_with("NVDA", proposals)

        call_kwargs = ai_client.hypothesis_revision_proposals.call_args.kwargs
        self.assertEqual("NVDA", call_kwargs["symbol"])
        self.assertEqual("Research Journal: NVDA", call_kwargs["journal"])
        self.assertIn("hyp-001", call_kwargs["hypotheses"])
        self.assertIn("refine_candidate", call_kwargs["lifecycle_recommendations"])

    def test_generate_for_symbol_skips_ai_when_no_eligible_recommendations(self):
        ai_client = Mock()
        storage = Mock()
        journal_builder = Mock()

        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Momentum continuation",
            description="Test whether momentum persists.",
            status=HypothesisStatus.ACTIVE,
            confidence=0.68,
        )
        storage.load_hypotheses.return_value = [hypothesis]
        storage.load_experiment_requests.return_value = []
        storage.load_experiment_results.return_value = []
        storage.load_hypothesis_reviews.return_value = []

        service = HypothesisRevisionService(
            ai_client=ai_client,
            storage=storage,
            journal_builder=journal_builder,
        )

        proposals = service.generate_for_symbol(symbol="NVDA")

        self.assertEqual([], proposals)
        ai_client.hypothesis_revision_proposals.assert_not_called()
        journal_builder.build.assert_not_called()
        storage.save_hypothesis_revision_proposals.assert_not_called()


if __name__ == "__main__":
    unittest.main()
