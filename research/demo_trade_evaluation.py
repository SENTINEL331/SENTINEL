"""Append-only deterministic evaluation of open demo trades from local records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256

from config import settings
from research.demo_trade_performance_dashboard import (
    RATING_FLAT_OPEN,
    RATING_POSITIVE_OPEN,
    RATING_RISK_BREACH,
    RATING_UNKNOWN,
    RATING_WEAK_OPEN,
    rate_unrealized_plpc,
)


EVALUATION_STATUS_RISK_BREACH = "risk_breach"
EVALUATION_STATUS_SUCCESSFUL_WINDOW = "successful_window"
EVALUATION_STATUS_FLAT_WINDOW = "flat_window"
EVALUATION_STATUS_WEAK_WINDOW = "weak_window"
EVALUATION_STATUS_NEEDS_MORE_TIME = "needs_more_time"
EVALUATION_STATUS_UNKNOWN = "unknown"

ACTION_EXIT_CANDIDATE = "exit_candidate"
ACTION_CONTINUE_OR_REVIEW_FOR_PROMOTION = "continue_or_review_for_promotion"
ACTION_NEEDS_MORE_TIME_OR_EXIT_REVIEW = "needs_more_time_or_exit_review"
ACTION_EXIT_CANDIDATE_OR_CONTINUE_MONITORING = "exit_candidate_or_continue_monitoring"
ACTION_CONTINUE_MONITORING = "continue_monitoring"
ACTION_MANUAL_REVIEW = "manual_review"

EVALUATION_STATUS_ORDER = (
    EVALUATION_STATUS_NEEDS_MORE_TIME,
    EVALUATION_STATUS_SUCCESSFUL_WINDOW,
    EVALUATION_STATUS_FLAT_WINDOW,
    EVALUATION_STATUS_WEAK_WINDOW,
    EVALUATION_STATUS_RISK_BREACH,
    EVALUATION_STATUS_UNKNOWN,
)


@dataclass(frozen=True, slots=True)
class DemoTradeEvaluation:
    demo_trade_evaluation_id: str
    symbol: str
    performance_snapshot_id: str
    order_intent_id: str
    broker_order_id: str
    broker_order_record_id: str
    queue_item_id: str
    demo_trade_candidate_id: str
    source_hypothesis_id: str
    evaluated_at: datetime
    entry_reference_time: datetime | None = None
    trading_days_elapsed: int = 0
    evaluation_window_trading_days: int = 0
    evaluation_window_complete: bool = False
    current_rating: str = RATING_UNKNOWN
    evaluation_status: str = EVALUATION_STATUS_UNKNOWN
    recommended_action: str = ACTION_MANUAL_REVIEW
    side: str = "none"
    filled_qty: float | None = None
    filled_avg_price: float | None = None
    current_price: float | None = None
    entry_value: float | None = None
    current_value: float | None = None
    unrealized_pl: float | None = None
    unrealized_plpc: float | None = None
    max_loss_per_trade: float = 0.0
    risk_breached: bool = False
    demo_only: bool = True
    created_by: str = "sentinel"


@dataclass(frozen=True, slots=True)
class DemoTradeEvaluationResult:
    symbol: str
    performance_snapshots_loaded: int
    evaluations_created: int
    skipped_existing: int
    skipped_ineligible: int
    failed_evaluations: int
    records_modified: bool
    evaluations: tuple[DemoTradeEvaluation, ...] = field(default_factory=tuple)
    status_counts: dict[str, int] = field(default_factory=dict)


def _new_demo_trade_evaluation_id(*, symbol: str, performance_snapshot_id: str, evaluated_at: datetime) -> str:
    digest = sha256(
        f"{symbol}|{performance_snapshot_id}|{evaluated_at.isoformat()}".encode("utf-8")
    ).hexdigest()[:12]
    return f"dtev-{symbol}-{digest}"


def _normalize(value: str) -> str:
    return (value or "").strip().casefold()


def _safe_float(value):
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_datetime(value) -> datetime | None:
    return value if isinstance(value, datetime) else None


def count_trading_days(start: datetime | None, end: datetime | None) -> int:
    """Count weekdays elapsed between two timestamps without a market calendar."""

    if start is None or end is None:
        return 0

    start_date: date = start.date()
    end_date: date = end.date()
    if end_date <= start_date:
        return 0

    elapsed = 0
    current = start_date + timedelta(days=1)
    while current <= end_date:
        if current.weekday() < 5:
            elapsed += 1
        current += timedelta(days=1)

    return elapsed


def classify_demo_trade_evaluation(*, current_rating: str, evaluation_window_complete: bool) -> tuple[str, str]:
    """Deterministic evaluation status and recommended action. Not promotion, not an exit order."""

    if current_rating == RATING_RISK_BREACH:
        return EVALUATION_STATUS_RISK_BREACH, ACTION_EXIT_CANDIDATE

    if evaluation_window_complete and current_rating == RATING_POSITIVE_OPEN:
        return EVALUATION_STATUS_SUCCESSFUL_WINDOW, ACTION_CONTINUE_OR_REVIEW_FOR_PROMOTION

    if evaluation_window_complete and current_rating == RATING_FLAT_OPEN:
        return EVALUATION_STATUS_FLAT_WINDOW, ACTION_NEEDS_MORE_TIME_OR_EXIT_REVIEW

    if evaluation_window_complete and current_rating == RATING_WEAK_OPEN:
        return EVALUATION_STATUS_WEAK_WINDOW, ACTION_EXIT_CANDIDATE_OR_CONTINUE_MONITORING

    if not evaluation_window_complete and current_rating != RATING_UNKNOWN:
        return EVALUATION_STATUS_NEEDS_MORE_TIME, ACTION_CONTINUE_MONITORING

    return EVALUATION_STATUS_UNKNOWN, ACTION_MANUAL_REVIEW


def _latest_performance_snapshots(snapshots):
    latest: dict[str, object] = {}
    for snapshot in snapshots:
        key = str(getattr(snapshot, "broker_order_id", "") or "") or str(
            getattr(snapshot, "order_intent_id", "") or ""
        )
        if not key:
            key = str(getattr(snapshot, "performance_snapshot_id", "") or "")
        if not key:
            continue

        existing = latest.get(key)
        if existing is None:
            latest[key] = snapshot
            continue

        snapshot_at = _as_datetime(getattr(snapshot, "snapshot_at", None)) or datetime.min.replace(
            tzinfo=timezone.utc
        )
        existing_at = _as_datetime(getattr(existing, "snapshot_at", None)) or datetime.min.replace(
            tzinfo=timezone.utc
        )
        if snapshot_at >= existing_at:
            latest[key] = snapshot

    return latest


def _entry_reference_time(*, broker_order_record, order_statuses, intent) -> datetime | None:
    if broker_order_record is not None:
        submitted_at = _as_datetime(getattr(broker_order_record, "submitted_at", None))
        if submitted_at is not None:
            return submitted_at

        created_at = _as_datetime(getattr(broker_order_record, "created_at", None))
        if created_at is not None:
            return created_at

    earliest_synced_at = None
    for status_record in order_statuses:
        synced_at = _as_datetime(getattr(status_record, "synced_at", None))
        if synced_at is None:
            continue

        if earliest_synced_at is None or synced_at < earliest_synced_at:
            earliest_synced_at = synced_at

    if earliest_synced_at is not None:
        return earliest_synced_at

    if intent is not None:
        return _as_datetime(getattr(intent, "created_at", None))

    return None


def build_demo_trade_evaluations(*, symbol: str, storage) -> DemoTradeEvaluationResult:
    """Append deterministic demo trade evaluations without broker, AI, or order calls."""

    if not symbol:
        raise ValueError("symbol is required")

    demo_broker_settings = settings.get_demo_broker_settings()
    if _normalize(demo_broker_settings.get("mode")) == "live":
        raise ValueError("live trading is not allowed")

    window_trading_days = int(getattr(settings, "DEMO_TRADE_EVALUATION_WINDOW_TRADING_DAYS", 5))

    performance_snapshots = list(storage.load_demo_trade_performance_snapshots(symbol=symbol) or [])
    order_intents = list(storage.load_demo_order_intents(symbol=symbol) or [])
    candidates = list(storage.load_demo_trade_candidates(symbol=symbol) or [])
    broker_order_records = list(storage.load_demo_broker_order_records(symbol=symbol) or [])
    order_statuses = list(storage.load_demo_broker_order_statuses(symbol=symbol) or [])
    existing_evaluations = list(storage.load_demo_trade_evaluations(symbol=symbol) or [])

    evaluated_snapshot_ids = {
        str(getattr(evaluation, "performance_snapshot_id", "") or "")
        for evaluation in existing_evaluations
    }
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
    records_by_broker_order_id = {
        str(getattr(record, "broker_order_id", "") or ""): record
        for record in broker_order_records
        if getattr(record, "broker_order_id", "")
    }

    evaluations: list[DemoTradeEvaluation] = []
    skipped_existing = 0
    skipped_ineligible = 0
    failed_evaluations = 0
    status_counts = {status: 0 for status in EVALUATION_STATUS_ORDER}

    for snapshot in _latest_performance_snapshots(performance_snapshots).values():
        performance_snapshot_id = str(getattr(snapshot, "performance_snapshot_id", "") or "")
        if not performance_snapshot_id:
            skipped_ineligible += 1
            continue

        if performance_snapshot_id in evaluated_snapshot_ids:
            skipped_existing += 1
            continue

        snapshot_at = _as_datetime(getattr(snapshot, "snapshot_at", None))
        if snapshot_at is None:
            failed_evaluations += 1
            continue

        broker_order_id = str(getattr(snapshot, "broker_order_id", "") or "")
        order_intent_id = str(getattr(snapshot, "order_intent_id", "") or "")
        intent = intents_by_id.get(order_intent_id)
        broker_order_record = records_by_broker_order_id.get(broker_order_id)
        matching_statuses = [
            status_record
            for status_record in order_statuses
            if str(getattr(status_record, "broker_order_id", "") or "") == broker_order_id
        ]

        demo_trade_candidate_id = str(getattr(snapshot, "demo_trade_candidate_id", "") or "")
        if not demo_trade_candidate_id and intent is not None:
            demo_trade_candidate_id = str(getattr(intent, "demo_trade_candidate_id", "") or "")

        source_hypothesis_id = str(getattr(snapshot, "source_hypothesis_id", "") or "")
        if not source_hypothesis_id and intent is not None:
            source_hypothesis_id = str(getattr(intent, "source_hypothesis_id", "") or "")

        candidate = candidates_by_id.get(demo_trade_candidate_id)
        max_loss_per_trade = _safe_float(getattr(intent, "max_loss_per_trade", None))
        if max_loss_per_trade is None:
            max_loss_per_trade = _safe_float(getattr(candidate, "max_loss_per_trade", None))

        entry_reference_time = _entry_reference_time(
            broker_order_record=broker_order_record,
            order_statuses=matching_statuses,
            intent=intent,
        )
        trading_days_elapsed = count_trading_days(entry_reference_time, snapshot_at)
        evaluation_window_complete = trading_days_elapsed >= window_trading_days

        unrealized_plpc = _safe_float(getattr(snapshot, "unrealized_plpc", None))
        current_rating = rate_unrealized_plpc(unrealized_plpc)
        evaluation_status, recommended_action = classify_demo_trade_evaluation(
            current_rating=current_rating,
            evaluation_window_complete=evaluation_window_complete,
        )

        evaluated_at = datetime.now(timezone.utc)
        evaluation = DemoTradeEvaluation(
            demo_trade_evaluation_id=_new_demo_trade_evaluation_id(
                symbol=symbol,
                performance_snapshot_id=performance_snapshot_id,
                evaluated_at=evaluated_at,
            ),
            symbol=symbol,
            performance_snapshot_id=performance_snapshot_id,
            order_intent_id=order_intent_id,
            broker_order_id=broker_order_id,
            broker_order_record_id=str(getattr(snapshot, "broker_order_record_id", "") or ""),
            queue_item_id=str(getattr(snapshot, "queue_item_id", "") or ""),
            demo_trade_candidate_id=demo_trade_candidate_id,
            source_hypothesis_id=source_hypothesis_id,
            evaluated_at=evaluated_at,
            entry_reference_time=entry_reference_time,
            trading_days_elapsed=trading_days_elapsed,
            evaluation_window_trading_days=window_trading_days,
            evaluation_window_complete=evaluation_window_complete,
            current_rating=current_rating,
            evaluation_status=evaluation_status,
            recommended_action=recommended_action,
            side=str(getattr(snapshot, "side", "") or "none"),
            filled_qty=_safe_float(getattr(snapshot, "filled_qty", None)),
            filled_avg_price=_safe_float(getattr(snapshot, "filled_avg_price", None)),
            current_price=_safe_float(getattr(snapshot, "current_price", None)),
            entry_value=_safe_float(getattr(snapshot, "entry_value", None)),
            current_value=_safe_float(getattr(snapshot, "current_value", None)),
            unrealized_pl=_safe_float(getattr(snapshot, "unrealized_pl", None)),
            unrealized_plpc=unrealized_plpc,
            max_loss_per_trade=max_loss_per_trade or 0.0,
            risk_breached=current_rating == RATING_RISK_BREACH,
            demo_only=bool(getattr(snapshot, "demo_only", True)),
            created_by=str(getattr(snapshot, "created_by", "sentinel") or "sentinel"),
        )

        storage.save_demo_trade_evaluation(evaluation)
        evaluations.append(evaluation)
        evaluated_snapshot_ids.add(performance_snapshot_id)
        status_counts[evaluation_status] += 1

    evaluations.sort(
        key=lambda item: (
            item.source_hypothesis_id,
            item.demo_trade_candidate_id,
            item.order_intent_id,
            item.broker_order_id,
        )
    )

    return DemoTradeEvaluationResult(
        symbol=symbol,
        performance_snapshots_loaded=len(performance_snapshots),
        evaluations_created=len(evaluations),
        skipped_existing=skipped_existing,
        skipped_ineligible=skipped_ineligible,
        failed_evaluations=failed_evaluations,
        records_modified=bool(evaluations),
        evaluations=tuple(evaluations),
        status_counts=status_counts,
    )
