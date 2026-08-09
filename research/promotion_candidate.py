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
    best_return: float | None
    worst_return: float | None
    latest_review_action: HypothesisReviewRecommendation | None
    latest_review_confidence: float | None = None
    latest_review_rationale: str | None = None
    review_current: bool = False
    has_lineage_context: bool = False
    risk_flags: tuple[str, ...] = field(default_factory=tuple)
    failed_checks: tuple[str, ...] = field(default_factory=tuple)
    rationale: str = ""


def _build_candidate_risk_flags(
    *,
    hypothesis: Hypothesis,
    evidence: HypothesisEvidenceSummary,
    thresholds: PromotionCandidateThresholds,
) -> tuple[str, ...]:
    risk_flags: list[str] = []

    if evidence.total_trade_count < (2 * thresholds.min_trade_count):
        risk_flags.append("low_trade_count_margin")

    if evidence.win_rate is not None and evidence.win_rate <= (thresholds.min_win_rate + 0.05):
        risk_flags.append("marginal_win_rate")

    if (
        evidence.average_return is not None
        and evidence.average_return <= (thresholds.min_average_return + 0.005)
    ):
        risk_flags.append("marginal_average_return")

    if evidence.worst_return is not None and evidence.worst_return <= -0.10:
        risk_flags.append("large_worst_loss")

    if evidence.completed_experiment_count <= thresholds.min_completed_experiments:
        risk_flags.append("limited_experiment_count")

    if hypothesis.parent_hypothesis_id is not None or hypothesis.lineage_hypothesis_ids:
        risk_flags.append("parent_or_lineage_context")

    return tuple(risk_flags)


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
        risk_flags = (
            _build_candidate_risk_flags(
                hypothesis=hypothesis,
                evidence=evidence,
                thresholds=thresholds,
            )
            if decision == PromotionCandidateDecision.CANDIDATE
            else ()
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
                best_return=evidence.best_return,
                worst_return=evidence.worst_return,
                latest_review_action=(latest_review.recommendation if latest_review is not None else None),
                latest_review_confidence=(latest_review.confidence if latest_review is not None else None),
                latest_review_rationale=(latest_review.rationale if latest_review is not None else None),
                review_current=(freshness.review_freshness == ReviewFreshnessStatus.CURRENT),
                has_lineage_context=bool(
                    hypothesis.parent_hypothesis_id is not None or hypothesis.lineage_hypothesis_ids
                ),
                risk_flags=risk_flags,
                failed_checks=failed_checks_tuple,
                rationale=rationale,
            )
        )

    return evaluations