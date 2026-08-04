"""Deterministic lifecycle recommendation policy for hypotheses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable

from research.hypothesis import Hypothesis, HypothesisStatus
from research.hypothesis_evaluation import HypothesisEvidenceStatus, HypothesisEvidenceSummary
from research.hypothesis_review import HypothesisReview, HypothesisReviewRecommendation


class HypothesisLifecycleAction(str, Enum):
    """Supported recommendation-only lifecycle actions."""

    NO_ACTION = "no_action"
    NEEDS_MORE_TESTS = "needs_more_tests"
    REFINE_CANDIDATE = "refine_candidate"
    RETIRE_CANDIDATE = "retire_candidate"
    SUPERSEDE_CANDIDATE = "supersede_candidate"


@dataclass(frozen=True, slots=True)
class HypothesisLifecycleRecommendation:
    """Deterministic recommendation for one hypothesis lifecycle decision."""

    hypothesis_id: str
    hypothesis_title: str
    current_status: HypothesisStatus
    evidence_status: HypothesisEvidenceStatus
    completed_experiment_count: int
    zero_trade_completed_experiment_count: int
    total_trade_count: int
    action: HypothesisLifecycleAction
    rationale: str
    review_id: str | None = None
    review_recommendation: HypothesisReviewRecommendation | None = None
    review_confidence: float | None = None


_MIN_RETIRE_COMPLETED_EXPERIMENTS = 2
_MIN_RETIRE_TOTAL_TRADES = 20
_REPEATED_ZERO_TRADE_THRESHOLD = 2


def select_latest_hypothesis_reviews(
    hypothesis_reviews: Iterable[HypothesisReview],
) -> dict[str, HypothesisReview]:
    """Select latest review per hypothesis with deterministic tie-breaking."""

    hypothesis_reviews = list(hypothesis_reviews)

    def _sort_key(indexed_review):
        index, review = indexed_review
        created_at = getattr(review, "created_at", None)
        has_created_at = 1 if created_at is not None else 0
        comparable_created_at = created_at
        if comparable_created_at is None:
            comparable_created_at = datetime.min.replace(tzinfo=timezone.utc)

        # Stable deterministic ordering:
        # 1) created_at descending (via last-write-wins over ascending sort)
        # 2) original list position descending for created_at ties.
        return (
            has_created_at,
            comparable_created_at,
            index,
        )

    latest_reviews: dict[str, HypothesisReview] = {}

    indexed_reviews = list(enumerate(hypothesis_reviews))
    for _, review in sorted(indexed_reviews, key=_sort_key):
        latest_reviews[review.hypothesis_id] = review

    return latest_reviews


def _is_mature_weak_evidence(summary: HypothesisEvidenceSummary) -> bool:
    return (
        summary.evidence_status == HypothesisEvidenceStatus.WEAK
        and summary.completed_experiment_count >= _MIN_RETIRE_COMPLETED_EXPERIMENTS
        and summary.total_trade_count >= _MIN_RETIRE_TOTAL_TRADES
    )


def _base_action_from_evidence(
    summary: HypothesisEvidenceSummary,
) -> tuple[HypothesisLifecycleAction, str]:
    if summary.evidence_status == HypothesisEvidenceStatus.UNTESTED:
        return (
            HypothesisLifecycleAction.NEEDS_MORE_TESTS,
            "Untested hypothesis requires initial evidence.",
        )

    if summary.evidence_status == HypothesisEvidenceStatus.INSUFFICIENT_DATA:
        if summary.zero_trade_completed_experiment_count >= _REPEATED_ZERO_TRADE_THRESHOLD:
            return (
                HypothesisLifecycleAction.REFINE_CANDIDATE,
                "Insufficient data with repeated zero-trade completed experiments suggests setup refinement.",
            )

        return (
            HypothesisLifecycleAction.NEEDS_MORE_TESTS,
            "Insufficient data requires additional completed experiments.",
        )

    if summary.evidence_status == HypothesisEvidenceStatus.PROMISING:
        return (
            HypothesisLifecycleAction.NO_ACTION,
            "Promising evidence suggests maintaining current hypothesis unchanged.",
        )

    if summary.evidence_status == HypothesisEvidenceStatus.MIXED:
        return (
            HypothesisLifecycleAction.NEEDS_MORE_TESTS,
            "Mixed evidence requires additional testing before lifecycle changes.",
        )

    if _is_mature_weak_evidence(summary):
        return (
            HypothesisLifecycleAction.RETIRE_CANDIDATE,
            "Weak evidence with sufficient completed experiments and trade sample suggests retirement.",
        )

    return (
        HypothesisLifecycleAction.NEEDS_MORE_TESTS,
        "Weak evidence lacks sufficient sample size for retirement recommendation.",
    )


def _apply_review_guardrails(
    base_action: HypothesisLifecycleAction,
    base_rationale: str,
    summary: HypothesisEvidenceSummary,
    latest_review: HypothesisReview | None,
) -> tuple[HypothesisLifecycleAction, str]:
    if latest_review is None:
        return base_action, base_rationale

    recommendation = latest_review.recommendation

    if recommendation == HypothesisReviewRecommendation.RETIRE and _is_mature_weak_evidence(summary):
        return (
            HypothesisLifecycleAction.RETIRE_CANDIDATE,
            "Latest AI review supports retirement and deterministic weak-evidence thresholds are met.",
        )

    if (
        recommendation == HypothesisReviewRecommendation.REFINE
        and base_action == HypothesisLifecycleAction.RETIRE_CANDIDATE
    ):
        return (
            HypothesisLifecycleAction.SUPERSEDE_CANDIDATE,
            "Latest AI review suggests refine while evidence is mature-weak; consider superseding with a new child hypothesis.",
        )

    if (
        recommendation == HypothesisReviewRecommendation.NEEDS_MORE_TESTS
        and base_action == HypothesisLifecycleAction.NO_ACTION
        and summary.evidence_status != HypothesisEvidenceStatus.PROMISING
    ):
        return (
            HypothesisLifecycleAction.NEEDS_MORE_TESTS,
            "Latest AI review requests more tests and evidence is not conclusively promising.",
        )

    return base_action, base_rationale


def recommend_hypothesis_lifecycle_actions(
    hypotheses: Iterable[Hypothesis],
    evidence_summaries: Iterable[HypothesisEvidenceSummary],
    latest_reviews_by_hypothesis_id: dict[str, HypothesisReview] | None = None,
) -> list[HypothesisLifecycleRecommendation]:
    """Return deterministic lifecycle recommendations without mutating hypotheses."""

    summary_by_hypothesis_id = {
        summary.hypothesis_id: summary
        for summary in evidence_summaries
    }
    latest_reviews_by_hypothesis_id = latest_reviews_by_hypothesis_id or {}

    recommendations: list[HypothesisLifecycleRecommendation] = []

    for hypothesis in hypotheses:
        summary = summary_by_hypothesis_id.get(hypothesis.hypothesis_id)
        if summary is None:
            summary = HypothesisEvidenceSummary(
                hypothesis_id=hypothesis.hypothesis_id,
                hypothesis_title=hypothesis.title,
                completed_experiment_count=0,
                zero_trade_completed_experiment_count=0,
                total_trade_count=0,
                average_return=None,
                win_rate=None,
                best_return=None,
                worst_return=None,
                evidence_status=HypothesisEvidenceStatus.UNTESTED,
            )

        latest_review = latest_reviews_by_hypothesis_id.get(hypothesis.hypothesis_id)

        base_action, base_rationale = _base_action_from_evidence(summary)
        action, rationale = _apply_review_guardrails(
            base_action=base_action,
            base_rationale=base_rationale,
            summary=summary,
            latest_review=latest_review,
        )

        recommendations.append(
            HypothesisLifecycleRecommendation(
                hypothesis_id=hypothesis.hypothesis_id,
                hypothesis_title=hypothesis.title,
                current_status=hypothesis.status,
                evidence_status=summary.evidence_status,
                completed_experiment_count=summary.completed_experiment_count,
                zero_trade_completed_experiment_count=summary.zero_trade_completed_experiment_count,
                total_trade_count=summary.total_trade_count,
                action=action,
                rationale=rationale,
                review_id=(latest_review.review_id if latest_review is not None else None),
                review_recommendation=(
                    latest_review.recommendation if latest_review is not None else None
                ),
                review_confidence=(latest_review.confidence if latest_review is not None else None),
            )
        )

    return recommendations
