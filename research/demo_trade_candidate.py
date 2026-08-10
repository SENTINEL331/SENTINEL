"""Demo trade candidate domain model and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DemoTradeCandidateStatus(str, Enum):
    """Lifecycle states for a demo trade candidate."""

    PROPOSED = "proposed"
    GATE_PASSED = "gate_passed"
    GATE_FAILED = "gate_failed"
    IN_DEMO = "in_demo"
    DEMO_COMPLETED = "demo_completed"
    PROMOTED = "promoted"
    REJECTED = "rejected"


_MAX_LOSS_PER_TRADE_CAP = 0.02
_MAX_PORTFOLIO_EXPOSURE_CAP = 0.10


@dataclass(frozen=True, slots=True)
class DemoTradeCandidate:
    """Append-only concrete demo-trading setup derived from a research candidate."""

    trade_candidate_id: str
    symbol: str
    source_hypothesis_id: str
    source_research_candidate_decision: str
    source_trade_candidate_id: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    status: DemoTradeCandidateStatus = DemoTradeCandidateStatus.PROPOSED
    entry_logic: str = ""
    exit_logic: str = ""
    invalidation_logic: str = ""
    maximum_holding_period: str = ""
    position_sizing_rule: str = ""
    max_loss_per_trade: float = 0.0
    max_portfolio_exposure: float = 0.0
    demo_only: bool = True
    monitoring_frequency: str = ""
    pause_conditions: tuple[str, ...] = field(default_factory=tuple)
    source_evidence_summary: Mapping[str, Any] = field(default_factory=dict)
    source_review_action: str | None = None
    source_review_confidence: float | None = None
    risk_flags: tuple[str, ...] = field(default_factory=tuple)
    gate_checked_at: datetime | None = None
    gate_decision: str | None = None
    failed_checks: tuple[str, ...] = field(default_factory=tuple)
    gate_rationale: str | None = None
    created_by: str = ""

    def __post_init__(self) -> None:
        if not self.trade_candidate_id:
            raise ValueError("trade_candidate_id is required")

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")

        if self.gate_checked_at is not None:
            if self.gate_checked_at.tzinfo is None or self.gate_checked_at.utcoffset() is None:
                raise ValueError("gate_checked_at must be timezone-aware")

        normalized_evidence = MappingProxyType(dict(self.source_evidence_summary))
        object.__setattr__(self, "source_evidence_summary", normalized_evidence)

    @property
    def id(self) -> str:
        return self.trade_candidate_id


def validate_demo_trade_candidate(candidate: DemoTradeCandidate) -> None:
    """Validate deterministic demo-trade candidate safety and completeness constraints."""

    if not candidate.source_hypothesis_id:
        raise ValueError("source_hypothesis_id is required")

    if not candidate.symbol:
        raise ValueError("symbol is required")

    if not candidate.entry_logic:
        raise ValueError("entry_logic is required")

    if not candidate.exit_logic:
        raise ValueError("exit_logic is required")

    if not candidate.invalidation_logic:
        raise ValueError("invalidation_logic is required")

    if not candidate.maximum_holding_period:
        raise ValueError("maximum_holding_period is required")

    if not candidate.position_sizing_rule:
        raise ValueError("position_sizing_rule is required")

    if not candidate.monitoring_frequency:
        raise ValueError("monitoring_frequency is required")

    if not candidate.demo_only:
        raise ValueError("demo_only must be true")

    if candidate.max_loss_per_trade <= 0:
        raise ValueError("max_loss_per_trade must be positive")

    if candidate.max_loss_per_trade > _MAX_LOSS_PER_TRADE_CAP:
        raise ValueError("max_loss_per_trade must not exceed 0.02")

    if candidate.max_portfolio_exposure <= 0:
        raise ValueError("max_portfolio_exposure must be positive")

    if candidate.max_portfolio_exposure > _MAX_PORTFOLIO_EXPOSURE_CAP:
        raise ValueError("max_portfolio_exposure must not exceed 0.10")

    if not isinstance(candidate.status, DemoTradeCandidateStatus):
        raise ValueError("status must be allowed")