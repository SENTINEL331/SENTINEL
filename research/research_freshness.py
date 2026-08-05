"""Deterministic freshness analysis for research artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Iterable

from research.experiment import ExperimentRequest
from research.experiment_result import ExperimentResult
from research.experiment_result import ExperimentResultStatus
from research.hypothesis import Hypothesis
from research.hypothesis_lifecycle import HypothesisLifecycleAction
from research.hypothesis_lifecycle import HypothesisLifecycleRecommendation
from research.hypothesis_review import HypothesisReview
from research.hypothesis_revision_proposal import HypothesisRevisionProposal


class ReviewFreshnessStatus(str, Enum):
    """Freshness states for review recency checks."""

    CURRENT = "current"
    STALE_AFTER_NEW_RESULT = "stale_after_new_result"
    STALE_AFTER_NEW_OBSERVATION = "stale_after_new_observation"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"


class ProposalFreshnessStatus(str, Enum):
    """Freshness states for revision proposal recency checks."""

    CURRENT = "current"
    STALE_AFTER_REVIEW = "stale_after_review"
    MISSING_FOR_REFINE_CANDIDATE = "missing_for_refine_candidate"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class ResearchFreshnessItem:
    """Freshness snapshot for one hypothesis."""

    hypothesis_id: str
    hypothesis_title: str
    latest_observation_at: datetime | None
    latest_completed_result_at: datetime | None
    latest_review_at: datetime | None
    latest_revision_proposal_at: datetime | None
    review_freshness: ReviewFreshnessStatus
    proposal_freshness: ProposalFreshnessStatus
    rationale: str


def _latest_datetime(values: Iterable[datetime | None]) -> datetime | None:
    latest_value: datetime | None = None

    for value in values:
        if value is None:
            continue

        if latest_value is None or value > latest_value:
            latest_value = value

    return latest_value


def _coerce_datetime(value: object) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        parsed_value = datetime.fromisoformat(value)
        if parsed_value.tzinfo is None or parsed_value.utcoffset() is None:
            return parsed_value.replace(tzinfo=timezone.utc)

        return parsed_value

    raise TypeError(f"Unsupported timestamp value: {type(value)!r}")


def _build_latest_review_by_hypothesis_id(
    hypothesis_reviews: Iterable[HypothesisReview],
) -> dict[str, HypothesisReview]:
    latest_by_hypothesis_id: dict[str, HypothesisReview] = {}

    for review in hypothesis_reviews:
        existing = latest_by_hypothesis_id.get(review.hypothesis_id)
        if existing is None or review.created_at >= existing.created_at:
            latest_by_hypothesis_id[review.hypothesis_id] = review

    return latest_by_hypothesis_id


def _build_latest_proposal_by_hypothesis_id(
    revision_proposals: Iterable[HypothesisRevisionProposal],
) -> dict[str, HypothesisRevisionProposal]:
    latest_by_hypothesis_id: dict[str, HypothesisRevisionProposal] = {}

    for proposal in revision_proposals:
        existing = latest_by_hypothesis_id.get(proposal.parent_hypothesis_id)
        if existing is None or proposal.created_at >= existing.created_at:
            latest_by_hypothesis_id[proposal.parent_hypothesis_id] = proposal

    return latest_by_hypothesis_id


def _build_completed_result_time_by_hypothesis_id(
    experiment_results: Iterable[ExperimentResult],
) -> dict[str, datetime]:
    latest_by_hypothesis_id: dict[str, datetime] = {}

    for result in experiment_results:
        if result.status != ExperimentResultStatus.COMPLETED or result.completed_at is None:
            continue

        existing = latest_by_hypothesis_id.get(result.hypothesis_id)
        if existing is None or result.completed_at >= existing:
            latest_by_hypothesis_id[result.hypothesis_id] = result.completed_at

    return latest_by_hypothesis_id


def _build_latest_observation_at(
    observations: Iterable[object],
) -> datetime | None:
    timestamps = []

    for observation in observations:
        created_at = getattr(observation, "created_at", None)
        if created_at is not None:
            timestamps.append(_coerce_datetime(created_at))
            continue

        effective_time = getattr(observation, "effective_time", None)
        if effective_time is not None:
            timestamps.append(_coerce_datetime(effective_time))

    return _latest_datetime(timestamps)


def _classify_review_freshness(
    *,
    latest_observation_at: datetime | None,
    latest_completed_result_at: datetime | None,
    latest_review_at: datetime | None,
) -> ReviewFreshnessStatus:
    if latest_observation_at is None and latest_completed_result_at is None:
        return ReviewFreshnessStatus.NOT_APPLICABLE

    if latest_completed_result_at is not None:
        if latest_review_at is None:
            return ReviewFreshnessStatus.MISSING

        if latest_completed_result_at > latest_review_at:
            return ReviewFreshnessStatus.STALE_AFTER_NEW_RESULT

        if latest_observation_at is not None and latest_observation_at > latest_review_at:
            return ReviewFreshnessStatus.STALE_AFTER_NEW_OBSERVATION

        return ReviewFreshnessStatus.CURRENT

    if latest_review_at is None:
        if latest_observation_at is not None:
            return ReviewFreshnessStatus.STALE_AFTER_NEW_OBSERVATION

        return ReviewFreshnessStatus.NOT_APPLICABLE

    if latest_observation_at is not None and latest_observation_at > latest_review_at:
        return ReviewFreshnessStatus.STALE_AFTER_NEW_OBSERVATION

    return ReviewFreshnessStatus.CURRENT


def _classify_proposal_freshness(
    *,
    lifecycle_action: HypothesisLifecycleAction,
    latest_review_at: datetime | None,
    latest_revision_proposal_at: datetime | None,
) -> ProposalFreshnessStatus:
    if lifecycle_action != HypothesisLifecycleAction.REFINE_CANDIDATE:
        return ProposalFreshnessStatus.NOT_APPLICABLE

    if latest_revision_proposal_at is None:
        return ProposalFreshnessStatus.MISSING_FOR_REFINE_CANDIDATE

    if latest_review_at is not None and latest_review_at > latest_revision_proposal_at:
        return ProposalFreshnessStatus.STALE_AFTER_REVIEW

    return ProposalFreshnessStatus.CURRENT


def build_research_freshness(
    *,
    hypotheses: Iterable[Hypothesis],
    observations: Iterable[object],
    experiment_requests: Iterable[ExperimentRequest],
    experiment_results: Iterable[ExperimentResult],
    hypothesis_reviews: Iterable[HypothesisReview],
    revision_proposals: Iterable[HypothesisRevisionProposal],
    lifecycle_recommendations: Iterable[HypothesisLifecycleRecommendation],
) -> list[ResearchFreshnessItem]:
    """Build deterministic freshness summaries for one symbol."""

    hypotheses = list(hypotheses)
    observations = list(observations)
    experiment_requests = list(experiment_requests)
    experiment_results = list(experiment_results)
    hypothesis_reviews = list(hypothesis_reviews)
    revision_proposals = list(revision_proposals)
    lifecycle_recommendations = list(lifecycle_recommendations)

    latest_observation_at = _build_latest_observation_at(observations)
    latest_completed_result_by_hypothesis_id = _build_completed_result_time_by_hypothesis_id(
        experiment_results
    )
    latest_review_by_hypothesis_id = _build_latest_review_by_hypothesis_id(hypothesis_reviews)
    latest_proposal_by_hypothesis_id = _build_latest_proposal_by_hypothesis_id(revision_proposals)
    lifecycle_by_hypothesis_id = {
        recommendation.hypothesis_id: recommendation
        for recommendation in lifecycle_recommendations
    }

    freshness_items: list[ResearchFreshnessItem] = []

    for hypothesis in hypotheses:
        latest_completed_result_at = latest_completed_result_by_hypothesis_id.get(
            hypothesis.hypothesis_id
        )
        latest_review = latest_review_by_hypothesis_id.get(hypothesis.hypothesis_id)
        latest_review_at = latest_review.created_at if latest_review is not None else None
        latest_proposal = latest_proposal_by_hypothesis_id.get(hypothesis.hypothesis_id)
        latest_revision_proposal_at = (
            latest_proposal.created_at if latest_proposal is not None else None
        )
        lifecycle_recommendation = lifecycle_by_hypothesis_id.get(hypothesis.hypothesis_id)
        lifecycle_action = (
            lifecycle_recommendation.action
            if lifecycle_recommendation is not None
            else HypothesisLifecycleAction.NO_ACTION
        )

        review_freshness = _classify_review_freshness(
            latest_observation_at=latest_observation_at,
            latest_completed_result_at=latest_completed_result_at,
            latest_review_at=latest_review_at,
        )
        proposal_freshness = _classify_proposal_freshness(
            lifecycle_action=lifecycle_action,
            latest_review_at=latest_review_at,
            latest_revision_proposal_at=latest_revision_proposal_at,
        )

        if review_freshness == ReviewFreshnessStatus.MISSING:
            rationale = "completed experiment results exist without a review"
        elif review_freshness == ReviewFreshnessStatus.STALE_AFTER_NEW_RESULT:
            rationale = "latest completed result is newer than the latest review"
        elif review_freshness == ReviewFreshnessStatus.STALE_AFTER_NEW_OBSERVATION:
            rationale = "latest observation is newer than the latest review"
        elif review_freshness == ReviewFreshnessStatus.CURRENT:
            rationale = "latest review is current relative to available observations and results"
        else:
            rationale = "no observation or completed result context is available"

        freshness_items.append(
            ResearchFreshnessItem(
                hypothesis_id=hypothesis.hypothesis_id,
                hypothesis_title=hypothesis.title,
                latest_observation_at=latest_observation_at,
                latest_completed_result_at=latest_completed_result_at,
                latest_review_at=latest_review_at,
                latest_revision_proposal_at=latest_revision_proposal_at,
                review_freshness=review_freshness,
                proposal_freshness=proposal_freshness,
                rationale=rationale,
            )
        )

    return freshness_items