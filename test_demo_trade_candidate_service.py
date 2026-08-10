import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from ai.demo_trade_candidate_service import DemoTradeCandidateService
from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import DemoTradeCandidateStatus
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


class DemoTradeCandidateServiceTests(unittest.TestCase):
    def _build_executable_request(self, hypothesis_id: str) -> ExperimentRequest:
        return ExperimentRequest(
            experiment_request_id=f"expreq-{hypothesis_id}",
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
        hypothesis_id: str,
        experiment_request_id: str,
        completed_at: datetime,
        trade_count: int,
        average_return: float,
        win_rate: float,
    ) -> ExperimentResult:
        return ExperimentResult(
            experiment_result_id=f"expr-{hypothesis_id}-{completed_at.hour}",
            experiment_request_id=experiment_request_id,
            hypothesis_id=hypothesis_id,
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            status=ExperimentResultStatus.COMPLETED,
            started_at=completed_at,
            completed_at=completed_at,
            metrics=ExperimentMetrics(
                trade_count=trade_count,
                average_return=average_return,
                win_rate=win_rate,
            ),
            summary="Completed",
            created_at=completed_at,
            updated_at=completed_at,
        )

    def _build_existing_candidate(self, trade_candidate_id: str, source_hypothesis_id: str, status):
        return DemoTradeCandidate(
            trade_candidate_id=trade_candidate_id,
            symbol="NVDA",
            source_hypothesis_id=source_hypothesis_id,
            source_research_candidate_decision="candidate",
            created_at=datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc),
            status=status,
            entry_logic="Enter on breakout close above prior range.",
            exit_logic="Exit on trailing stop or target.",
            invalidation_logic="Invalidate on range breakdown.",
            maximum_holding_period="5D",
            position_sizing_rule="Risk 50 bps of equity.",
            max_loss_per_trade=0.01,
            max_portfolio_exposure=0.05,
            demo_only=True,
            monitoring_frequency="15m",
            pause_conditions=("halted_market",),
            source_evidence_summary={"completed_experiments": 2},
            source_review_action="keep",
            source_review_confidence=0.72,
            risk_flags=("limited_experiment_count",),
            created_by="ai",
        )

    def test_generate_for_symbol_calls_ai_validates_and_saves(self):
        ai_client = Mock()
        storage = Mock()
        journal_builder = Mock()
        journal_builder.build.return_value = "Research Journal: NVDA"

        now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
        hypothesis = Hypothesis(
            hypothesis_id="hyp-NVDA-002",
            symbol="NVDA",
            title="Candidate hypothesis",
            description="Promising and reviewed.",
            status=HypothesisStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        storage.load_hypotheses.return_value = [hypothesis]
        storage.load_observations.return_value = []
        storage.load_experiment_requests.return_value = [
            self._build_executable_request("hyp-NVDA-002"),
        ]
        storage.load_experiment_results.return_value = [
            self._build_completed_result(
                hypothesis_id="hyp-NVDA-002",
                experiment_request_id="expreq-hyp-NVDA-002",
                completed_at=now - timedelta(hours=2),
                trade_count=80,
                average_return=0.02,
                win_rate=0.65,
            ),
            self._build_completed_result(
                hypothesis_id="hyp-NVDA-002",
                experiment_request_id="expreq-hyp-NVDA-002",
                completed_at=now - timedelta(hours=1),
                trade_count=80,
                average_return=0.021,
                win_rate=0.67,
            ),
        ]
        storage.load_hypothesis_reviews.return_value = [
            HypothesisReview(
                review_id="hyprev-002",
                hypothesis_id="hyp-NVDA-002",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.KEEP,
                rationale="Keep.",
                confidence=0.7,
                created_at=now,
            ),
        ]
        storage.load_hypothesis_revision_proposals.return_value = []
        storage.load_demo_trade_candidates.return_value = []

        ai_client.demo_trade_candidate_generation.return_value = """
        {
            "demo_trade_candidates": [
                {
                    "symbol": "NVDA",
                    "source_hypothesis_id": "hyp-NVDA-002",
                    "source_research_candidate_decision": "candidate",
                    "status": "proposed",
                    "entry_logic": "Enter on breakout close above prior range.",
                    "exit_logic": "Exit on trailing stop or target.",
                    "invalidation_logic": "Invalidate on range breakdown.",
                    "maximum_holding_period": "5D",
                    "position_sizing_rule": "Risk 50 bps of equity.",
                    "max_loss_per_trade": 0.01,
                    "max_portfolio_exposure": 0.05,
                    "demo_only": true,
                    "monitoring_frequency": "15m",
                    "pause_conditions": ["halted_market"],
                    "source_evidence_summary": {"completed_experiments": 2},
                    "source_review_action": "keep",
                    "source_review_confidence": 0.7,
                    "risk_flags": ["limited_experiment_count"],
                    "created_by": "ai"
                }
            ]
        }
        """

        service = DemoTradeCandidateService(
            ai_client=ai_client,
            storage=storage,
            journal_builder=journal_builder,
        )

        result = service.generate_for_symbol("NVDA")

        self.assertEqual(1, result.research_candidates_loaded)
        self.assertEqual(1, result.generation_candidates)
        self.assertEqual(1, len(result.generated_candidates))
        self.assertEqual(0, result.skipped_existing)
        self.assertEqual(0, result.failed_validation)
        self.assertEqual("hyp-NVDA-002", result.generated_candidates[0].source_hypothesis_id)
        self.assertEqual(DemoTradeCandidateStatus.PROPOSED, result.generated_candidates[0].status)
        self.assertEqual(True, result.generated_candidates[0].demo_only)
        self.assertEqual("ai", result.generated_candidates[0].created_by)

        journal_builder.build.assert_called_once_with("NVDA")
        ai_client.demo_trade_candidate_generation.assert_called_once()
        storage.save_demo_trade_candidate.assert_called_once()

        call_kwargs = ai_client.demo_trade_candidate_generation.call_args.kwargs
        self.assertEqual("NVDA", call_kwargs["symbol"])
        self.assertEqual("Research Journal: NVDA", call_kwargs["journal"])
        self.assertIn("hyp-NVDA-002", call_kwargs["qualified_candidates"])

    def test_generate_for_symbol_skips_existing_active_candidate(self):
        ai_client = Mock()
        storage = Mock()
        journal_builder = Mock()

        now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
        hypothesis = Hypothesis(
            hypothesis_id="hyp-NVDA-002",
            symbol="NVDA",
            title="Candidate hypothesis",
            description="Promising and reviewed.",
            status=HypothesisStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        storage.load_hypotheses.return_value = [hypothesis]
        storage.load_observations.return_value = []
        storage.load_experiment_requests.return_value = [
            self._build_executable_request("hyp-NVDA-002"),
        ]
        storage.load_experiment_results.return_value = [
            self._build_completed_result(
                hypothesis_id="hyp-NVDA-002",
                experiment_request_id="expreq-hyp-NVDA-002",
                completed_at=now - timedelta(hours=2),
                trade_count=80,
                average_return=0.02,
                win_rate=0.65,
            ),
            self._build_completed_result(
                hypothesis_id="hyp-NVDA-002",
                experiment_request_id="expreq-hyp-NVDA-002",
                completed_at=now - timedelta(hours=1),
                trade_count=80,
                average_return=0.021,
                win_rate=0.67,
            ),
        ]
        storage.load_hypothesis_reviews.return_value = [
            HypothesisReview(
                review_id="hyprev-002",
                hypothesis_id="hyp-NVDA-002",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.KEEP,
                rationale="Keep.",
                confidence=0.7,
                created_at=now,
            ),
        ]
        storage.load_hypothesis_revision_proposals.return_value = []
        storage.load_demo_trade_candidates.return_value = [
            self._build_existing_candidate(
                trade_candidate_id="dtc-001",
                source_hypothesis_id="hyp-NVDA-002",
                status=DemoTradeCandidateStatus.PROPOSED,
            )
        ]

        service = DemoTradeCandidateService(
            ai_client=ai_client,
            storage=storage,
            journal_builder=journal_builder,
        )

        result = service.generate_for_symbol("NVDA")

        self.assertEqual(1, result.research_candidates_loaded)
        self.assertEqual(0, result.generation_candidates)
        self.assertEqual(0, len(result.generated_candidates))
        self.assertEqual(1, result.skipped_existing)
        self.assertEqual(0, result.failed_validation)
        ai_client.demo_trade_candidate_generation.assert_not_called()
        storage.save_demo_trade_candidate.assert_not_called()

    def test_generate_for_symbol_counts_validation_failures_without_saving(self):
        ai_client = Mock()
        storage = Mock()
        journal_builder = Mock()
        journal_builder.build.return_value = "Research Journal: NVDA"

        now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
        hypothesis = Hypothesis(
            hypothesis_id="hyp-NVDA-002",
            symbol="NVDA",
            title="Candidate hypothesis",
            description="Promising and reviewed.",
            status=HypothesisStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        storage.load_hypotheses.return_value = [hypothesis]
        storage.load_observations.return_value = []
        storage.load_experiment_requests.return_value = [
            self._build_executable_request("hyp-NVDA-002"),
        ]
        storage.load_experiment_results.return_value = [
            self._build_completed_result(
                hypothesis_id="hyp-NVDA-002",
                experiment_request_id="expreq-hyp-NVDA-002",
                completed_at=now - timedelta(hours=2),
                trade_count=80,
                average_return=0.02,
                win_rate=0.65,
            ),
            self._build_completed_result(
                hypothesis_id="hyp-NVDA-002",
                experiment_request_id="expreq-hyp-NVDA-002",
                completed_at=now - timedelta(hours=1),
                trade_count=80,
                average_return=0.021,
                win_rate=0.67,
            ),
        ]
        storage.load_hypothesis_reviews.return_value = [
            HypothesisReview(
                review_id="hyprev-002",
                hypothesis_id="hyp-NVDA-002",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.KEEP,
                rationale="Keep.",
                confidence=0.7,
                created_at=now,
            ),
        ]
        storage.load_hypothesis_revision_proposals.return_value = []
        storage.load_demo_trade_candidates.return_value = []

        ai_client.demo_trade_candidate_generation.return_value = """
        {
            "demo_trade_candidates": [
                {
                    "symbol": "NVDA",
                    "source_hypothesis_id": "hyp-NVDA-002",
                    "source_research_candidate_decision": "candidate",
                    "status": "proposed",
                    "entry_logic": "Enter on breakout close above prior range.",
                    "exit_logic": "Exit on trailing stop or target.",
                    "invalidation_logic": "Invalidate on range breakdown.",
                    "maximum_holding_period": "5D",
                    "position_sizing_rule": "Risk 50 bps of equity.",
                    "max_loss_per_trade": 0.03,
                    "max_portfolio_exposure": 0.05,
                    "demo_only": true,
                    "monitoring_frequency": "15m",
                    "pause_conditions": ["halted_market"],
                    "source_evidence_summary": {"completed_experiments": 2},
                    "source_review_action": "keep",
                    "source_review_confidence": 0.7,
                    "risk_flags": ["limited_experiment_count"],
                    "created_by": "ai"
                }
            ]
        }
        """

        service = DemoTradeCandidateService(
            ai_client=ai_client,
            storage=storage,
            journal_builder=journal_builder,
        )

        result = service.generate_for_symbol("NVDA")

        self.assertEqual(1, result.research_candidates_loaded)
        self.assertEqual(1, result.generation_candidates)
        self.assertEqual(0, len(result.generated_candidates))
        self.assertEqual(0, result.skipped_existing)
        self.assertEqual(1, result.failed_validation)
        storage.save_demo_trade_candidate.assert_not_called()


if __name__ == "__main__":
    unittest.main()