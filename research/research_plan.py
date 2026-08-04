"""Deterministic research plan model and planner helper."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable

from research.experiment import ExperimentRequest, ExperimentRequestStatus
from research.experiment_result import ExperimentResult, ExperimentResultStatus
from research.hypothesis import Hypothesis
from research.hypothesis_evaluation import HypothesisEvidenceStatus, HypothesisEvidenceSummary
from research.hypothesis_lifecycle import HypothesisLifecycleAction, HypothesisLifecycleRecommendation
from research.hypothesis_revision_application import HypothesisRevisionApplication
from research.hypothesis_revision_application import HypothesisRevisionApplicationStatus
from research.hypothesis_revision_proposal import HypothesisRevisionProposal
from research.hypothesis_review import HypothesisReview
from research.hypothesis_review import HypothesisReviewRecommendation


class ResearchPlanAction(str, Enum):
    """Deterministic next-step research actions."""

    GENERATE_EXPERIMENT_REQUEST = "generate_experiment_request"
    GENERATE_HYPOTHESIS_REVIEW = "generate_hypothesis_review"
    GENERATE_REVISION_PROPOSAL = "generate_revision_proposal"
    APPLY_REVISION_PROPOSAL_CANDIDATE = "apply_revision_proposal_candidate"
    MONITOR_EXISTING_CHILD = "monitor_existing_child"
    SKIP_PARENT_REFINED = "skip_parent_refined"
    NO_ACTION = "no_action"


class ResearchPlanPriority(str, Enum):
    """Relative urgency labels for deterministic research planning."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class ResearchPlanItem:
    """One deterministic next-step recommendation for a hypothesis."""

    symbol: str
    hypothesis_id: str
    hypothesis_title: str
    recommended_action: ResearchPlanAction
    priority: ResearchPlanPriority
    reason: str
    parent_hypothesis_id: str | None = None
    evidence_status: HypothesisEvidenceStatus | None = None
    lifecycle_action: HypothesisLifecycleAction | None = None
    latest_review_recommendation: HypothesisReviewRecommendation | None = None
    related_proposal_id: str | None = None
    related_child_hypothesis_id: str | None = None


@dataclass(frozen=True, slots=True)
class ResearchPlan:
    """Immutable symbol-level research planning output."""

    symbol: str
    created_at: datetime = field(default_factory=_utc_now)
    items: tuple[ResearchPlanItem, ...] = field(default_factory=tuple)


def _select_latest_experiment_result_time_by_hypothesis_id(
    experiment_results: Iterable[ExperimentResult],
) -> dict[str, datetime]:
    latest_times: dict[str, datetime] = {}

    for result in experiment_results:
        if result.status != ExperimentResultStatus.COMPLETED:
            continue

        completed_at = result.completed_at or result.updated_at
        if completed_at is None:
            continue

        current = latest_times.get(result.hypothesis_id)
        if current is None or completed_at > current:
            latest_times[result.hypothesis_id] = completed_at

    return latest_times


def _select_latest_proposal_by_parent_hypothesis_id(
    revision_proposals: Iterable[HypothesisRevisionProposal],
) -> dict[str, HypothesisRevisionProposal]:
    latest_by_parent: dict[str, HypothesisRevisionProposal] = {}

    for proposal in revision_proposals:
        existing = latest_by_parent.get(proposal.parent_hypothesis_id)
        if existing is None:
            latest_by_parent[proposal.parent_hypothesis_id] = proposal
            continue

        existing_created_at = existing.created_at
        if proposal.created_at > existing_created_at:
            latest_by_parent[proposal.parent_hypothesis_id] = proposal
            continue

        if proposal.created_at == existing_created_at:
            # Preserve later list entries on exact timestamp ties.
            latest_by_parent[proposal.parent_hypothesis_id] = proposal

    return latest_by_parent


def _select_latest_application_by_proposal_id(
    revision_applications: Iterable[HypothesisRevisionApplication],
) -> dict[str, HypothesisRevisionApplication]:
    latest_by_proposal_id: dict[str, HypothesisRevisionApplication] = {}

    for application in revision_applications:
        existing = latest_by_proposal_id.get(application.proposal_id)
        if existing is None or application.created_at >= existing.created_at:
            latest_by_proposal_id[application.proposal_id] = application

    return latest_by_proposal_id


def _select_latest_child_by_parent_hypothesis_id(
    hypotheses: Iterable[Hypothesis],
) -> dict[str, Hypothesis]:
    latest_children: dict[str, Hypothesis] = {}

    for hypothesis in hypotheses:
        if hypothesis.parent_hypothesis_id is None:
            continue

        existing = latest_children.get(hypothesis.parent_hypothesis_id)
        if existing is None or hypothesis.created_at >= existing.created_at:
            latest_children[hypothesis.parent_hypothesis_id] = hypothesis

    return latest_children


def _has_open_experiment_request(
    hypothesis_id: str,
    experiment_requests: Iterable[ExperimentRequest],
) -> bool:
    for request in experiment_requests:
        if request.hypothesis_id != hypothesis_id:
            continue

        if request.status in {
            ExperimentRequestStatus.PROPOSED,
            ExperimentRequestStatus.ACCEPTED,
            ExperimentRequestStatus.QUEUED,
            ExperimentRequestStatus.RUNNING,
        }:
            return True

    return False


def _completed_result_count_by_hypothesis_id(
    experiment_results: Iterable[ExperimentResult],
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for result in experiment_results:
        if result.status != ExperimentResultStatus.COMPLETED:
            continue

        counts[result.hypothesis_id] = counts.get(result.hypothesis_id, 0) + 1

    return counts


def _build_item(
    *,
    symbol: str,
    hypothesis: Hypothesis,
    recommended_action: ResearchPlanAction,
    priority: ResearchPlanPriority,
    reason: str,
    evidence_status: HypothesisEvidenceStatus | None = None,
    lifecycle_action: HypothesisLifecycleAction | None = None,
    latest_review_recommendation: HypothesisReviewRecommendation | None = None,
    related_proposal_id: str | None = None,
    related_child_hypothesis_id: str | None = None,
) -> ResearchPlanItem:
    return ResearchPlanItem(
        symbol=symbol,
        hypothesis_id=hypothesis.hypothesis_id,
        hypothesis_title=hypothesis.title,
        recommended_action=recommended_action,
        priority=priority,
        reason=reason,
        parent_hypothesis_id=hypothesis.parent_hypothesis_id,
        evidence_status=evidence_status,
        lifecycle_action=lifecycle_action,
        latest_review_recommendation=latest_review_recommendation,
        related_proposal_id=related_proposal_id,
        related_child_hypothesis_id=related_child_hypothesis_id,
    )


def build_research_plan(
    symbol: str,
    hypotheses: Iterable[Hypothesis],
    experiment_requests: Iterable[ExperimentRequest],
    experiment_results: Iterable[ExperimentResult],
    evidence_summaries: Iterable[HypothesisEvidenceSummary],
    latest_reviews_by_hypothesis_id: dict[str, HypothesisReview],
    lifecycle_recommendations: Iterable[HypothesisLifecycleRecommendation],
    revision_proposals: Iterable[HypothesisRevisionProposal],
    revision_applications: Iterable[HypothesisRevisionApplication],
    created_at: datetime | None = None,
) -> ResearchPlan:
    """Build a conservative deterministic research plan for one symbol."""

    created_at = created_at or _utc_now()
    hypotheses = list(hypotheses)
    experiment_requests = list(experiment_requests)
    experiment_results = list(experiment_results)
    evidence_summaries = list(evidence_summaries)
    lifecycle_recommendations = list(lifecycle_recommendations)
    revision_proposals = list(revision_proposals)
    revision_applications = list(revision_applications)

    evidence_by_hypothesis_id = {
        summary.hypothesis_id: summary
        for summary in evidence_summaries
    }
    lifecycle_by_hypothesis_id = {
        recommendation.hypothesis_id: recommendation
        for recommendation in lifecycle_recommendations
    }
    review_by_hypothesis_id = dict(latest_reviews_by_hypothesis_id)
    latest_result_time_by_hypothesis_id = _select_latest_experiment_result_time_by_hypothesis_id(
        experiment_results
    )
    completed_result_count_by_hypothesis_id = _completed_result_count_by_hypothesis_id(
        experiment_results
    )
    latest_proposal_by_parent_hypothesis_id = _select_latest_proposal_by_parent_hypothesis_id(
        revision_proposals
    )
    latest_application_by_proposal_id = _select_latest_application_by_proposal_id(
        revision_applications
    )
    latest_child_by_parent_hypothesis_id = _select_latest_child_by_parent_hypothesis_id(
        hypotheses
    )

    plan_items: list[ResearchPlanItem] = []

    for hypothesis in hypotheses:
        evidence = evidence_by_hypothesis_id.get(hypothesis.hypothesis_id)
        lifecycle = lifecycle_by_hypothesis_id.get(hypothesis.hypothesis_id)
        latest_review = review_by_hypothesis_id.get(hypothesis.hypothesis_id)
        latest_child = latest_child_by_parent_hypothesis_id.get(hypothesis.hypothesis_id)
        latest_proposal = latest_proposal_by_parent_hypothesis_id.get(hypothesis.hypothesis_id)
        latest_application = (
            latest_application_by_proposal_id.get(latest_proposal.proposal_id)
            if latest_proposal is not None
            else None
        )
        completed_result_count = completed_result_count_by_hypothesis_id.get(
            hypothesis.hypothesis_id,
            0,
        )
        open_request_exists = _has_open_experiment_request(
            hypothesis.hypothesis_id,
            experiment_requests,
        )
        latest_completed_result_time = latest_result_time_by_hypothesis_id.get(
            hypothesis.hypothesis_id
        )
        latest_review_time = latest_review.created_at if latest_review is not None else None

        if latest_child is not None and latest_child.source_revision_proposal_id is not None:
            plan_items.append(
                _build_item(
                    symbol=symbol,
                    hypothesis=hypothesis,
                    recommended_action=ResearchPlanAction.SKIP_PARENT_REFINED,
                    priority=ResearchPlanPriority.LOW,
                    reason=(
                        "parent hypothesis has an append-only child hypothesis; continue research on child instead"
                    ),
                    evidence_status=evidence.evidence_status if evidence is not None else None,
                    lifecycle_action=lifecycle.action if lifecycle is not None else None,
                    latest_review_recommendation=(
                        latest_review.recommendation if latest_review is not None else None
                    ),
                    related_child_hypothesis_id=latest_child.hypothesis_id,
                )
            )
            continue

        if completed_result_count > 0 and (
            latest_review_time is None
            or (latest_completed_result_time is not None and latest_completed_result_time > latest_review_time)
        ):
            plan_items.append(
                _build_item(
                    symbol=symbol,
                    hypothesis=hypothesis,
                    recommended_action=ResearchPlanAction.GENERATE_HYPOTHESIS_REVIEW,
                    priority=ResearchPlanPriority.MEDIUM,
                    reason=(
                        "completed experiment result is newer than the latest review"
                        if latest_review_time is not None
                        else "completed experiment results exist without a review"
                    ),
                    evidence_status=evidence.evidence_status if evidence is not None else None,
                    lifecycle_action=lifecycle.action if lifecycle is not None else None,
                    latest_review_recommendation=(
                        latest_review.recommendation if latest_review is not None else None
                    ),
                )
            )
            continue

        if hypothesis.parent_hypothesis_id is not None and completed_result_count == 0:
            plan_items.append(
                _build_item(
                    symbol=symbol,
                    hypothesis=hypothesis,
                    recommended_action=ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST,
                    priority=ResearchPlanPriority.HIGH,
                    reason="child hypothesis has not been tested yet",
                    evidence_status=evidence.evidence_status if evidence is not None else None,
                    lifecycle_action=lifecycle.action if lifecycle is not None else None,
                    latest_review_recommendation=(
                        latest_review.recommendation if latest_review is not None else None
                    ),
                    related_proposal_id=hypothesis.source_revision_proposal_id,
                    related_child_hypothesis_id=hypothesis.hypothesis_id,
                )
            )
            continue

        if (
            hypothesis.parent_hypothesis_id is not None
            and completed_result_count > 0
            and latest_review_time is not None
            and latest_completed_result_time is not None
            and latest_completed_result_time <= latest_review_time
        ):
            plan_items.append(
                _build_item(
                    symbol=symbol,
                    hypothesis=hypothesis,
                    recommended_action=ResearchPlanAction.MONITOR_EXISTING_CHILD,
                    priority=ResearchPlanPriority.LOW,
                    reason="child hypothesis has completed experiments and a current review; continue monitoring",
                    evidence_status=evidence.evidence_status if evidence is not None else None,
                    lifecycle_action=lifecycle.action if lifecycle is not None else None,
                    latest_review_recommendation=(
                        latest_review.recommendation if latest_review is not None else None
                    ),
                    related_child_hypothesis_id=hypothesis.hypothesis_id,
                )
            )
            continue

        if lifecycle is not None and lifecycle.action == HypothesisLifecycleAction.REFINE_CANDIDATE:
            if latest_proposal is None:
                plan_items.append(
                    _build_item(
                        symbol=symbol,
                        hypothesis=hypothesis,
                        recommended_action=ResearchPlanAction.GENERATE_REVISION_PROPOSAL,
                        priority=ResearchPlanPriority.HIGH,
                        reason="lifecycle recommendation is refine_candidate and no revision proposal exists",
                        evidence_status=evidence.evidence_status if evidence is not None else None,
                        lifecycle_action=lifecycle.action,
                        latest_review_recommendation=(
                            latest_review.recommendation if latest_review is not None else None
                        ),
                    )
                )
                continue

            if latest_application is None or latest_application.status != HypothesisRevisionApplicationStatus.APPLIED:
                plan_items.append(
                    _build_item(
                        symbol=symbol,
                        hypothesis=hypothesis,
                        recommended_action=ResearchPlanAction.APPLY_REVISION_PROPOSAL_CANDIDATE,
                        priority=ResearchPlanPriority.MEDIUM,
                        reason="proposal exists but requires explicit manual application",
                        evidence_status=evidence.evidence_status if evidence is not None else None,
                        lifecycle_action=lifecycle.action,
                        latest_review_recommendation=(
                            latest_review.recommendation if latest_review is not None else None
                        ),
                        related_proposal_id=latest_proposal.proposal_id,
                        related_child_hypothesis_id=(
                            latest_application.child_hypothesis_id if latest_application is not None else None
                        ),
                    )
                )
                continue

            plan_items.append(
                _build_item(
                    symbol=symbol,
                    hypothesis=hypothesis,
                    recommended_action=ResearchPlanAction.SKIP_PARENT_REFINED,
                    priority=ResearchPlanPriority.LOW,
                    reason="revision proposal has already been applied; continue with the child hypothesis",
                    evidence_status=evidence.evidence_status if evidence is not None else None,
                    lifecycle_action=lifecycle.action,
                    latest_review_recommendation=(
                        latest_review.recommendation if latest_review is not None else None
                    ),
                    related_proposal_id=latest_proposal.proposal_id,
                    related_child_hypothesis_id=latest_application.child_hypothesis_id,
                )
            )
            continue

        if lifecycle is not None and lifecycle.action == HypothesisLifecycleAction.NEEDS_MORE_TESTS:
            if open_request_exists:
                plan_items.append(
                    _build_item(
                        symbol=symbol,
                        hypothesis=hypothesis,
                        recommended_action=ResearchPlanAction.NO_ACTION,
                        priority=ResearchPlanPriority.LOW,
                        reason="experiment request already exists or evidence is pending",
                        evidence_status=evidence.evidence_status if evidence is not None else None,
                        lifecycle_action=lifecycle.action,
                        latest_review_recommendation=(
                            latest_review.recommendation if latest_review is not None else None
                        ),
                    )
                )
            else:
                plan_items.append(
                    _build_item(
                        symbol=symbol,
                        hypothesis=hypothesis,
                        recommended_action=ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST,
                        priority=ResearchPlanPriority.MEDIUM,
                        reason="needs_more_tests hypothesis has no open or executable experiment request",
                        evidence_status=evidence.evidence_status if evidence is not None else None,
                        lifecycle_action=lifecycle.action,
                        latest_review_recommendation=(
                            latest_review.recommendation if latest_review is not None else None
                        ),
                    )
                )
            continue

        if evidence is not None and evidence.evidence_status == HypothesisEvidenceStatus.UNTESTED:
            if open_request_exists:
                plan_items.append(
                    _build_item(
                        symbol=symbol,
                        hypothesis=hypothesis,
                        recommended_action=ResearchPlanAction.NO_ACTION,
                        priority=ResearchPlanPriority.LOW,
                        reason="untested hypothesis already has an open experiment request",
                        evidence_status=evidence.evidence_status,
                        lifecycle_action=lifecycle.action if lifecycle is not None else None,
                        latest_review_recommendation=(
                            latest_review.recommendation if latest_review is not None else None
                        ),
                    )
                )
            else:
                plan_items.append(
                    _build_item(
                        symbol=symbol,
                        hypothesis=hypothesis,
                        recommended_action=ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST,
                        priority=ResearchPlanPriority.MEDIUM,
                        reason="untested hypothesis requires initial experiment evidence",
                        evidence_status=evidence.evidence_status,
                        lifecycle_action=lifecycle.action if lifecycle is not None else None,
                        latest_review_recommendation=(
                            latest_review.recommendation if latest_review is not None else None
                        ),
                    )
                )
            continue

        if completed_result_count > 0:
            plan_items.append(
                _build_item(
                    symbol=symbol,
                    hypothesis=hypothesis,
                    recommended_action=ResearchPlanAction.NO_ACTION,
                    priority=ResearchPlanPriority.LOW,
                    reason="completed evidence is current and no deterministic next step is required",
                    evidence_status=evidence.evidence_status if evidence is not None else None,
                    lifecycle_action=lifecycle.action if lifecycle is not None else None,
                    latest_review_recommendation=(
                        latest_review.recommendation if latest_review is not None else None
                    ),
                )
            )
            continue

        plan_items.append(
            _build_item(
                symbol=symbol,
                hypothesis=hypothesis,
                recommended_action=ResearchPlanAction.GENERATE_EXPERIMENT_REQUEST,
                priority=ResearchPlanPriority.MEDIUM,
                reason="untested hypothesis requires initial experiment evidence",
                evidence_status=evidence.evidence_status if evidence is not None else None,
                lifecycle_action=lifecycle.action if lifecycle is not None else None,
                latest_review_recommendation=(
                    latest_review.recommendation if latest_review is not None else None
                ),
            )
        )

    return ResearchPlan(
        symbol=symbol,
        created_at=created_at,
        items=tuple(plan_items),
    )