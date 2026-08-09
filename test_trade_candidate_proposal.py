import unittest

from research.promotion_candidate import PromotionCandidateDecision, PromotionCandidateEvaluation
from research.hypothesis_evaluation import HypothesisEvidenceStatus
from research.hypothesis_review import HypothesisReviewRecommendation
from research.trade_candidate_proposal import TradeCandidateProposalDecision
from research.trade_candidate_proposal import evaluate_trade_candidate_proposals


def _promotion_evaluation(*, hypothesis_id: str, decision: PromotionCandidateDecision):
    return PromotionCandidateEvaluation(
        hypothesis_id=hypothesis_id,
        hypothesis_title=f"Title {hypothesis_id}",
        decision=decision,
        evidence_status=HypothesisEvidenceStatus.PROMISING
        if decision == PromotionCandidateDecision.CANDIDATE
        else HypothesisEvidenceStatus.MIXED,
        completed_experiments=2,
        trade_count=160,
        average_return=0.0207,
        win_rate=0.6625,
        best_return=0.1651,
        worst_return=-0.1401,
        latest_review_action=HypothesisReviewRecommendation.KEEP,
        latest_review_confidence=0.72,
        latest_review_rationale="Keep.",
        review_current=True,
        has_lineage_context=False,
        risk_flags=("limited_experiment_count",),
        failed_checks=() if decision == PromotionCandidateDecision.CANDIDATE else ("evidence_not_promising",),
        rationale="Promotion rationale.",
    )


class TradeCandidateProposalTests(unittest.TestCase):
    def test_qualified_research_candidate_becomes_proposal_ready(self):
        readiness = evaluate_trade_candidate_proposals(
            [_promotion_evaluation(hypothesis_id="hyp-001", decision=PromotionCandidateDecision.CANDIDATE)]
        )

        self.assertEqual(1, len(readiness))
        self.assertEqual(TradeCandidateProposalDecision.PROPOSAL_READY, readiness[0].decision)
        self.assertEqual(PromotionCandidateDecision.CANDIDATE, readiness[0].source_decision)

    def test_non_candidate_becomes_not_ready(self):
        readiness = evaluate_trade_candidate_proposals(
            [_promotion_evaluation(hypothesis_id="hyp-002", decision=PromotionCandidateDecision.NOT_CANDIDATE)]
        )

        self.assertEqual(TradeCandidateProposalDecision.NOT_READY, readiness[0].decision)
        self.assertEqual(PromotionCandidateDecision.NOT_CANDIDATE, readiness[0].source_decision)

    def test_proposal_ready_includes_required_and_missing_components(self):
        readiness = evaluate_trade_candidate_proposals(
            [_promotion_evaluation(hypothesis_id="hyp-003", decision=PromotionCandidateDecision.CANDIDATE)]
        )

        self.assertEqual(
            (
                "entry_logic",
                "exit_logic",
                "invalidation_logic",
                "position_sizing",
                "risk_limits",
                "demo_parameters",
            ),
            readiness[0].required_components,
        )
        self.assertEqual(readiness[0].required_components, readiness[0].missing_components)


if __name__ == "__main__":
    unittest.main()