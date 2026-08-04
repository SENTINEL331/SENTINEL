"""Hypothesis revision application domain model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HypothesisRevisionApplicationStatus(str, Enum):
    """Outcomes for explicit manual proposal application attempts."""

    DRY_RUN = "dry_run"
    APPLIED = "applied"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class HypothesisRevisionApplication:
    """Immutable append-only event record for proposal-application attempts."""

    application_id: str
    proposal_id: str
    symbol: str
    parent_hypothesis_id: str
    status: HypothesisRevisionApplicationStatus
    apply_mode: bool
    child_hypothesis_id: str | None = None
    message: str = ""
    created_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.application_id:
            raise ValueError("application_id is required")

        if not self.proposal_id:
            raise ValueError("proposal_id is required")

        if not self.symbol:
            raise ValueError("symbol is required")

        if not self.parent_hypothesis_id:
            raise ValueError("parent_hypothesis_id is required")

        if self.child_hypothesis_id is not None and not self.child_hypothesis_id:
            raise ValueError("child_hypothesis_id must be non-empty when provided")

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")

    @property
    def id(self) -> str:
        return self.application_id
