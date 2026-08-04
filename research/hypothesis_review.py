"""Hypothesis review domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HypothesisReviewRecommendation(str, Enum):
    """Allowed deterministic recommendation values for hypothesis review."""

    KEEP = "keep"
    REFINE = "refine"
    RETIRE = "retire"
    NEEDS_MORE_TESTS = "needs_more_tests"


@dataclass(frozen=True, slots=True)
class HypothesisReview:
    """Immutable AI recommendation record for one hypothesis."""

    review_id: str
    hypothesis_id: str
    symbol: str
    recommendation: HypothesisReviewRecommendation
    rationale: str
    confidence: float
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.review_id:
            raise ValueError("review_id is required")

        if not self.hypothesis_id:
            raise ValueError("hypothesis_id is required")

        if not self.symbol:
            raise ValueError("symbol is required")

        if not self.rationale:
            raise ValueError("rationale is required")

        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise ValueError("confidence must be numeric")

        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")

    @property
    def id(self) -> str:
        return self.review_id