import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from research.experiment import ExperimentRequest, ExperimentRequestStatus, ExperimentTestType
from research.experiment_result import ExperimentMetrics, ExperimentResult, ExperimentResultStatus
from research.hypothesis import Hypothesis, HypothesisStatus
from research.hypothesis_review import HypothesisReview, HypothesisReviewRecommendation
from research.runner import DEFAULT_SYMBOL, run_manual_trade_candidate_proposals


class ManualTradeCandidateProposalRunnerTests(unittest.TestCase):
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

    def test_runner_outputs_read_only_trade_candidate_proposal_readiness(self):
        storage = Mock()
        now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)

        candidate = Hypothesis(
            hypothesis_id="hyp-NVDA-002",
            symbol="NVDA",
            title="Candidate hypothesis",
            description="Promising and reviewed.",
            status=HypothesisStatus.PROPOSED,
            created_at=now,
            updated_at=now,
        )
        not_candidate = Hypothesis(
            hypothesis_id="hyp-NVDA-005",
            symbol="NVDA",
            title="Mixed hypothesis",
            description="Mixed evidence.",
            status=HypothesisStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        storage.load_hypotheses.return_value = [candidate, not_candidate]
        storage.load_observations.return_value = []
        storage.load_experiment_requests.return_value = [
            self._build_executable_request("hyp-NVDA-002"),
            self._build_executable_request("hyp-NVDA-005"),
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
                average_return=0.0214,
                win_rate=0.675,
            ),
            self._build_completed_result(
                hypothesis_id="hyp-NVDA-005",
                experiment_request_id="expreq-hyp-NVDA-005",
                completed_at=now - timedelta(hours=3),
                trade_count=70,
                average_return=-0.0019,
                win_rate=0.5199,
            ),
            self._build_completed_result(
                hypothesis_id="hyp-NVDA-005",
                experiment_request_id="expreq-hyp-NVDA-005",
                completed_at=now - timedelta(hours=2, minutes=30),
                trade_count=73,
                average_return=-0.0019,
                win_rate=0.5199,
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
            HypothesisReview(
                review_id="hyprev-005",
                hypothesis_id="hyp-NVDA-005",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.NEEDS_MORE_TESTS,
                rationale="Needs more tests.",
                confidence=0.6,
                created_at=now,
            ),
        ]
        storage.load_hypothesis_revision_proposals.return_value = []
        storage.load_hypothesis_revision_applications.return_value = []

        with patch("builtins.print") as mock_print:
            readiness = run_manual_trade_candidate_proposals(symbol="NVDA", storage=storage)

        self.assertEqual(2, len(readiness))
        mock_print.assert_any_call("Manual Trade Candidate Proposals: NVDA")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Hypotheses Loaded : 2")
        mock_print.assert_any_call("Research Candidates Loaded : 1")
        mock_print.assert_any_call("Trade Candidate Proposals : 1")
        mock_print.assert_any_call("- hyp-NVDA-002 decision=proposal_ready")
        mock_print.assert_any_call("  source_decision=candidate")
        mock_print.assert_any_call(
            "  required_components=entry_logic, exit_logic, invalidation_logic, position_sizing, risk_limits, demo_parameters"
        )
        mock_print.assert_any_call(
            "  missing_components=entry_logic, exit_logic, invalidation_logic, position_sizing, risk_limits, demo_parameters"
        )
        mock_print.assert_any_call("- hyp-NVDA-005 decision=not_ready")
        mock_print.assert_any_call("  source_decision=not_candidate")
        mock_print.assert_any_call("Proposal Design Checklist")
        mock_print.assert_any_call("- hyp-NVDA-002")
        mock_print.assert_any_call("  - define entry trigger")
        mock_print.assert_any_call("  - define exit trigger")
        mock_print.assert_any_call("  - define invalidation condition")
        mock_print.assert_any_call("  - define maximum holding period")
        mock_print.assert_any_call("  - define position sizing rule")
        mock_print.assert_any_call("  - define max loss per trade")
        mock_print.assert_any_call("  - define max portfolio exposure")
        mock_print.assert_any_call("  - define demo-only enforcement")
        mock_print.assert_any_call("  - define monitoring frequency")
        mock_print.assert_any_call("  - define evidence conditions that would pause the setup")
        mock_print.assert_any_call("Trade candidate proposal is not approval to trade.")
        mock_print.assert_any_call(
            "Promotion comes only after demo-trading parameters/risk gates are defined and passed."
        )

        storage.save_hypotheses.assert_not_called()
        storage.save_experiment_requests.assert_not_called()
        storage.save_experiment_results.assert_not_called()
        storage.save_hypothesis_reviews.assert_not_called()
        storage.save_hypothesis_revision_proposals.assert_not_called()
        storage.save_hypothesis_revision_applications.assert_not_called()

    def test_runner_prints_stable_empty_checklist_message_when_no_proposals_are_ready(self):
        storage = Mock()
        now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
        not_candidate = Hypothesis(
            hypothesis_id="hyp-NVDA-005",
            symbol="NVDA",
            title="Mixed hypothesis",
            description="Mixed evidence.",
            status=HypothesisStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        storage.load_hypotheses.return_value = [not_candidate]
        storage.load_observations.return_value = []
        storage.load_experiment_requests.return_value = [
            self._build_executable_request("hyp-NVDA-005"),
        ]
        storage.load_experiment_results.return_value = [
            self._build_completed_result(
                hypothesis_id="hyp-NVDA-005",
                experiment_request_id="expreq-hyp-NVDA-005",
                completed_at=now - timedelta(hours=3),
                trade_count=70,
                average_return=-0.0019,
                win_rate=0.5199,
            ),
            self._build_completed_result(
                hypothesis_id="hyp-NVDA-005",
                experiment_request_id="expreq-hyp-NVDA-005",
                completed_at=now - timedelta(hours=2, minutes=30),
                trade_count=73,
                average_return=-0.0019,
                win_rate=0.5199,
            ),
        ]
        storage.load_hypothesis_reviews.return_value = [
            HypothesisReview(
                review_id="hyprev-005",
                hypothesis_id="hyp-NVDA-005",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.NEEDS_MORE_TESTS,
                rationale="Needs more tests.",
                confidence=0.6,
                created_at=now,
            ),
        ]
        storage.load_hypothesis_revision_proposals.return_value = []
        storage.load_hypothesis_revision_applications.return_value = []

        with patch("builtins.print") as mock_print:
            readiness = run_manual_trade_candidate_proposals(symbol="NVDA", storage=storage)

        self.assertEqual(1, len(readiness))
        mock_print.assert_any_call("Trade Candidate Proposals : 0")
        mock_print.assert_any_call("Proposal Design Checklist")
        mock_print.assert_any_call("No trade candidate proposals are ready for design review.")

    def test_runner_uses_default_symbol(self):
        storage = Mock()
        storage.load_hypotheses.return_value = []
        storage.load_observations.return_value = []
        storage.load_experiment_requests.return_value = []
        storage.load_experiment_results.return_value = []
        storage.load_hypothesis_reviews.return_value = []
        storage.load_hypothesis_revision_proposals.return_value = []
        storage.load_hypothesis_revision_applications.return_value = []

        with patch("builtins.print"):
            run_manual_trade_candidate_proposals(storage=storage)

        storage.load_hypotheses.assert_called_once_with(DEFAULT_SYMBOL)


if __name__ == "__main__":
    unittest.main()