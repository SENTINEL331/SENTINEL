"""Read-only demo trade performance dashboard built from local append-only records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


RATING_RISK_BREACH = "risk_breach"
RATING_WEAK_OPEN = "weak_open"
RATING_FLAT_OPEN = "flat_open"
RATING_POSITIVE_OPEN = "positive_open"
RATING_UNKNOWN = "unknown"

PROMOTION_STATUS_NOT_EVALUATED = "not_evaluated"
DASHBOARD_NOTE = "Current mark-to-market only. Not a promotion decision."

_RISK_BREACH_THRESHOLD = -0.02
_WEAK_OPEN_THRESHOLD = -0.005
_POSITIVE_OPEN_THRESHOLD = 0.005


@dataclass(frozen=True, slots=True)
class DemoTradeDashboardRow:
    source_hypothesis_id: str
    demo_trade_candidate_id: str
    order_intent_id: str
    broker_order_id: str
    status: str
    current_rating: str
    side: str
    filled_qty: float | None = None
    filled_avg_price: float | None = None
    current_price: float | None = None
    entry_value: float | None = None
    current_value: float | None = None
    unrealized_pl: float | None = None
    unrealized_plpc: float | None = None
    demo_only: bool = True


@dataclass(frozen=True, slots=True)
class DemoTradeHypothesisSummaryRow:
    source_hypothesis_id: str
    trades: int
    total_entry_value: float
    total_current_value: float
    total_unrealized_pl: float
    total_unrealized_plpc: float
    current_rating: str
    promotion_status: str = PROMOTION_STATUS_NOT_EVALUATED
    note: str = DASHBOARD_NOTE


@dataclass(frozen=True, slots=True)
class DemoTradePerformanceDashboardResult:
    symbol: str
    performance_snapshots_loaded: int
    latest_trades_displayed: int
    hypotheses_displayed: int
    records_modified: bool = False
    position_snapshot: object | None = None
    trades: tuple[DemoTradeDashboardRow, ...] = field(default_factory=tuple)
    hypotheses: tuple[DemoTradeHypothesisSummaryRow, ...] = field(default_factory=tuple)


def _safe_float(value):
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rate_unrealized_plpc(unrealized_plpc) -> str:
    """Deterministic current mark-to-market rating. Not a promotion decision."""

    value = _safe_float(unrealized_plpc)
    if value is None:
        return RATING_UNKNOWN

    if value <= _RISK_BREACH_THRESHOLD:
        return RATING_RISK_BREACH

    if value < _WEAK_OPEN_THRESHOLD:
        return RATING_WEAK_OPEN

    if value <= _POSITIVE_OPEN_THRESHOLD:
        return RATING_FLAT_OPEN

    return RATING_POSITIVE_OPEN


def _timestamp(item, name: str) -> datetime:
    value = getattr(item, name, None)
    if isinstance(value, datetime):
        return value

    return datetime.min.replace(tzinfo=timezone.utc)


def _group_key(snapshot) -> str:
    broker_order_id = str(getattr(snapshot, "broker_order_id", "") or "")
    if broker_order_id:
        return f"broker_order_id:{broker_order_id}"

    order_intent_id = str(getattr(snapshot, "order_intent_id", "") or "")
    if order_intent_id:
        return f"order_intent_id:{order_intent_id}"

    return f"performance_snapshot_id:{getattr(snapshot, 'performance_snapshot_id', '')}"


def build_demo_trade_performance_dashboard(*, symbol: str, storage) -> DemoTradePerformanceDashboardResult:
    """Summarize current demo trade performance from stored records without writes or broker calls."""

    if not symbol:
        raise ValueError("symbol is required")

    performance_snapshots = list(storage.load_demo_trade_performance_snapshots(symbol=symbol) or [])
    order_intents = list(storage.load_demo_order_intents(symbol=symbol) or [])
    candidates = list(storage.load_demo_trade_candidates(symbol=symbol) or [])
    position_snapshots = list(storage.load_demo_position_snapshots(symbol=symbol) or [])

    intents_by_id = {
        str(getattr(intent, "order_intent_id", "") or ""): intent
        for intent in order_intents
        if getattr(intent, "order_intent_id", "")
    }
    candidates_by_id = {
        str(getattr(candidate, "trade_candidate_id", "") or ""): candidate
        for candidate in candidates
        if getattr(candidate, "trade_candidate_id", "")
    }

    latest_position_snapshot = None
    for snapshot in position_snapshots:
        if latest_position_snapshot is None or _timestamp(snapshot, "synced_at") >= _timestamp(
            latest_position_snapshot, "synced_at"
        ):
            latest_position_snapshot = snapshot

    latest_by_group: dict[str, object] = {}
    for snapshot in performance_snapshots:
        key = _group_key(snapshot)
        existing = latest_by_group.get(key)
        if existing is None or _timestamp(snapshot, "snapshot_at") >= _timestamp(existing, "snapshot_at"):
            latest_by_group[key] = snapshot

    trades: list[DemoTradeDashboardRow] = []
    for snapshot in latest_by_group.values():
        order_intent_id = str(getattr(snapshot, "order_intent_id", "") or "")
        intent = intents_by_id.get(order_intent_id)

        demo_trade_candidate_id = str(getattr(snapshot, "demo_trade_candidate_id", "") or "")
        if not demo_trade_candidate_id and intent is not None:
            demo_trade_candidate_id = str(getattr(intent, "demo_trade_candidate_id", "") or "")

        source_hypothesis_id = str(getattr(snapshot, "source_hypothesis_id", "") or "")
        if not source_hypothesis_id and intent is not None:
            source_hypothesis_id = str(getattr(intent, "source_hypothesis_id", "") or "")
        if not source_hypothesis_id and demo_trade_candidate_id:
            candidate = candidates_by_id.get(demo_trade_candidate_id)
            source_hypothesis_id = str(getattr(candidate, "source_hypothesis_id", "") or "")

        unrealized_plpc = _safe_float(getattr(snapshot, "unrealized_plpc", None))
        trades.append(
            DemoTradeDashboardRow(
                source_hypothesis_id=source_hypothesis_id,
                demo_trade_candidate_id=demo_trade_candidate_id,
                order_intent_id=order_intent_id,
                broker_order_id=str(getattr(snapshot, "broker_order_id", "") or ""),
                status=str(getattr(snapshot, "status", "") or "unknown"),
                current_rating=rate_unrealized_plpc(unrealized_plpc),
                side=str(getattr(snapshot, "side", "") or "none"),
                filled_qty=_safe_float(getattr(snapshot, "filled_qty", None)),
                filled_avg_price=_safe_float(getattr(snapshot, "filled_avg_price", None)),
                current_price=_safe_float(getattr(snapshot, "current_price", None)),
                entry_value=_safe_float(getattr(snapshot, "entry_value", None)),
                current_value=_safe_float(getattr(snapshot, "current_value", None)),
                unrealized_pl=_safe_float(getattr(snapshot, "unrealized_pl", None)),
                unrealized_plpc=unrealized_plpc,
                demo_only=bool(getattr(snapshot, "demo_only", True)),
            )
        )

    trades.sort(
        key=lambda row: (
            row.source_hypothesis_id,
            row.demo_trade_candidate_id,
            row.order_intent_id,
            row.broker_order_id,
        )
    )

    totals: dict[str, dict[str, float]] = {}
    for row in trades:
        bucket = totals.setdefault(
            row.source_hypothesis_id,
            {"trades": 0.0, "entry": 0.0, "current": 0.0, "pl": 0.0, "valued": 0.0},
        )
        bucket["trades"] += 1
        if row.entry_value is not None:
            bucket["entry"] += row.entry_value
            bucket["valued"] += 1
        if row.current_value is not None:
            bucket["current"] += row.current_value
        if row.unrealized_pl is not None:
            bucket["pl"] += row.unrealized_pl

    hypotheses: list[DemoTradeHypothesisSummaryRow] = []
    for source_hypothesis_id in sorted(totals):
        bucket = totals[source_hypothesis_id]
        total_entry_value = bucket["entry"]
        total_unrealized_pl = bucket["pl"]
        total_unrealized_plpc = (total_unrealized_pl / total_entry_value) if total_entry_value > 0 else 0.0
        current_rating = (
            rate_unrealized_plpc(total_unrealized_plpc) if bucket["valued"] > 0 else RATING_UNKNOWN
        )
        hypotheses.append(
            DemoTradeHypothesisSummaryRow(
                source_hypothesis_id=source_hypothesis_id,
                trades=int(bucket["trades"]),
                total_entry_value=total_entry_value,
                total_current_value=bucket["current"],
                total_unrealized_pl=total_unrealized_pl,
                total_unrealized_plpc=total_unrealized_plpc,
                current_rating=current_rating,
            )
        )

    return DemoTradePerformanceDashboardResult(
        symbol=symbol,
        performance_snapshots_loaded=len(performance_snapshots),
        latest_trades_displayed=len(trades),
        hypotheses_displayed=len(hypotheses),
        records_modified=False,
        position_snapshot=latest_position_snapshot,
        trades=tuple(trades),
        hypotheses=tuple(hypotheses),
    )
