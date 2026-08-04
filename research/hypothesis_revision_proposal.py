"""Hypothesis revision proposal domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from research.hypothesis_lifecycle import HypothesisLifecycleAction


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HypothesisRevisionProposalType(str, Enum):
    """Supported proposal record types for append-only hypothesis revisions."""

    CREATE_CHILD_HYPOTHESIS = "create_child_hypothesis"
    REQUEST_MORE_TESTS = "request_more_tests"
    NO_REVISION = "no_revision"


@dataclass(frozen=True, slots=True)
class HypothesisRevisionProposal:
    """Immutable proposal record for potential future hypothesis revision work."""

    proposal_id: str
    symbol: str
    parent_hypothesis_id: str
    source_review_id: str | None
    lifecycle_action: HypothesisLifecycleAction
    proposal_type: HypothesisRevisionProposalType
    proposed_title: str
    proposed_description: str
    rationale: str
    confidence: float
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.proposal_id:
            raise ValueError("proposal_id is required")

        if not self.symbol:
            raise ValueError("symbol is required")

        if not self.parent_hypothesis_id:
            raise ValueError("parent_hypothesis_id is required")

        if not self.rationale:
            raise ValueError("rationale is required")

        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise ValueError("confidence must be numeric")

        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")

        if self.proposal_type == HypothesisRevisionProposalType.CREATE_CHILD_HYPOTHESIS:
            if not self.proposed_title:
                raise ValueError("proposed_title is required for create_child_hypothesis")

            if not self.proposed_description:
                raise ValueError("proposed_description is required for create_child_hypothesis")

    @property
    def id(self) -> str:
        return self.proposal_id
