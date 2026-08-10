import unittest
from datetime import datetime, timezone

from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import DemoTradeCandidateStatus
from research.demo_trade_gate import DemoTradeGateDecision
from research.demo_trade_gate import evaluate_demo_trade_gate
from research.hypothesis_evaluation import HypothesisEvidenceStatus
from research.hypothesis_review import HypothesisReviewRecommendation
from research.promotion_candidate import PromotionCandidateDecision
from research.promotion_candidate import PromotionCandidateEvaluation


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


def _promotion_evaluation(**overrides):
    base = {
        "hypothesis_id": "hyp-001",
        "hypothesis_title": "Candidate hypothesis",
        "decision": PromotionCandidateDecision.CANDIDATE,
        "evidence_status": HypothesisEvidenceStatus.PROMISING,
        "completed_experiments": 2,
        "trade_count": 160,
        "average_return": 0.02,
        "win_rate": 0.66,
        "best_return": 0.16,
        "worst_return": -0.14,
        "latest_review_action": HypothesisReviewRecommendation.KEEP,
        "latest_review_confidence": 0.72,
        "latest_review_rationale": "Keep.",
        "review_current": True,
        "has_lineage_context": False,
        "risk_flags": ("large_worst_loss", "limited_experiment_count"),
        "failed_checks": (),
        "rationale": "Evidence exceeds promotion-candidate thresholds and latest review is current.",
    }
    base.update(overrides)
    return PromotionCandidateEvaluation(**base)


class DemoTradeGateTests(unittest.TestCase):
    def test_valid_proposed_candidate_can_gate_pass(self):
        evaluations = evaluate_demo_trade_gate([_candidate()], [_promotion_evaluation()])

        self.assertEqual(1, len(evaluations))
        self.assertEqual(DemoTradeGateDecision.GATE_PASS, evaluations[0].decision)
        self.assertEqual((), evaluations[0].failed_checks)

    def test_invalid_candidate_gate_fails(self):
        evaluations = evaluate_demo_trade_gate(
            [_candidate(entry_logic="")],
            [_promotion_evaluation()],
        )

        self.assertEqual(DemoTradeGateDecision.GATE_FAIL, evaluations[0].decision)
        self.assertIn("entry_logic_missing", evaluations[0].failed_checks)

    def test_demo_only_false_gate_fails(self):
        evaluations = evaluate_demo_trade_gate(
            [_candidate(demo_only=False)],
            [_promotion_evaluation()],
        )

        self.assertEqual(DemoTradeGateDecision.GATE_FAIL, evaluations[0].decision)
        self.assertIn("demo_only_false", evaluations[0].failed_checks)

    def test_missing_source_research_candidate_gate_fails(self):
        evaluations = evaluate_demo_trade_gate([_candidate()], [])

        self.assertEqual(DemoTradeGateDecision.GATE_FAIL, evaluations[0].decision)
        self.assertIn("source_research_candidate_missing", evaluations[0].failed_checks)

    def test_stale_review_gate_fails(self):
        evaluations = evaluate_demo_trade_gate(
            [_candidate()],
            [
                _promotion_evaluation(
                    decision=PromotionCandidateDecision.NOT_CANDIDATE,
                    review_current=False,
                    failed_checks=("review_not_current",),
                )
            ],
        )

        self.assertEqual(DemoTradeGateDecision.GATE_FAIL, evaluations[0].decision)
        self.assertIn("latest_review_not_current", evaluations[0].failed_checks)

    def test_weak_or_mixed_source_evidence_gate_fails(self):
        evaluations = evaluate_demo_trade_gate(
            [_candidate()],
            [
                _promotion_evaluation(
                    decision=PromotionCandidateDecision.NOT_CANDIDATE,
                    evidence_status=HypothesisEvidenceStatus.MIXED,
                    failed_checks=("evidence_not_promising",),
                )
            ],
        )

        self.assertEqual(DemoTradeGateDecision.GATE_FAIL, evaluations[0].decision)
        self.assertIn("source_evidence_not_promising", evaluations[0].failed_checks)

    def test_max_loss_per_trade_over_cap_gate_fails(self):
        evaluations = evaluate_demo_trade_gate(
            [_candidate(max_loss_per_trade=0.03)],
            [_promotion_evaluation()],
        )

        self.assertEqual(DemoTradeGateDecision.GATE_FAIL, evaluations[0].decision)
        self.assertIn("max_loss_per_trade_above_limit", evaluations[0].failed_checks)

    def test_max_portfolio_exposure_over_cap_gate_fails(self):
        evaluations = evaluate_demo_trade_gate(
            [_candidate(max_portfolio_exposure=0.11)],
            [_promotion_evaluation()],
        )

        self.assertEqual(DemoTradeGateDecision.GATE_FAIL, evaluations[0].decision)
        self.assertIn("max_portfolio_exposure_above_limit", evaluations[0].failed_checks)

    def test_empty_pause_conditions_gate_fails(self):
        evaluations = evaluate_demo_trade_gate(
            [_candidate(pause_conditions=())],
            [_promotion_evaluation()],
        )

        self.assertEqual(DemoTradeGateDecision.GATE_FAIL, evaluations[0].decision)
        self.assertIn("pause_conditions_empty", evaluations[0].failed_checks)

    def test_identical_entry_exit_and_invalidation_logic_gate_fails(self):
        evaluations = evaluate_demo_trade_gate(
            [
                _candidate(
                    entry_logic="same logic",
                    exit_logic="same logic",
                    invalidation_logic="same logic",
                )
            ],
            [_promotion_evaluation()],
        )

        self.assertEqual(DemoTradeGateDecision.GATE_FAIL, evaluations[0].decision)
        self.assertIn("entry_logic_matches_exit_logic", evaluations[0].failed_checks)
        self.assertIn("entry_logic_matches_invalidation_logic", evaluations[0].failed_checks)
        self.assertIn("exit_logic_matches_invalidation_logic", evaluations[0].failed_checks)

    def test_non_proposed_candidate_is_not_evaluated(self):
        evaluations = evaluate_demo_trade_gate(
            [_candidate(status=DemoTradeCandidateStatus.GATE_PASSED)],
            [_promotion_evaluation()],
        )

        self.assertEqual(DemoTradeGateDecision.NOT_EVALUATED, evaluations[0].decision)
        self.assertEqual((), evaluations[0].failed_checks)


if __name__ == "__main__":
    unittest.main()