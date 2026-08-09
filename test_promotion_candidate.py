import unittest
from datetime import datetime, timedelta, timezone

from research.hypothesis import Hypothesis, HypothesisStatus
from research.hypothesis_evaluation import HypothesisEvidenceStatus, HypothesisEvidenceSummary
from research.hypothesis_review import HypothesisReview, HypothesisReviewRecommendation
from research.promotion_candidate import PromotionCandidateDecision
from research.promotion_candidate import evaluate_promotion_candidates
from research.research_freshness import ProposalFreshnessStatus
from research.research_freshness import ResearchFreshnessItem
from research.research_freshness import ReviewFreshnessStatus


def _hypothesis(
    *,
    hypothesis_id: str,
    status: HypothesisStatus = HypothesisStatus.ACTIVE,
    parent_hypothesis_id: str | None = None,
    source_revision_proposal_id: str | None = None,
):
    now = datetime(2026, 8, 9, 0, 0, tzinfo=timezone.utc)
    hypothesis = Hypothesis(
        hypothesis_id=hypothesis_id,
        symbol="NVDA",
        title=f"Title {hypothesis_id}",
        description="Description.",
        status=status,
        created_at=now,
        updated_at=now,
    )

    if parent_hypothesis_id is not None:
        hypothesis = hypothesis.with_parent(
            parent_hypothesis_id,
            source_revision_proposal_id=source_revision_proposal_id,
            updated_at=now,
        )

    return hypothesis


def _evidence(
    *,
    hypothesis_id: str,
    evidence_status: HypothesisEvidenceStatus,
    completed_experiment_count: int,
    total_trade_count: int,
    average_return: float | None,
    win_rate: float | None,
):
    return HypothesisEvidenceSummary(
        hypothesis_id=hypothesis_id,
        hypothesis_title=f"Title {hypothesis_id}",
        completed_experiment_count=completed_experiment_count,
        zero_trade_completed_experiment_count=0,
        total_trade_count=total_trade_count,
        average_return=average_return,
        win_rate=win_rate,
        best_return=None,
        worst_return=None,
        evidence_status=evidence_status,
    )


def _freshness(*, hypothesis_id: str, review_freshness: ReviewFreshnessStatus):
    now = datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc)
    return ResearchFreshnessItem(
        hypothesis_id=hypothesis_id,
        hypothesis_title=f"Title {hypothesis_id}",
        latest_observation_at=now - timedelta(days=1),
        latest_completed_result_at=now - timedelta(hours=2),
        latest_review_at=(now - timedelta(hours=1) if review_freshness == ReviewFreshnessStatus.CURRENT else None),
        latest_revision_proposal_at=None,
        review_freshness=review_freshness,
        proposal_freshness=ProposalFreshnessStatus.NOT_APPLICABLE,
        rationale="Freshness rationale.",
    )


def _review(*, hypothesis_id: str, recommendation: HypothesisReviewRecommendation):
    return HypothesisReview(
        review_id=f"hyprev-{hypothesis_id}",
        hypothesis_id=hypothesis_id,
        symbol="NVDA",
        recommendation=recommendation,
        rationale="Review rationale.",
        confidence=0.7,
        created_at=datetime(2026, 8, 9, 13, 0, tzinfo=timezone.utc),
    )


class PromotionCandidateTests(unittest.TestCase):
    def test_proposed_promising_hypothesis_with_current_review_and_thresholds_becomes_candidate(self):
        hypothesis = _hypothesis(hypothesis_id="hyp-proposed", status=HypothesisStatus.PROPOSED)
        evidence = _evidence(
            hypothesis_id="hyp-proposed",
            evidence_status=HypothesisEvidenceStatus.PROMISING,
            completed_experiment_count=2,
            total_trade_count=160,
            average_return=0.0207,
            win_rate=0.6625,
        )
        freshness = _freshness(
            hypothesis_id="hyp-proposed",
            review_freshness=ReviewFreshnessStatus.CURRENT,
        )
        review = _review(
            hypothesis_id="hyp-proposed",
            recommendation=HypothesisReviewRecommendation.KEEP,
        )

        evaluations = evaluate_promotion_candidates(
            hypotheses=[hypothesis],
            evidence_summaries=[evidence],
            freshness_items=[freshness],
            latest_reviews_by_hypothesis_id={"hyp-proposed": review},
        )

        self.assertEqual(PromotionCandidateDecision.CANDIDATE, evaluations[0].decision)

    def test_promising_hypothesis_with_current_review_and_thresholds_becomes_candidate(self):
        hypothesis = _hypothesis(hypothesis_id="hyp-001")
        evidence = _evidence(
            hypothesis_id="hyp-001",
            evidence_status=HypothesisEvidenceStatus.PROMISING,
            completed_experiment_count=2,
            total_trade_count=160,
            average_return=0.0207,
            win_rate=0.6625,
        )
        freshness = _freshness(hypothesis_id="hyp-001", review_freshness=ReviewFreshnessStatus.CURRENT)
        review = _review(hypothesis_id="hyp-001", recommendation=HypothesisReviewRecommendation.KEEP)

        evaluations = evaluate_promotion_candidates(
            hypotheses=[hypothesis],
            evidence_summaries=[evidence],
            freshness_items=[freshness],
            latest_reviews_by_hypothesis_id={"hyp-001": review},
        )

        self.assertEqual(PromotionCandidateDecision.CANDIDATE, evaluations[0].decision)

    def test_promising_hypothesis_below_trade_threshold_is_not_candidate(self):
        hypothesis = _hypothesis(hypothesis_id="hyp-002")
        evidence = _evidence(
            hypothesis_id="hyp-002",
            evidence_status=HypothesisEvidenceStatus.PROMISING,
            completed_experiment_count=2,
            total_trade_count=49,
            average_return=0.02,
            win_rate=0.60,
        )
        freshness = _freshness(hypothesis_id="hyp-002", review_freshness=ReviewFreshnessStatus.CURRENT)
        review = _review(hypothesis_id="hyp-002", recommendation=HypothesisReviewRecommendation.KEEP)

        evaluations = evaluate_promotion_candidates(
            hypotheses=[hypothesis],
            evidence_summaries=[evidence],
            freshness_items=[freshness],
            latest_reviews_by_hypothesis_id={"hyp-002": review},
        )

        self.assertEqual(PromotionCandidateDecision.NOT_CANDIDATE, evaluations[0].decision)
        self.assertIn("trade_count_below_threshold", evaluations[0].failed_checks)

    def test_promising_hypothesis_with_stale_review_is_not_candidate(self):
        hypothesis = _hypothesis(hypothesis_id="hyp-003")
        evidence = _evidence(
            hypothesis_id="hyp-003",
            evidence_status=HypothesisEvidenceStatus.PROMISING,
            completed_experiment_count=2,
            total_trade_count=80,
            average_return=0.02,
            win_rate=0.60,
        )
        freshness = _freshness(hypothesis_id="hyp-003", review_freshness=ReviewFreshnessStatus.STALE_AFTER_NEW_RESULT)
        review = _review(hypothesis_id="hyp-003", recommendation=HypothesisReviewRecommendation.KEEP)

        evaluations = evaluate_promotion_candidates(
            hypotheses=[hypothesis],
            evidence_summaries=[evidence],
            freshness_items=[freshness],
            latest_reviews_by_hypothesis_id={"hyp-003": review},
        )

        self.assertEqual(PromotionCandidateDecision.NOT_CANDIDATE, evaluations[0].decision)
        self.assertIn("review_not_current", evaluations[0].failed_checks)

    def test_thresholds_are_applied_even_when_evidence_status_is_promising(self):
        hypothesis = _hypothesis(hypothesis_id="hyp-003b")
        evidence = _evidence(
            hypothesis_id="hyp-003b",
            evidence_status=HypothesisEvidenceStatus.PROMISING,
            completed_experiment_count=2,
            total_trade_count=80,
            average_return=0.004,
            win_rate=0.54,
        )
        freshness = _freshness(hypothesis_id="hyp-003b", review_freshness=ReviewFreshnessStatus.CURRENT)
        review = _review(hypothesis_id="hyp-003b", recommendation=HypothesisReviewRecommendation.KEEP)

        evaluations = evaluate_promotion_candidates(
            hypotheses=[hypothesis],
            evidence_summaries=[evidence],
            freshness_items=[freshness],
            latest_reviews_by_hypothesis_id={"hyp-003b": review},
        )

        self.assertEqual(PromotionCandidateDecision.NOT_CANDIDATE, evaluations[0].decision)
        self.assertIn("win_rate_below_threshold", evaluations[0].failed_checks)
        self.assertIn("average_return_below_threshold", evaluations[0].failed_checks)

    def test_mixed_evidence_is_not_candidate(self):
        hypothesis = _hypothesis(hypothesis_id="hyp-004")
        evidence = _evidence(
            hypothesis_id="hyp-004",
            evidence_status=HypothesisEvidenceStatus.MIXED,
            completed_experiment_count=4,
            total_trade_count=143,
            average_return=-0.0019,
            win_rate=0.5199,
        )
        freshness = _freshness(hypothesis_id="hyp-004", review_freshness=ReviewFreshnessStatus.CURRENT)
        review = _review(hypothesis_id="hyp-004", recommendation=HypothesisReviewRecommendation.NEEDS_MORE_TESTS)

        evaluations = evaluate_promotion_candidates(
            hypotheses=[hypothesis],
            evidence_summaries=[evidence],
            freshness_items=[freshness],
            latest_reviews_by_hypothesis_id={"hyp-004": review},
        )

        self.assertEqual(PromotionCandidateDecision.NOT_CANDIDATE, evaluations[0].decision)
        self.assertIn("evidence_not_promising", evaluations[0].failed_checks)

    def test_insufficient_data_is_not_candidate(self):
        hypothesis = _hypothesis(hypothesis_id="hyp-005")
        evidence = _evidence(
            hypothesis_id="hyp-005",
            evidence_status=HypothesisEvidenceStatus.INSUFFICIENT_DATA,
            completed_experiment_count=1,
            total_trade_count=12,
            average_return=0.01,
            win_rate=0.65,
        )
        freshness = _freshness(hypothesis_id="hyp-005", review_freshness=ReviewFreshnessStatus.MISSING)

        evaluations = evaluate_promotion_candidates(
            hypotheses=[hypothesis],
            evidence_summaries=[evidence],
            freshness_items=[freshness],
            latest_reviews_by_hypothesis_id={},
        )

        self.assertEqual(PromotionCandidateDecision.NOT_CANDIDATE, evaluations[0].decision)

    def test_parent_hypothesis_with_append_only_child_is_not_candidate(self):
        parent = _hypothesis(hypothesis_id="hyp-parent")
        child = _hypothesis(
            hypothesis_id="hyp-child",
            parent_hypothesis_id="hyp-parent",
            source_revision_proposal_id="hyprevp-001",
        )
        evidence = _evidence(
            hypothesis_id="hyp-parent",
            evidence_status=HypothesisEvidenceStatus.PROMISING,
            completed_experiment_count=3,
            total_trade_count=120,
            average_return=0.02,
            win_rate=0.60,
        )
        child_evidence = _evidence(
            hypothesis_id="hyp-child",
            evidence_status=HypothesisEvidenceStatus.PROMISING,
            completed_experiment_count=3,
            total_trade_count=120,
            average_return=0.02,
            win_rate=0.60,
        )
        parent_freshness = _freshness(hypothesis_id="hyp-parent", review_freshness=ReviewFreshnessStatus.CURRENT)
        child_freshness = _freshness(hypothesis_id="hyp-child", review_freshness=ReviewFreshnessStatus.CURRENT)
        parent_review = _review(hypothesis_id="hyp-parent", recommendation=HypothesisReviewRecommendation.KEEP)
        child_review = _review(hypothesis_id="hyp-child", recommendation=HypothesisReviewRecommendation.KEEP)

        evaluations = evaluate_promotion_candidates(
            hypotheses=[parent, child],
            evidence_summaries=[evidence, child_evidence],
            freshness_items=[parent_freshness, child_freshness],
            latest_reviews_by_hypothesis_id={"hyp-parent": parent_review, "hyp-child": child_review},
        )

        by_id = {evaluation.hypothesis_id: evaluation for evaluation in evaluations}
        self.assertEqual(PromotionCandidateDecision.NOT_CANDIDATE, by_id["hyp-parent"].decision)
        self.assertIn("parent_has_append_only_child", by_id["hyp-parent"].failed_checks)
        self.assertEqual(PromotionCandidateDecision.CANDIDATE, by_id["hyp-child"].decision)

    def test_proposed_parent_hypothesis_with_append_only_child_is_not_candidate(self):
        parent = _hypothesis(hypothesis_id="hyp-parent-proposed", status=HypothesisStatus.PROPOSED)
        child = _hypothesis(
            hypothesis_id="hyp-child-proposed",
            parent_hypothesis_id="hyp-parent-proposed",
            source_revision_proposal_id="hyprevp-010",
        )
        parent_evidence = _evidence(
            hypothesis_id="hyp-parent-proposed",
            evidence_status=HypothesisEvidenceStatus.PROMISING,
            completed_experiment_count=3,
            total_trade_count=120,
            average_return=0.02,
            win_rate=0.60,
        )
        child_evidence = _evidence(
            hypothesis_id="hyp-child-proposed",
            evidence_status=HypothesisEvidenceStatus.PROMISING,
            completed_experiment_count=3,
            total_trade_count=120,
            average_return=0.02,
            win_rate=0.60,
        )
        parent_freshness = _freshness(
            hypothesis_id="hyp-parent-proposed",
            review_freshness=ReviewFreshnessStatus.CURRENT,
        )
        child_freshness = _freshness(
            hypothesis_id="hyp-child-proposed",
            review_freshness=ReviewFreshnessStatus.CURRENT,
        )
        parent_review = _review(
            hypothesis_id="hyp-parent-proposed",
            recommendation=HypothesisReviewRecommendation.KEEP,
        )
        child_review = _review(
            hypothesis_id="hyp-child-proposed",
            recommendation=HypothesisReviewRecommendation.KEEP,
        )

        evaluations = evaluate_promotion_candidates(
            hypotheses=[parent, child],
            evidence_summaries=[parent_evidence, child_evidence],
            freshness_items=[parent_freshness, child_freshness],
            latest_reviews_by_hypothesis_id={
                "hyp-parent-proposed": parent_review,
                "hyp-child-proposed": child_review,
            },
        )

        by_id = {evaluation.hypothesis_id: evaluation for evaluation in evaluations}
        self.assertEqual(
            PromotionCandidateDecision.NOT_CANDIDATE,
            by_id["hyp-parent-proposed"].decision,
        )
        self.assertIn(
            "parent_has_append_only_child",
            by_id["hyp-parent-proposed"].failed_checks,
        )

    def test_review_action_retire_blocks_candidacy(self):
        hypothesis = _hypothesis(hypothesis_id="hyp-006")
        evidence = _evidence(
            hypothesis_id="hyp-006",
            evidence_status=HypothesisEvidenceStatus.PROMISING,
            completed_experiment_count=2,
            total_trade_count=80,
            average_return=0.02,
            win_rate=0.60,
        )
        freshness = _freshness(hypothesis_id="hyp-006", review_freshness=ReviewFreshnessStatus.CURRENT)
        review = _review(hypothesis_id="hyp-006", recommendation=HypothesisReviewRecommendation.RETIRE)

        evaluations = evaluate_promotion_candidates(
            hypotheses=[hypothesis],
            evidence_summaries=[evidence],
            freshness_items=[freshness],
            latest_reviews_by_hypothesis_id={"hyp-006": review},
        )

        self.assertEqual(PromotionCandidateDecision.NOT_CANDIDATE, evaluations[0].decision)
        self.assertIn("review_recommendation_retire", evaluations[0].failed_checks)

    def test_old_records_without_review_are_not_candidates(self):
        hypothesis = _hypothesis(hypothesis_id="hyp-007")
        evidence = _evidence(
            hypothesis_id="hyp-007",
            evidence_status=HypothesisEvidenceStatus.PROMISING,
            completed_experiment_count=2,
            total_trade_count=80,
            average_return=0.02,
            win_rate=0.60,
        )
        freshness = _freshness(hypothesis_id="hyp-007", review_freshness=ReviewFreshnessStatus.MISSING)

        evaluations = evaluate_promotion_candidates(
            hypotheses=[hypothesis],
            evidence_summaries=[evidence],
            freshness_items=[freshness],
            latest_reviews_by_hypothesis_id={},
        )

        self.assertEqual(PromotionCandidateDecision.NOT_CANDIDATE, evaluations[0].decision)
        self.assertIn("review_not_current", evaluations[0].failed_checks)

    def test_inactive_hypothesis_is_not_candidate(self):
        hypothesis = _hypothesis(hypothesis_id="hyp-008", status=HypothesisStatus.INACTIVE)
        evidence = _evidence(
            hypothesis_id="hyp-008",
            evidence_status=HypothesisEvidenceStatus.PROMISING,
            completed_experiment_count=3,
            total_trade_count=120,
            average_return=0.02,
            win_rate=0.60,
        )
        freshness = _freshness(hypothesis_id="hyp-008", review_freshness=ReviewFreshnessStatus.CURRENT)
        review = _review(hypothesis_id="hyp-008", recommendation=HypothesisReviewRecommendation.KEEP)

        evaluations = evaluate_promotion_candidates(
            hypotheses=[hypothesis],
            evidence_summaries=[evidence],
            freshness_items=[freshness],
            latest_reviews_by_hypothesis_id={"hyp-008": review},
        )

        self.assertEqual(PromotionCandidateDecision.NOT_CANDIDATE, evaluations[0].decision)
        self.assertIn("hypothesis_status_not_eligible", evaluations[0].failed_checks)

    def test_contradicted_blocked_and_superseded_hypotheses_are_not_candidates(self):
        statuses = [
            HypothesisStatus.CONTRADICTED,
            HypothesisStatus.BLOCKED,
            HypothesisStatus.SUPERSEDED,
        ]

        for status in statuses:
            with self.subTest(status=status.value):
                hypothesis = _hypothesis(hypothesis_id=f"hyp-{status.value}", status=status)
                evidence = _evidence(
                    hypothesis_id=f"hyp-{status.value}",
                    evidence_status=HypothesisEvidenceStatus.PROMISING,
                    completed_experiment_count=3,
                    total_trade_count=120,
                    average_return=0.02,
                    win_rate=0.60,
                )
                freshness = _freshness(
                    hypothesis_id=f"hyp-{status.value}",
                    review_freshness=ReviewFreshnessStatus.CURRENT,
                )
                review = _review(
                    hypothesis_id=f"hyp-{status.value}",
                    recommendation=HypothesisReviewRecommendation.KEEP,
                )

                evaluations = evaluate_promotion_candidates(
                    hypotheses=[hypothesis],
                    evidence_summaries=[evidence],
                    freshness_items=[freshness],
                    latest_reviews_by_hypothesis_id={f"hyp-{status.value}": review},
                )

                self.assertEqual(PromotionCandidateDecision.NOT_CANDIDATE, evaluations[0].decision)
                self.assertIn("hypothesis_status_not_eligible", evaluations[0].failed_checks)


if __name__ == "__main__":
    unittest.main()