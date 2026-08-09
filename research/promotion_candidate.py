"""Deterministic read-only promotion candidate evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from research.hypothesis import Hypothesis, HypothesisStatus
from research.hypothesis_evaluation import HypothesisEvidenceStatus, HypothesisEvidenceSummary
from research.hypothesis_review import HypothesisReview, HypothesisReviewRecommendation
from research.research_freshness import ResearchFreshnessItem, ReviewFreshnessStatus


class PromotionCandidateDecision(str, Enum):
    """Promotion-candidate evaluation outcome."""

    CANDIDATE = "candidate"
    NOT_CANDIDATE = "not_candidate"


@dataclass(frozen=True, slots=True)
class PromotionCandidateThresholds:
    """Conservative default thresholds for promotion candidate evaluation."""

    min_completed_experiments: int = 2
    min_trade_count: int = 50
    min_win_rate: float = 0.55
    min_average_return: float = 0.005


@dataclass(frozen=True, slots=True)
class PromotionCandidateEvaluation:
    """Deterministic promotion-candidate evaluation for one hypothesis."""

    hypothesis_id: str
    hypothesis_title: str
    decision: PromotionCandidateDecision
    evidence_status: HypothesisEvidenceStatus
    completed_experiments: int
    trade_count: int
    average_return: float | None
    win_rate: float | None
    latest_review_action: HypothesisReviewRecommendation | None
    failed_checks: tuple[str, ...] = field(default_factory=tuple)
    rationale: str = ""


_ELIGIBLE_STATUSES = {
    HypothesisStatus.PROPOSED,
    HypothesisStatus.ACTIVE,
    HypothesisStatus.SUPPORTED,
}


def _latest_append_only_child_by_parent_hypothesis_id(
    hypotheses: Iterable[Hypothesis],
) -> dict[str, Hypothesis]:
    latest_children: dict[str, Hypothesis] = {}

    for hypothesis in hypotheses:
        if hypothesis.parent_hypothesis_id is None:
            continue

        if hypothesis.source_revision_proposal_id is None:
            continue

        existing = latest_children.get(hypothesis.parent_hypothesis_id)
        if existing is None or hypothesis.created_at >= existing.created_at:
            latest_children[hypothesis.parent_hypothesis_id] = hypothesis

    return latest_children


def _build_not_candidate_rationale(
    failed_checks: tuple[str, ...],
    evidence_status: HypothesisEvidenceStatus,
) -> str:
    primary_failure = failed_checks[0]

    if primary_failure == "hypothesis_status_not_eligible":
        return "Hypothesis status is not eligible for promotion consideration."

    if primary_failure == "parent_has_append_only_child":
        return "Parent hypothesis has an append-only child and is not eligible for promotion consideration."

    if primary_failure == "evidence_not_promising":
        return f"{evidence_status.value.replace('_', ' ').capitalize()} evidence does not qualify for promotion consideration."

    if primary_failure == "review_not_current":
        return "Latest review is not current relative to available evidence."

    if primary_failure == "review_recommendation_retire":
        return "Latest review recommendation blocks promotion consideration."

    return "Evidence does not satisfy promotion-candidate thresholds."


def evaluate_promotion_candidates(
    *,
    hypotheses: Iterable[Hypothesis],
    evidence_summaries: Iterable[HypothesisEvidenceSummary],
    freshness_items: Iterable[ResearchFreshnessItem],
    latest_reviews_by_hypothesis_id: dict[str, HypothesisReview],
    thresholds: PromotionCandidateThresholds | None = None,
) -> list[PromotionCandidateEvaluation]:
    """Evaluate deterministic read-only promotion-candidate eligibility."""

    thresholds = thresholds or PromotionCandidateThresholds()
    hypotheses = list(hypotheses)
    evidence_by_hypothesis_id = {
        summary.hypothesis_id: summary
        for summary in evidence_summaries
    }
    freshness_by_hypothesis_id = {
        item.hypothesis_id: item
        for item in freshness_items
    }
    latest_append_only_children = _latest_append_only_child_by_parent_hypothesis_id(hypotheses)

    evaluations: list[PromotionCandidateEvaluation] = []
    for hypothesis in hypotheses:
        evidence = evidence_by_hypothesis_id[hypothesis.hypothesis_id]
        freshness = freshness_by_hypothesis_id[hypothesis.hypothesis_id]
        latest_review = latest_reviews_by_hypothesis_id.get(hypothesis.hypothesis_id)

        failed_checks: list[str] = []
        if hypothesis.status not in _ELIGIBLE_STATUSES:
            failed_checks.append("hypothesis_status_not_eligible")

        if hypothesis.hypothesis_id in latest_append_only_children:
            failed_checks.append("parent_has_append_only_child")

        if evidence.evidence_status != HypothesisEvidenceStatus.PROMISING:
            failed_checks.append("evidence_not_promising")

        if evidence.completed_experiment_count < thresholds.min_completed_experiments:
            failed_checks.append("completed_experiments_below_threshold")

        if evidence.total_trade_count < thresholds.min_trade_count:
            failed_checks.append("trade_count_below_threshold")

        if evidence.win_rate is None or evidence.win_rate < thresholds.min_win_rate:
            failed_checks.append("win_rate_below_threshold")

        if evidence.average_return is None or evidence.average_return < thresholds.min_average_return:
            failed_checks.append("average_return_below_threshold")

        if freshness.review_freshness != ReviewFreshnessStatus.CURRENT:
            failed_checks.append("review_not_current")

        if latest_review is not None and latest_review.recommendation == HypothesisReviewRecommendation.RETIRE:
            failed_checks.append("review_recommendation_retire")

        failed_checks_tuple = tuple(failed_checks)
        decision = (
            PromotionCandidateDecision.CANDIDATE
            if not failed_checks_tuple
            else PromotionCandidateDecision.NOT_CANDIDATE
        )
        rationale = (
            "Evidence exceeds promotion-candidate thresholds and latest review is current."
            if decision == PromotionCandidateDecision.CANDIDATE
            else _build_not_candidate_rationale(failed_checks_tuple, evidence.evidence_status)
        )

        evaluations.append(
            PromotionCandidateEvaluation(
                hypothesis_id=hypothesis.hypothesis_id,
                hypothesis_title=hypothesis.title,
                decision=decision,
                evidence_status=evidence.evidence_status,
                completed_experiments=evidence.completed_experiment_count,
                trade_count=evidence.total_trade_count,
                average_return=evidence.average_return,
                win_rate=evidence.win_rate,
                latest_review_action=(latest_review.recommendation if latest_review is not None else None),
                failed_checks=failed_checks_tuple,
                rationale=rationale,
            )
        )

    return evaluations