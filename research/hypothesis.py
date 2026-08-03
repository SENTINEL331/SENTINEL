"""Hypothesis domain model."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _touch_timestamp(timestamp: datetime | None) -> datetime:
    if timestamp is None:
        return _utc_now()

    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")

    return timestamp


class HypothesisStatus(str, Enum):
    """Scientific lifecycle states for a hypothesis."""

    PROPOSED = "proposed"
    ACTIVE = "active"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    BLOCKED = "blocked"
    INACTIVE = "inactive"
    SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class Hypothesis:
    """Immutable domain record for a falsifiable research hypothesis."""

    hypothesis_id: str
    symbol: str
    title: str
    description: str
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    confidence: float = 0.0
    source_observation_ids: tuple[str, ...] = field(default_factory=tuple)
    parent_hypothesis_id: str | None = None
    lineage_hypothesis_ids: tuple[str, ...] = field(default_factory=tuple)
    experiment_refs: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def __post_init__(self) -> None:
        if not self.hypothesis_id:
            raise ValueError("hypothesis_id is required")

        if not self.symbol:
            raise ValueError("symbol is required")

        if not self.title:
            raise ValueError("title is required")

        if not self.description:
            raise ValueError("description is required")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")

        if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
            raise ValueError("updated_at must be timezone-aware")

        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not be earlier than created_at")

    @property
    def id(self) -> str:
        return self.hypothesis_id

    @property
    def observations(self) -> tuple[str, ...]:
        return self.source_observation_ids

    @property
    def experiments(self) -> tuple[str, ...]:
        return self.experiment_refs

    @property
    def created(self) -> str:
        return self.created_at.isoformat()

    @property
    def updated(self) -> str:
        return self.updated_at.isoformat()

    def with_status(
        self,
        status: HypothesisStatus,
        updated_at: datetime | None = None,
    ) -> Hypothesis:
        return replace(self, status=status, updated_at=_touch_timestamp(updated_at))

    def with_confidence(
        self,
        confidence: float,
        updated_at: datetime | None = None,
    ) -> Hypothesis:
        return replace(
            self,
            confidence=confidence,
            updated_at=_touch_timestamp(updated_at),
        )

    def add_source_observation(
        self,
        observation_id: str,
        updated_at: datetime | None = None,
    ) -> Hypothesis:
        if not observation_id:
            raise ValueError("observation_id is required")

        return replace(
            self,
            source_observation_ids=self.source_observation_ids + (observation_id,),
            updated_at=_touch_timestamp(updated_at),
        )

    def add_experiment_reference(
        self,
        experiment_ref: str,
        updated_at: datetime | None = None,
    ) -> Hypothesis:
        if not experiment_ref:
            raise ValueError("experiment_ref is required")

        return replace(
            self,
            experiment_refs=self.experiment_refs + (experiment_ref,),
            updated_at=_touch_timestamp(updated_at),
        )

    def with_parent(
        self,
        parent_hypothesis_id: str,
        ancestor_ids: tuple[str, ...] = (),
        updated_at: datetime | None = None,
    ) -> Hypothesis:
        if not parent_hypothesis_id:
            raise ValueError("parent_hypothesis_id is required")

        lineage = ancestor_ids + (parent_hypothesis_id,)

        return replace(
            self,
            parent_hypothesis_id=parent_hypothesis_id,
            lineage_hypothesis_ids=lineage,
            updated_at=_touch_timestamp(updated_at),
        )