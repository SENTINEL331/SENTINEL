"""Deterministic local demo order intent model and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256

from config import settings
from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import validate_demo_trade_candidate
from research.demo_trade_queue import DemoTradeQueueItem
from research.demo_trade_queue import DemoTradeQueueStatus


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DemoOrderIntentStatus(str, Enum):
    """Allowed lifecycle states for a local demo order intent."""

    PREPARED = "prepared"
    SUBMITTED = "submitted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    FILLED = "filled"
    COMPLETED = "completed"


_ALLOWED_SIDES = {"buy", "sell"}
_ALLOWED_ORDER_TYPES = {"market", "limit"}
_ALLOWED_TIF = {"day"}
_ALLOWED_STATUSES = {status.value for status in DemoOrderIntentStatus}


@dataclass(frozen=True, slots=True)
class DemoOrderIntent:
    """Deterministic local order preview built from a queued demo trade candidate."""

    order_intent_id: str
    symbol: str
    queue_item_id: str
    demo_trade_candidate_id: str
    source_hypothesis_id: str
    created_at: datetime = field(default_factory=_utc_now)
    status: DemoOrderIntentStatus = DemoOrderIntentStatus.PREPARED
    demo_only: bool = True
    side: str = "buy"
    order_type: str = "market"
    time_in_force: str = "day"
    notional: float | None = None
    quantity: float | None = None
    limit_price: float | None = None
    stop_price: float | None = None
    max_loss_per_trade: float = 0.0
    max_portfolio_exposure: float = 0.0
    intent_reason: str = ""
    created_by: str = ""

    def __post_init__(self) -> None:
        if not self.order_intent_id:
            raise ValueError("order_intent_id is required")

        if not self.symbol:
            raise ValueError("symbol is required")

        if not self.queue_item_id:
            raise ValueError("queue_item_id is required")

        if not self.demo_trade_candidate_id:
            raise ValueError("demo_trade_candidate_id is required")

        if not self.source_hypothesis_id:
            raise ValueError("source_hypothesis_id is required")

        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")

        normalized_status = self.status
        if isinstance(normalized_status, str):
            try:
                normalized_status = DemoOrderIntentStatus(normalized_status)
            except ValueError as exc:
                raise ValueError("status must be allowed") from exc
        if not isinstance(normalized_status, DemoOrderIntentStatus):
            raise ValueError("status must be allowed")
        object.__setattr__(self, "status", normalized_status)

        if not self.demo_only:
            raise ValueError("demo_only must be true")

        side_value = (self.side or "").casefold()
        if not side_value or side_value not in _ALLOWED_SIDES:
            raise ValueError("side must be buy or sell")
        object.__setattr__(self, "side", side_value)

        order_type_value = (self.order_type or "").casefold()
        if not order_type_value or order_type_value not in _ALLOWED_ORDER_TYPES:
            raise ValueError("order_type must be market or limit")
        object.__setattr__(self, "order_type", order_type_value)

        if self.time_in_force != "day":
            raise ValueError("time_in_force must be day")

        has_notional = self.notional is not None
        has_quantity = self.quantity is not None
        if has_notional and has_quantity:
            raise ValueError("notional and quantity cannot both be set")
        if not has_notional and not has_quantity:
            raise ValueError("notional or quantity is required")

        if self.notional is not None and self.notional <= 0:
            raise ValueError("notional must be positive")

        if self.notional is not None and self.notional > getattr(settings, "DEMO_MAX_ORDER_NOTIONAL", 100.0):
            raise ValueError("notional must be <= DEMO_MAX_ORDER_NOTIONAL")

        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("quantity must be positive")

        if getattr(settings, "BROKER_MODE", "").casefold() == "live":
            raise ValueError("live trading is not allowed")

        if getattr(settings, "DEMO_BROKER_MODE", "").casefold() == "live":
            raise ValueError("live trading is not allowed")

    @property
    def id(self) -> str:
        return self.order_intent_id


def validate_demo_order_intent(intent: DemoOrderIntent, storage=None) -> None:
    """Validate a deterministic local demo order intent."""

    if intent is None:
        raise ValueError("intent is required")

    if not intent.symbol:
        raise ValueError("symbol is required")

    if not intent.queue_item_id:
        raise ValueError("queue_item_id is required")

    if not intent.demo_trade_candidate_id:
        raise ValueError("demo_trade_candidate_id is required")

    if not intent.source_hypothesis_id:
        raise ValueError("source_hypothesis_id is required")

    if not intent.demo_only:
        raise ValueError("demo_only must be true")

    status_value = getattr(intent.status, "value", intent.status)
    if status_value not in _ALLOWED_STATUSES:
        raise ValueError("status must be allowed")

    if intent.side.casefold() not in _ALLOWED_SIDES:
        raise ValueError("side must be buy or sell")

    if intent.order_type.casefold() not in _ALLOWED_ORDER_TYPES:
        raise ValueError("order_type must be market or limit")

    if intent.time_in_force != "day":
        raise ValueError("time_in_force must be day")

    has_notional = intent.notional is not None
    has_quantity = intent.quantity is not None
    if has_notional and has_quantity:
        raise ValueError("notional and quantity cannot both be set")
    if not has_notional and not has_quantity:
        raise ValueError("notional or quantity is required")
    if has_notional:
        if intent.notional <= 0:
            raise ValueError("notional must be positive")
        if intent.notional > getattr(settings, "DEMO_MAX_ORDER_NOTIONAL", 100.0):
            raise ValueError("notional must be <= DEMO_MAX_ORDER_NOTIONAL")
    else:
        if intent.quantity <= 0:
            raise ValueError("quantity must be positive")

    if getattr(settings, "BROKER_MODE", "").casefold() == "live":
        raise ValueError("live trading is not allowed")

    if getattr(settings, "DEMO_BROKER_MODE", "").casefold() == "live":
        raise ValueError("live trading is not allowed")

    if storage is None:
        return

    queue_items = storage.load_demo_trade_queue_items(symbol=intent.symbol)
    queue_item = next(
        (item for item in queue_items if item.queue_item_id == intent.queue_item_id),
        None,
    )
    if queue_item is None:
        raise ValueError("queue item not found")
    if queue_item.status != DemoTradeQueueStatus.QUEUED:
        raise ValueError("queue item status must be queued")
    if not queue_item.demo_only:
        raise ValueError("queue item demo_only must be true")

    candidates = storage.load_demo_trade_candidates(symbol=intent.symbol)
    candidate = next(
        (item for item in candidates if item.trade_candidate_id == intent.demo_trade_candidate_id),
        None,
    )
    if candidate is None:
        raise ValueError("demo trade candidate not found")
    validate_demo_trade_candidate(candidate)
    if not candidate.demo_only:
        raise ValueError("demo_trade_candidate demo_only must be true")


def _new_order_intent_id(symbol: str, queue_item_id: str, demo_trade_candidate_id: str, created_at: datetime) -> str:
    digest = sha256(
        f"{symbol}|{queue_item_id}|{demo_trade_candidate_id}|prepared|{created_at.isoformat()}".encode("utf-8")
    ).hexdigest()[:12]
    return f"doi-{symbol}-{digest}"


def build_demo_order_intent_from_queue_item(
    *,
    queue_item: DemoTradeQueueItem,
    candidate: DemoTradeCandidate,
    created_at: datetime | None = None,
    created_by: str = "sentinel",
) -> DemoOrderIntent:
    """Create a prepared demo order intent from a valid queued demo candidate."""

    if not isinstance(queue_item, DemoTradeQueueItem):
        raise TypeError("queue_item must be a DemoTradeQueueItem")
    if not isinstance(candidate, DemoTradeCandidate):
        raise TypeError("candidate must be a DemoTradeCandidate")

    created_at = created_at or _utc_now()
    notional = float(getattr(settings, "DEMO_DEFAULT_ORDER_NOTIONAL", 100.0))
    max_notional = float(getattr(settings, "DEMO_MAX_ORDER_NOTIONAL", 100.0))
    if notional > max_notional:
        raise ValueError("DEMO_DEFAULT_ORDER_NOTIONAL exceeds DEMO_MAX_ORDER_NOTIONAL")

    return DemoOrderIntent(
        order_intent_id=_new_order_intent_id(
            queue_item.symbol,
            queue_item.queue_item_id,
            candidate.trade_candidate_id,
            created_at,
        ),
        symbol=queue_item.symbol,
        queue_item_id=queue_item.queue_item_id,
        demo_trade_candidate_id=candidate.trade_candidate_id,
        source_hypothesis_id=candidate.source_hypothesis_id,
        created_at=created_at,
        status=DemoOrderIntentStatus.PREPARED,
        demo_only=True,
        side="buy",
        order_type="market",
        time_in_force="day",
        notional=notional,
        quantity=None,
        limit_price=None,
        stop_price=None,
        max_loss_per_trade=candidate.max_loss_per_trade,
        max_portfolio_exposure=candidate.max_portfolio_exposure,
        intent_reason="queued_demo_trade_candidate",
        created_by=created_by,
    )
