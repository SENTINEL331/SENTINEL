"""Demo trade queue domain model for append-only local queue entries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DemoTradeQueueStatus(str, Enum):
    """Allowed lifecycle states for a demo trade queue item."""

    QUEUED = "queued"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    COMPLETED = "completed"


_ALLOWED_REQUESTED_ACTION = "prepare_demo_order"


@dataclass(frozen=True, slots=True)
class DemoTradeQueueItem:
    """Append-only queue entry created for an eligible demo trade candidate."""

    queue_item_id: str
    symbol: str
    demo_trade_candidate_id: str
    source_hypothesis_id: str
    created_at: datetime = field(default_factory=_utc_now)
    status: DemoTradeQueueStatus = DemoTradeQueueStatus.QUEUED
    demo_only: bool = True
    queue_reason: str = ""
    risk_summary: str = ""
    requested_action: str = _ALLOWED_REQUESTED_ACTION
    created_by: str = ""

    def __post_init__(self) -> None:
        if not self.queue_item_id:
            raise ValueError("queue_item_id is required")

        if not self.symbol:
            raise ValueError("symbol is required")

        if not self.demo_trade_candidate_id:
            raise ValueError("demo_trade_candidate_id is required")

        if not self.source_hypothesis_id:
            raise ValueError("source_hypothesis_id is required")

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")

        if not isinstance(self.status, DemoTradeQueueStatus):
            raise ValueError("status must be allowed")

        if not self.demo_only:
            raise ValueError("demo_only must be true")

        if not self.queue_reason:
            raise ValueError("queue_reason is required")

        if not self.risk_summary:
            raise ValueError("risk_summary is required")

        if self.requested_action != _ALLOWED_REQUESTED_ACTION:
            raise ValueError("requested_action must be prepare_demo_order")

        if not self.created_by:
            raise ValueError("created_by is required")

    @property
    def id(self) -> str:
        return self.queue_item_id