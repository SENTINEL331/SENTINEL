"""Deterministic read-only ratings for the current attractiveness of demo setups."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from research.demo_trade_performance_dashboard import rate_unrealized_plpc
from research.demo_promotion_board import build_demo_promotion_board


RATING_ATTRACTIVE_NOW = "attractive_now"
RATING_CAUTION_NEW_ENTRY = "caution_new_entry"
RATING_WAIT = "wait"
RATING_MONITOR = "monitor"
RATING_AVOID_NEW_ENTRY = "avoid_new_entry"
RATING_RISK_WARNING = "risk_warning"
RATING_NOT_READY = "not_ready"
RATING_BLOCKED = "blocked"
RATING_UNKNOWN = "unknown"

OPPORTUNITY_RATING_ORDER = (
    RATING_ATTRACTIVE_NOW,
    RATING_CAUTION_NEW_ENTRY,
    RATING_WAIT,
    RATING_AVOID_NEW_ENTRY,
    RATING_RISK_WARNING,
    RATING_NOT_READY,
    RATING_BLOCKED,
    RATING_UNKNOWN,
)

OPPORTUNITY_NOTE = (
    "Current opportunity rating is based on latest local snapshot only. "
    "This is not a new trade instruction and not promotion."
)


@dataclass(frozen=True, slots=True)
class DemoCurrentOpportunityRating:
    source_hypothesis_id: str
    demo_trade_candidate_id: str
    order_intent_id: str
    broker_order_id: str
    latest_current_price: float | None
    entry_price: float | None
    entry_performance_rating: str
    entry_unrealized_plpc: float | None
    board_recommendation: str
    hypothesis_summary_rating: str
    current_opportunity_rating: str
    opportunity_reason: str
    action: str = "no_new_entry"
    note: str = OPPORTUNITY_NOTE


@dataclass(frozen=True, slots=True)
class DemoCurrentOpportunityRatingResult:
    symbol: str
    performance_snapshots_loaded: int
    position_snapshots_loaded: int
    hypothesis_summaries_loaded: int
    ratings_displayed: int
    records_modified: bool = False
    ratings: tuple[DemoCurrentOpportunityRating, ...] = field(default_factory=tuple)
    rating_counts: dict[str, int] = field(default_factory=dict)


def _number(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _timestamp(item, name: str) -> datetime:
    value = getattr(item, name, None)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    return datetime.min.replace(tzinfo=timezone.utc)


def _latest_performance_snapshots(snapshots):
    latest = {}
    for snapshot in snapshots:
        broker_order_id = str(getattr(snapshot, "broker_order_id", "") or "")
        order_intent_id = str(getattr(snapshot, "order_intent_id", "") or "")
        key = broker_order_id or order_intent_id or str(
            getattr(snapshot, "performance_snapshot_id", "") or ""
        )
        if not key:
            continue
        existing = latest.get(key)
        if existing is None or (
            _timestamp(snapshot, "snapshot_at"),
            str(getattr(snapshot, "performance_snapshot_id", "")),
        ) >= (
            _timestamp(existing, "snapshot_at"),
            str(getattr(existing, "performance_snapshot_id", "")),
        ):
            latest[key] = snapshot
    return latest


def _latest_position_snapshot(snapshots):
    latest = None
    for snapshot in snapshots:
        if latest is None or _timestamp(snapshot, "synced_at") >= _timestamp(latest, "synced_at"):
            latest = snapshot
    return latest


def _current_price(*, performance_snapshot, position_snapshot):
    performance_price = _number(getattr(performance_snapshot, "current_price", None))
    position_price = _number(getattr(position_snapshot, "current_price", None))
    if performance_price is None:
        return position_price
    if position_price is None:
        return performance_price
    if _timestamp(position_snapshot, "synced_at") >= _timestamp(performance_snapshot, "snapshot_at"):
        return position_price
    return performance_price


def _entry_unrealized_plpc(*, snapshot, current_price, entry_price):
    if current_price is not None and entry_price not in (None, 0):
        return (current_price - entry_price) / entry_price
    return _number(getattr(snapshot, "unrealized_plpc", None))


def _rate(*, board_recommendation, summary, snapshot, current_price, entry_performance_rating, entry_unrealized_plpc):
    risk_breach_count = _number(getattr(summary, "risk_breach_count", None)) if summary else None
    summary_rating = str(getattr(summary, "current_summary_rating", "unknown") or "unknown") if summary else "unknown"
    if board_recommendation == "blocked" or (risk_breach_count is not None and risk_breach_count > 0):
        return RATING_BLOCKED, "blocked_by_demo_risk_evidence"
    if board_recommendation == "not_ready":
        return RATING_NOT_READY, "demo_evidence_is_not_ready"
    if board_recommendation == "monitor":
        return RATING_MONITOR, "active_demo_requires_monitoring"
    if summary_rating == "needs_more_time":
        return RATING_WAIT, "demo_evidence_needs_more_time"

    if snapshot is None or current_price is None or entry_performance_rating == "unknown":
        return RATING_UNKNOWN, "missing_current_opportunity_data"

    is_open = str(getattr(snapshot, "status", "") or "").casefold() == "open"
    if is_open and entry_unrealized_plpc is not None:
        if entry_unrealized_plpc > 0.005:
            return RATING_AVOID_NEW_ENTRY, "setup_may_have_moved_away_do_not_chase"
        if entry_unrealized_plpc < -0.005:
            return RATING_RISK_WARNING, "current_trade_is_below_entry_risk_warning"
        return RATING_CAUTION_NEW_ENTRY, "close_to_entry_requires_signal_recheck"

    completed_positive_evidence = (
        board_recommendation == "review_later" and summary_rating == "promising_demo"
    )
    if completed_positive_evidence:
        return RATING_ATTRACTIVE_NOW, "completed_positive_demo_evidence_without_risk_breach"
    return RATING_UNKNOWN, "insufficient_completed_positive_demo_evidence"


def build_demo_current_opportunity_ratings(*, symbol: str, storage) -> DemoCurrentOpportunityRatingResult:
    """Rate current local demo opportunities without writes, broker, market-data, or AI calls."""

    if not symbol:
        raise ValueError("symbol is required")

    performance_snapshots = list(storage.load_demo_trade_performance_snapshots(symbol=symbol) or [])
    position_snapshots = list(storage.load_demo_position_snapshots(symbol=symbol) or [])
    candidates = list(storage.load_demo_trade_candidates(symbol=symbol) or [])
    intents = list(storage.load_demo_order_intents(symbol=symbol) or [])
    position_snapshot = _latest_position_snapshot(position_snapshots)
    board_result = build_demo_promotion_board(symbol=symbol, storage=storage)
    board_by_hypothesis = {item.source_hypothesis_id: item for item in board_result.board_items}

    candidates_by_id = {
        str(getattr(candidate, "trade_candidate_id", "") or ""): candidate
        for candidate in candidates
        if getattr(candidate, "trade_candidate_id", "")
    }
    intents_by_id = {
        str(getattr(intent, "order_intent_id", "") or ""): intent
        for intent in intents
        if getattr(intent, "order_intent_id", "")
    }

    ratings = []
    for snapshot in sorted(
        _latest_performance_snapshots(performance_snapshots).values(),
        key=lambda item: (
            str(getattr(item, "source_hypothesis_id", "") or ""),
            str(getattr(item, "broker_order_id", "") or ""),
            str(getattr(item, "order_intent_id", "") or ""),
        ),
    ):
        order_intent_id = str(getattr(snapshot, "order_intent_id", "") or "")
        intent = intents_by_id.get(order_intent_id)
        candidate_id = str(getattr(snapshot, "demo_trade_candidate_id", "") or "")
        if not candidate_id and intent is not None:
            candidate_id = str(getattr(intent, "demo_trade_candidate_id", "") or "")
        candidate = candidates_by_id.get(candidate_id)
        source_hypothesis_id = str(getattr(snapshot, "source_hypothesis_id", "") or "")
        if not source_hypothesis_id and intent is not None:
            source_hypothesis_id = str(getattr(intent, "source_hypothesis_id", "") or "")
        if not source_hypothesis_id and candidate is not None:
            source_hypothesis_id = str(getattr(candidate, "source_hypothesis_id", "") or "")

        current_price = _current_price(
            performance_snapshot=snapshot,
            position_snapshot=position_snapshot,
        )
        entry_price = _number(getattr(snapshot, "filled_avg_price", None))
        entry_unrealized_plpc = _entry_unrealized_plpc(
            snapshot=snapshot,
            current_price=current_price,
            entry_price=entry_price,
        )
        entry_performance_rating = rate_unrealized_plpc(entry_unrealized_plpc)
        board_item = board_by_hypothesis.get(source_hypothesis_id)
        summary = board_item
        board_recommendation = board_item.board_recommendation if board_item else "unknown"
        current_rating, reason = _rate(
            board_recommendation=board_recommendation,
            summary=summary,
            snapshot=snapshot,
            current_price=current_price,
            entry_performance_rating=entry_performance_rating,
            entry_unrealized_plpc=entry_unrealized_plpc,
        )
        ratings.append(
            DemoCurrentOpportunityRating(
                source_hypothesis_id=source_hypothesis_id,
                demo_trade_candidate_id=candidate_id,
                order_intent_id=order_intent_id,
                broker_order_id=str(getattr(snapshot, "broker_order_id", "") or ""),
                latest_current_price=current_price,
                entry_price=entry_price,
                entry_performance_rating=entry_performance_rating,
                entry_unrealized_plpc=entry_unrealized_plpc,
                board_recommendation=board_recommendation,
                hypothesis_summary_rating=(
                    str(getattr(summary, "current_summary_rating", "unknown") or "unknown")
                    if summary is not None
                    else "unknown"
                ),
                current_opportunity_rating=current_rating,
                opportunity_reason=reason,
            )
        )

    rating_counts = {rating: 0 for rating in OPPORTUNITY_RATING_ORDER}
    for rating in ratings:
        rating_counts[rating.current_opportunity_rating] = rating_counts.get(
            rating.current_opportunity_rating, 0
        ) + 1
    return DemoCurrentOpportunityRatingResult(
        symbol=symbol,
        performance_snapshots_loaded=len(performance_snapshots),
        position_snapshots_loaded=len(position_snapshots),
        hypothesis_summaries_loaded=board_result.hypothesis_summaries_loaded,
        ratings_displayed=len(ratings),
        ratings=tuple(ratings),
        rating_counts=rating_counts,
    )