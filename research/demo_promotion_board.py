"""Deterministic read-only board recommendations from local demo summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


BOARD_BLOCKED = "blocked"
BOARD_NOT_READY = "not_ready"
BOARD_MONITOR = "monitor"
BOARD_REVIEW_LATER = "review_later"
BOARD_UNKNOWN = "unknown"

ACTION_CONTINUE_DEMO_MONITORING = "continue_demo_monitoring"
BOARD_NOTE = "Read-only board recommendation. No promotion was performed."

BOARD_RECOMMENDATION_ORDER = (
    BOARD_NOT_READY,
    BOARD_MONITOR,
    BOARD_REVIEW_LATER,
    BOARD_BLOCKED,
    BOARD_UNKNOWN,
)


@dataclass(frozen=True, slots=True)
class DemoPromotionBoardItem:
    source_hypothesis_id: str
    latest_summary_id: str
    trades_evaluated: int
    evaluation_window_complete_count: int
    current_summary_rating: str
    promotion_readiness: str
    board_recommendation: str
    board_reason: tuple[str, ...] = field(default_factory=tuple)
    total_unrealized_pl: float | None = None
    total_unrealized_plpc: float | None = None
    risk_breach_rate: float | None = None
    completion_rate: float | None = None
    action: str = ACTION_CONTINUE_DEMO_MONITORING
    note: str = BOARD_NOTE


@dataclass(frozen=True, slots=True)
class DemoPromotionBoardResult:
    symbol: str
    hypothesis_summaries_loaded: int
    board_items_displayed: int
    records_modified: bool = False
    board_items: tuple[DemoPromotionBoardItem, ...] = field(default_factory=tuple)
    recommendation_counts: dict[str, int] = field(default_factory=dict)


def _timestamp(summary) -> datetime:
    value = getattr(summary, "summarized_at", None)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    return datetime.min.replace(tzinfo=timezone.utc)


def _number(summary, name: str, default=None):
    value = getattr(summary, name, default)
    if value in (None, ""):
        return default
    try:
        if name in {"trades_evaluated", "evaluation_window_complete_count"}:
            return int(value)
        return float(value)
    except (TypeError, ValueError):
        return default


def _recommend(summary) -> tuple[str, tuple[str, ...]]:
    trades = _number(summary, "trades_evaluated")
    completed = _number(summary, "evaluation_window_complete_count")
    rating = getattr(summary, "current_summary_rating", None)
    readiness = getattr(summary, "promotion_readiness", None)
    risk_breaches = _number(summary, "risk_breach_count")

    if trades is None or completed is None or risk_breaches is None or not rating or not readiness:
        return BOARD_UNKNOWN, ("missing_demo_summary_data",)

    reasons = []
    if risk_breaches > 0:
        reasons.append("risk_breach_detected")
    if trades < 3:
        reasons.append(f"only_{trades}_demo_trade" if trades == 1 else "limited_forward_evidence")
    if completed == 0:
        reasons.append("no_completed_evaluation_window")
    if rating == "needs_more_time" and trades >= 3:
        return BOARD_MONITOR, ("active_demo_needs_more_time",)
    if risk_breaches > 0:
        return BOARD_BLOCKED, tuple(reasons)
    if trades < 3 or completed == 0:
        return BOARD_NOT_READY, tuple(reasons)
    return BOARD_REVIEW_LATER, ("limited_forward_evidence",)


def build_demo_promotion_board(*, symbol: str, storage) -> DemoPromotionBoardResult:
    """Review only latest locally stored demo summaries; never writes or calls brokers."""

    if not symbol:
        raise ValueError("symbol is required")

    summaries = list(storage.load_demo_hypothesis_performance_summaries(symbol=symbol) or [])
    latest: dict[str, object] = {}
    for summary in summaries:
        source_hypothesis_id = str(getattr(summary, "source_hypothesis_id", "") or "")
        if not source_hypothesis_id:
            continue
        existing = latest.get(source_hypothesis_id)
        summary_key = (
            _timestamp(summary),
            str(getattr(summary, "demo_hypothesis_summary_id", "")),
        )
        existing_key = (
            _timestamp(existing),
            str(getattr(existing, "demo_hypothesis_summary_id", "")),
        ) if existing is not None else None
        if existing is None or summary_key >= existing_key:
            latest[source_hypothesis_id] = summary

    items = []
    for source_hypothesis_id in sorted(latest):
        summary = latest[source_hypothesis_id]
        recommendation, reasons = _recommend(summary)
        items.append(
            DemoPromotionBoardItem(
                source_hypothesis_id=source_hypothesis_id,
                latest_summary_id=str(getattr(summary, "demo_hypothesis_summary_id", "") or ""),
                trades_evaluated=_number(summary, "trades_evaluated", 0),
                evaluation_window_complete_count=_number(summary, "evaluation_window_complete_count", 0),
                current_summary_rating=str(getattr(summary, "current_summary_rating", "unknown") or "unknown"),
                promotion_readiness=str(getattr(summary, "promotion_readiness", "unknown") or "unknown"),
                board_recommendation=recommendation,
                board_reason=reasons,
                total_unrealized_pl=_number(summary, "total_unrealized_pl"),
                total_unrealized_plpc=_number(summary, "total_unrealized_plpc"),
                risk_breach_rate=_number(summary, "risk_breach_rate"),
                completion_rate=_number(summary, "completion_rate"),
            )
        )

    counts = {recommendation: 0 for recommendation in BOARD_RECOMMENDATION_ORDER}
    for item in items:
        counts[item.board_recommendation] += 1
    return DemoPromotionBoardResult(
        symbol=symbol,
        hypothesis_summaries_loaded=len(summaries),
        board_items_displayed=len(items),
        board_items=tuple(items),
        recommendation_counts=counts,
    )