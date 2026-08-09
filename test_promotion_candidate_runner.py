import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from research.experiment import ExperimentRequest, ExperimentRequestStatus, ExperimentTestType
from research.experiment_result import ExperimentMetrics, ExperimentResult, ExperimentResultStatus
from research.hypothesis import Hypothesis, HypothesisStatus
from research.hypothesis_review import HypothesisReview, HypothesisReviewRecommendation
from research.runner import DEFAULT_SYMBOL, run_manual_promotion_candidates


class ManualPromotionCandidateRunnerTests(unittest.TestCase):
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

    def test_runner_outputs_read_only_promotion_candidate_summary(self):
        storage = Mock()
        now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)

        candidate = Hypothesis(
            hypothesis_id="hyp-NVDA-002",
            symbol="NVDA",
            title="Candidate hypothesis",
            description="Promising and reviewed.",
            status=HypothesisStatus.ACTIVE,
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
            ExperimentResult(
                hypothesis_id="hyp-NVDA-002",
                experiment_result_id="expr-hyp-NVDA-002-11",
                experiment_request_id="expreq-hyp-NVDA-002",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=now - timedelta(hours=1),
                completed_at=now - timedelta(hours=1),
                metrics=ExperimentMetrics(
                    trade_count=80,
                    average_return=0.0214,
                    win_rate=0.675,
                    extra_metrics={
                        "best_return": 0.1651,
                        "worst_return": -0.1401,
                    },
                ),
                summary="Completed",
                created_at=now - timedelta(hours=1),
                updated_at=now - timedelta(hours=1),
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
            evaluations = run_manual_promotion_candidates(symbol="NVDA", storage=storage)

        self.assertEqual(2, len(evaluations))
        mock_print.assert_any_call("Manual Promotion Candidates: NVDA")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Hypotheses Loaded : 2")
        mock_print.assert_any_call("Candidates Evaluated : 2")
        mock_print.assert_any_call("Promotion Candidates : 1")
        mock_print.assert_any_call("- hyp-NVDA-002 decision=candidate")
        mock_print.assert_any_call("  average_return=2.07%")
        mock_print.assert_any_call("  win_rate=66.25%")
        mock_print.assert_any_call("  latest_review_action=keep")
        mock_print.assert_any_call("- hyp-NVDA-005 decision=not_candidate")
        mock_print.assert_any_call(
            "  failed_checks=evidence_not_promising, win_rate_below_threshold, average_return_below_threshold"
        )
        mock_print.assert_any_call("Promotion Summary")
        mock_print.assert_any_call("- candidate : 1")
        mock_print.assert_any_call("- not_candidate : 1")
        mock_print.assert_any_call(
            "No automatic promotion action is available. Promotion candidates require explicit human review."
        )
        mock_print.assert_any_call("Candidate Detail")
        mock_print.assert_any_call("- hyp-NVDA-002")
        mock_print.assert_any_call(
            "  evidence_strength: completed_experiments=2, trade_count=160, average_return=2.07%, win_rate=66.25%, best_return=16.51%, worst_return=-14.01%"
        )
        mock_print.assert_any_call(
            "  review_state: action=keep, confidence=0.70, current=yes"
        )
        mock_print.assert_any_call("  latest_review_summary: Keep.")
        mock_print.assert_any_call(
            "  risk_flags=large_worst_loss, limited_experiment_count"
        )
        mock_print.assert_any_call("  required_human_checks:")
        mock_print.assert_any_call("    - Confirm hypothesis still makes economic sense.")
        mock_print.assert_any_call("    - Inspect experiment assumptions and setup conditions.")
        mock_print.assert_any_call("    - Check whether returns are overlapping or regime-dependent.")
        mock_print.assert_any_call("    - Check downside risk and worst-return behavior.")
        mock_print.assert_any_call("    - Decide whether to create a trade-candidate proposal.")
        mock_print.assert_any_call("  reminder: Promotion candidate is not approval to trade.")
        mock_print.assert_any_call("Promotion candidate evaluation complete. No records were modified.")

        storage.save_hypotheses.assert_not_called()
        storage.save_experiment_requests.assert_not_called()
        storage.save_experiment_results.assert_not_called()
        storage.save_hypothesis_reviews.assert_not_called()
        storage.save_hypothesis_revision_proposals.assert_not_called()
        storage.save_hypothesis_revision_applications.assert_not_called()

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
            run_manual_promotion_candidates(storage=storage)

        storage.load_hypotheses.assert_called_once_with(DEFAULT_SYMBOL)

    def test_runner_prints_stable_empty_candidate_detail_message_when_no_candidates_exist(self):
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
            evaluations = run_manual_promotion_candidates(symbol="NVDA", storage=storage)

        self.assertEqual(1, len(evaluations))
        mock_print.assert_any_call("Promotion Candidates : 0")
        mock_print.assert_any_call("Candidate Detail")
        mock_print.assert_any_call("No promotion candidates available for candidate detail review.")


if __name__ == "__main__":
    unittest.main()