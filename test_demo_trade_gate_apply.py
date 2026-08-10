import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import DemoTradeCandidateStatus
from research.demo_trade_gate_apply import DemoTradeGateApplyService
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


def _candidate(**overrides):
    base = {
        "trade_candidate_id": "dtc-001",
        "symbol": "NVDA",
        "source_hypothesis_id": "hyp-001",
        "source_research_candidate_decision": "candidate",
        "created_at": datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc),
        "status": DemoTradeCandidateStatus.PROPOSED,
        "entry_logic": "Enter on breakout close above prior range.",
        "exit_logic": "Exit on trailing stop or target.",
        "invalidation_logic": "Invalidate on range breakdown.",
        "maximum_holding_period": "5D",
        "position_sizing_rule": "Risk 50 bps of equity.",
        "max_loss_per_trade": 0.01,
        "max_portfolio_exposure": 0.05,
        "demo_only": True,
        "monitoring_frequency": "15m",
        "pause_conditions": ("halted_market",),
        "source_evidence_summary": {"completed_experiments": 2},
        "source_review_action": "keep",
        "source_review_confidence": 0.72,
        "risk_flags": ("large_worst_loss", "limited_experiment_count"),
        "created_by": "ai",
    }
    base.update(overrides)
    return DemoTradeCandidate(**base)


class DemoTradeGateApplyServiceTests(unittest.TestCase):
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
            machine_readable_entry_conditions=({"field": "Close", "operator": ">", "value": 100.0},),
            exit_conditions="Exit",
            time_horizon="5D",
            forward_horizon=5,
            status=ExperimentRequestStatus.PROPOSED,
        )

    def _build_completed_result(self, hypothesis_id: str, experiment_request_id: str, completed_at: datetime, average_return: float = 0.02, win_rate: float = 0.66) -> ExperimentResult:
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
                trade_count=80,
                average_return=average_return,
                win_rate=win_rate,
                extra_metrics={"best_return": 0.16, "worst_return": -0.14},
            ),
            summary="Completed",
            created_at=completed_at,
            updated_at=completed_at,
        )

    def _build_storage(self, *, candidates, review_current=True, average_return=0.02, win_rate=0.66):
        storage = Mock()
        now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
        hypothesis = Hypothesis(
            hypothesis_id="hyp-001",
            symbol="NVDA",
            title="Candidate hypothesis",
            description="Promising and reviewed.",
            status=HypothesisStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        storage.load_hypotheses.return_value = [hypothesis]
        storage.load_observations.return_value = [] if review_current else [Mock(created_at=(now + timedelta(days=1)).isoformat())]
        storage.load_experiment_requests.return_value = [self._build_executable_request("hyp-001")]
        storage.load_experiment_results.return_value = [
            self._build_completed_result("hyp-001", "expreq-hyp-001", now - timedelta(hours=2), average_return=average_return, win_rate=win_rate),
            self._build_completed_result("hyp-001", "expreq-hyp-001", now - timedelta(hours=1), average_return=average_return, win_rate=win_rate),
        ]
        review_created_at = now if review_current else now - timedelta(days=2)
        storage.load_hypothesis_reviews.return_value = [
            HypothesisReview(
                review_id="hyprev-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                recommendation=HypothesisReviewRecommendation.KEEP,
                rationale="Keep.",
                confidence=0.72,
                created_at=review_created_at,
            )
        ]
        storage.load_hypothesis_revision_proposals.return_value = []
        storage.load_demo_trade_candidates.return_value = candidates
        return storage

    def test_dry_run_writes_nothing(self):
        storage = self._build_storage(candidates=[_candidate()])
        service = DemoTradeGateApplyService(storage=storage)

        result = service.apply_for_symbol("NVDA", apply_mode=False)

        self.assertFalse(result.apply_mode)
        self.assertEqual(1, result.gate_evaluated)
        self.assertEqual(1, result.would_pass)
        self.assertEqual(0, result.applied_passed)
        storage.save_demo_trade_candidate.assert_not_called()

    def test_apply_writes_gate_passed_version_for_gate_pass(self):
        storage = self._build_storage(candidates=[_candidate()])
        service = DemoTradeGateApplyService(storage=storage)

        result = service.apply_for_symbol("NVDA", apply_mode=True)

        self.assertTrue(result.apply_mode)
        self.assertEqual(1, result.applied_passed)
        saved_candidate = storage.save_demo_trade_candidate.call_args.args[0]
        self.assertEqual(DemoTradeCandidateStatus.GATE_PASSED, saved_candidate.status)
        self.assertEqual("gate_pass", saved_candidate.gate_decision)
        self.assertEqual("dtc-001", saved_candidate.source_trade_candidate_id)

    def test_apply_writes_gate_failed_version_for_gate_fail(self):
        storage = self._build_storage(candidates=[_candidate(max_loss_per_trade=0.03)])
        service = DemoTradeGateApplyService(storage=storage)

        result = service.apply_for_symbol("NVDA", apply_mode=True)

        self.assertEqual(1, result.applied_failed)
        saved_candidate = storage.save_demo_trade_candidate.call_args.args[0]
        self.assertEqual(DemoTradeCandidateStatus.GATE_FAILED, saved_candidate.status)
        self.assertEqual("gate_fail", saved_candidate.gate_decision)
        self.assertIn("max_loss_per_trade_above_limit", saved_candidate.failed_checks)

    def test_duplicate_apply_skips_already_gated_candidate(self):
        gated = _candidate(
            trade_candidate_id="dtc-002",
            source_trade_candidate_id="dtc-001",
            status=DemoTradeCandidateStatus.GATE_PASSED,
            created_at=datetime(2026, 8, 9, 13, 0, tzinfo=timezone.utc),
            gate_checked_at=datetime(2026, 8, 9, 13, 0, tzinfo=timezone.utc),
            gate_decision="gate_pass",
            gate_rationale="Candidate passes deterministic demo gate checks.",
            created_by="sentinel",
        )
        storage = self._build_storage(candidates=[_candidate(), gated])
        service = DemoTradeGateApplyService(storage=storage)

        result = service.apply_for_symbol("NVDA", apply_mode=True)

        self.assertEqual(1, result.skipped_existing)
        self.assertEqual(0, result.gate_evaluated)
        storage.save_demo_trade_candidate.assert_not_called()

    def test_latest_status_wins(self):
        newer_proposed = _candidate(
            trade_candidate_id="dtc-003",
            source_trade_candidate_id="dtc-001",
            created_at=datetime(2026, 8, 9, 14, 0, tzinfo=timezone.utc),
            status=DemoTradeCandidateStatus.PROPOSED,
            created_by="sentinel",
        )
        older_gated = _candidate(
            trade_candidate_id="dtc-002",
            source_trade_candidate_id="dtc-001",
            created_at=datetime(2026, 8, 9, 13, 0, tzinfo=timezone.utc),
            status=DemoTradeCandidateStatus.GATE_FAILED,
            gate_checked_at=datetime(2026, 8, 9, 13, 0, tzinfo=timezone.utc),
            gate_decision="gate_fail",
            failed_checks=("max_loss_per_trade_above_limit",),
            gate_rationale="Candidate fails deterministic demo gate checks.",
            created_by="sentinel",
        )
        storage = self._build_storage(candidates=[_candidate(), older_gated, newer_proposed])
        service = DemoTradeGateApplyService(storage=storage)

        result = service.apply_for_symbol("NVDA", apply_mode=False)

        self.assertEqual(1, result.gate_evaluated)
        self.assertEqual(0, result.skipped_existing)


if __name__ == "__main__":
    unittest.main()