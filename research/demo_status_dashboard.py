"""Read-only combined dashboard for the latest local demo monitoring state."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from research.demo_current_opportunity_rating import (
    build_demo_current_opportunity_ratings,
)
from research.demo_exit_readiness import classify_demo_exit_readiness
from research.demo_promotion_board import build_demo_promotion_board
from research.demo_trade_performance_dashboard import build_demo_trade_performance_dashboard


@dataclass(frozen=True, slots=True)
class DemoStatusTradeRow:
    source_hypothesis_id: str
    demo_trade_candidate_id: str
    order_intent_id: str
    broker_order_id: str
    entry_price: float | None
    current_price: float | None
    entry_performance_rating: str
    entry_unrealized_plpc: float | None
    trade_evaluation_status: str
    trade_recommended_action: str
    hypothesis_summary_rating: str
    board_recommendation: str
    current_opportunity_rating: str
    current_opportunity_action: str
    demo_only: bool = True
    status: str = "unknown"
    exit_readiness: str = "unknown"
    exit_reason: str = "missing_or_unrecognized_exit_data"
    exit_action: str = "manual_review"
    trading_days_elapsed: int | None = None
    evaluation_window_trading_days: int | None = None
    evaluation_days_remaining: int | None = None
    evaluation_window_complete: bool | None = None


@dataclass(frozen=True, slots=True)
class DemoStatusHypothesisRow:
    source_hypothesis_id: str
    trades_evaluated: int
    current_summary_rating: str
    promotion_readiness: str
    board_recommendation: str
    board_reason: tuple[str, ...] = field(default_factory=tuple)
    current_opportunity_rating: str = "unknown"
    action: str = "no_new_entry"


@dataclass(frozen=True, slots=True)
class DemoStatusDashboardResult:
    symbol: str
    records_modified: bool
    position_snapshot: object | None
    trades: tuple[DemoStatusTradeRow, ...] = field(default_factory=tuple)
    hypotheses: tuple[DemoStatusHypothesisRow, ...] = field(default_factory=tuple)
    open_demo_trades: int = 0
    total_entry_value: float = 0.0
    total_current_value: float = 0.0
    total_unrealized_pl: float = 0.0
    total_unrealized_plpc: float = 0.0
    rating_counts: dict[str, int] = field(default_factory=dict)
    latest_daily_ai_review: object | None = None
    staleness_status: str = "unknown"
    latest_position_snapshot_at: datetime | None = None
    latest_position_snapshot_age_hours: float | None = None
    latest_performance_snapshot_at: datetime | None = None
    latest_performance_snapshot_age_hours: float | None = None
    latest_trade_evaluation_at: datetime | None = None
    latest_trade_evaluation_age_hours: float | None = None
    latest_ai_review_at: datetime | None = None
    latest_ai_review_age_hours: float | None = None
    freshness_reason: str = "required_snapshot_timestamp_missing_or_invalid"
    ai_review_freshness: str = "unknown"
    latest_required_snapshot_at: datetime | None = None
    ai_review_lag_hours: float | None = None
    ai_review_freshness_reason: str = "required_snapshot_timestamp_missing_or_invalid"


def _timestamp(item, name: str) -> datetime:
    value = getattr(item, name, None)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    return datetime.min.replace(tzinfo=timezone.utc)


def _parse_timestamp(value) -> datetime | None:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return None
    return value.astimezone(timezone.utc)


def _latest_timestamp(items, name: str) -> datetime | None:
    timestamps = [_parse_timestamp(getattr(item, name, None)) for item in items]
    valid_timestamps = [timestamp for timestamp in timestamps if timestamp is not None]
    return max(valid_timestamps) if valid_timestamps else None


def _age_hours(timestamp: datetime | None, now: datetime) -> float | None:
    if timestamp is None:
        return None
    return round(max((now - timestamp).total_seconds() / 3600, 0.0), 2)


def _snapshot_freshness(*, position_snapshots, performance_snapshots, evaluations, latest_daily_ai_review):
    now = datetime.now(timezone.utc)
    position_at = _latest_timestamp(position_snapshots, "synced_at")
    performance_at = _latest_timestamp(performance_snapshots, "snapshot_at")
    evaluation_at = _latest_timestamp(evaluations, "evaluated_at")
    review_at = _parse_timestamp(getattr(latest_daily_ai_review, "reviewed_at", None))

    required_timestamps = (position_at, performance_at, evaluation_at)
    required_ages = tuple(_age_hours(timestamp, now) for timestamp in required_timestamps)
    if any(timestamp is None for timestamp in required_timestamps):
        status = "unknown"
        reason = "required_snapshot_timestamp_missing_or_invalid"
    else:
        latest_required_age = max(age for age in required_ages if age is not None)
        if latest_required_age <= 24:
            status = "fresh"
            reason = "latest_required_snapshots_fresh"
        elif latest_required_age <= 48:
            status = "warning"
            reason = "latest_required_snapshots_warning"
        else:
            status = "stale"
            reason = "latest_required_snapshots_stale"

    latest_required_snapshot_at = (
        max(required_timestamps) if all(required_timestamps) else None
    )
    if review_at is None and latest_daily_ai_review is None:
        ai_review_freshness = "missing"
        ai_review_freshness_reason = "no_stored_ai_review"
        ai_review_lag_hours = None
    elif review_at is None or latest_required_snapshot_at is None:
        ai_review_freshness = "unknown"
        ai_review_freshness_reason = "ai_review_or_required_snapshot_timestamp_invalid"
        ai_review_lag_hours = None
    elif review_at >= latest_required_snapshot_at:
        ai_review_freshness = "current"
        ai_review_freshness_reason = "ai_review_current_with_latest_required_snapshot"
        ai_review_lag_hours = 0.0
    else:
        ai_review_freshness = "behind_latest_snapshot"
        ai_review_freshness_reason = "ai_review_older_than_latest_required_snapshot"
        ai_review_lag_hours = round(
            (latest_required_snapshot_at - review_at).total_seconds() / 3600,
            2,
        )

    return {
        "staleness_status": status,
        "latest_position_snapshot_at": position_at,
        "latest_position_snapshot_age_hours": required_ages[0],
        "latest_performance_snapshot_at": performance_at,
        "latest_performance_snapshot_age_hours": required_ages[1],
        "latest_trade_evaluation_at": evaluation_at,
        "latest_trade_evaluation_age_hours": required_ages[2],
        "latest_ai_review_at": review_at,
        "latest_ai_review_age_hours": _age_hours(review_at, now),
        "freshness_reason": reason,
        "ai_review_freshness": ai_review_freshness,
        "latest_required_snapshot_at": latest_required_snapshot_at,
        "ai_review_lag_hours": ai_review_lag_hours,
        "ai_review_freshness_reason": ai_review_freshness_reason,
    }


def _latest_evaluations(evaluations):
    latest = {}
    for evaluation in evaluations:
        key = str(getattr(evaluation, "broker_order_id", "") or "") or str(
            getattr(evaluation, "order_intent_id", "") or ""
        )
        if not key:
            key = str(getattr(evaluation, "demo_trade_evaluation_id", "") or "")
        if not key:
            continue

        existing = latest.get(key)
        evaluated_at = _timestamp(evaluation, "evaluated_at")
        existing_at = _timestamp(existing, "evaluated_at") if existing is not None else None
        evaluation_key = (
            evaluated_at,
            str(getattr(evaluation, "demo_trade_evaluation_id", "")),
        )
        existing_key = (
            existing_at,
            str(getattr(existing, "demo_trade_evaluation_id", "")),
        ) if existing is not None else None
        if existing is None or evaluation_key >= existing_key:
            latest[key] = evaluation
    return latest


def _latest_daily_ai_review(storage, symbol):
    loader = getattr(storage, "load_demo_daily_ai_reviews", None)
    if not callable(loader):
        return None
    try:
        reviews = list(loader(symbol=symbol) or [])
    except TypeError:
        return None
    if not reviews:
        return None
    return max(
        reviews,
        key=lambda review: (
            _timestamp(review, "reviewed_at"),
            str(getattr(review, "demo_daily_ai_review_id", "")),
        ),
    )


def build_demo_status_dashboard(*, symbol: str, storage) -> DemoStatusDashboardResult:
    """Compose latest local demo state without writes, network calls, or actions."""

    if not symbol:
        raise ValueError("symbol is required")

    performance_dashboard = build_demo_trade_performance_dashboard(
        symbol=symbol,
        storage=storage,
    )
    performance_snapshots = list(
        storage.load_demo_trade_performance_snapshots(symbol=symbol) or []
    )
    position_snapshots = list(storage.load_demo_position_snapshots(symbol=symbol) or [])
    evaluations = list(storage.load_demo_trade_evaluations(symbol=symbol) or [])
    latest_evaluations = _latest_evaluations(evaluations)
    board = build_demo_promotion_board(symbol=symbol, storage=storage)
    opportunity = build_demo_current_opportunity_ratings(symbol=symbol, storage=storage)
    latest_daily_ai_review = _latest_daily_ai_review(storage, symbol)
    freshness = _snapshot_freshness(
        position_snapshots=position_snapshots,
        performance_snapshots=performance_snapshots,
        evaluations=evaluations,
        latest_daily_ai_review=latest_daily_ai_review,
    )

    board_by_hypothesis = {item.source_hypothesis_id: item for item in board.board_items}
    summary_risk_by_hypothesis = {
        item.source_hypothesis_id: item.board_recommendation == "blocked"
        for item in board.board_items
    }
    opportunity_by_key = {}
    opportunity_by_hypothesis = {}
    for item in opportunity.ratings:
        key = item.broker_order_id or item.order_intent_id
        if key:
            opportunity_by_key[key] = item
        if item.source_hypothesis_id:
            opportunity_by_hypothesis[item.source_hypothesis_id] = item

    evaluation_by_key = {}
    for evaluation in latest_evaluations.values():
        key = str(getattr(evaluation, "broker_order_id", "") or "") or str(
            getattr(evaluation, "order_intent_id", "") or ""
        )
        if key:
            evaluation_by_key[key] = evaluation

    trades = []
    for trade in performance_dashboard.trades:
        key = trade.broker_order_id or trade.order_intent_id
        evaluation = evaluation_by_key.get(key)
        opportunity_item = opportunity_by_key.get(key) or opportunity_by_hypothesis.get(
            trade.source_hypothesis_id
        )
        board_item = board_by_hypothesis.get(trade.source_hypothesis_id)
        exit_readiness, exit_reason, exit_action = classify_demo_exit_readiness(
            trade=trade,
            evaluation=evaluation,
            summary_risk_breach=summary_risk_by_hypothesis.get(
                trade.source_hypothesis_id, False
            ),
        )
        trades.append(
            DemoStatusTradeRow(
                source_hypothesis_id=trade.source_hypothesis_id,
                demo_trade_candidate_id=trade.demo_trade_candidate_id,
                order_intent_id=trade.order_intent_id,
                broker_order_id=trade.broker_order_id,
                entry_price=trade.filled_avg_price,
                current_price=(
                    opportunity_item.latest_current_price
                    if opportunity_item is not None
                    else trade.current_price
                ),
                entry_performance_rating=(
                    opportunity_item.entry_performance_rating
                    if opportunity_item is not None
                    else trade.current_rating
                ),
                entry_unrealized_plpc=(
                    opportunity_item.entry_unrealized_plpc
                    if opportunity_item is not None
                    else trade.unrealized_plpc
                ),
                trade_evaluation_status=str(
                    getattr(evaluation, "evaluation_status", "unknown") or "unknown"
                ),
                trade_recommended_action=str(
                    getattr(evaluation, "recommended_action", "manual_review") or "manual_review"
                ),
                hypothesis_summary_rating=(
                    opportunity_item.hypothesis_summary_rating
                    if opportunity_item is not None
                    else (
                        board_item.current_summary_rating
                        if board_item is not None
                        else "unknown"
                    )
                ),
                board_recommendation=(
                    opportunity_item.board_recommendation
                    if opportunity_item is not None
                    else (
                        board_item.board_recommendation
                        if board_item is not None
                        else "unknown"
                    )
                ),
                current_opportunity_rating=(
                    opportunity_item.current_opportunity_rating
                    if opportunity_item is not None
                    else "unknown"
                ),
                current_opportunity_action=(
                    opportunity_item.action if opportunity_item is not None else "no_new_entry"
                ),
                demo_only=trade.demo_only,
                status=trade.status,
                exit_readiness=exit_readiness,
                exit_reason=exit_reason,
                exit_action=exit_action,
                trading_days_elapsed=(
                    getattr(evaluation, "trading_days_elapsed", None)
                    if evaluation is not None
                    else None
                ),
                evaluation_window_trading_days=(
                    getattr(evaluation, "evaluation_window_trading_days", None)
                    if evaluation is not None
                    else None
                ),
                evaluation_days_remaining=(
                    max(
                        int(getattr(evaluation, "evaluation_window_trading_days", 0))
                        - int(getattr(evaluation, "trading_days_elapsed", 0)),
                        0,
                    )
                    if evaluation is not None
                    and getattr(evaluation, "evaluation_window_trading_days", None) is not None
                    and getattr(evaluation, "trading_days_elapsed", None) is not None
                    else None
                ),
                evaluation_window_complete=(
                    getattr(evaluation, "evaluation_window_complete", None)
                    if evaluation is not None
                    else None
                ),
            )
        )

    hypotheses = []
    for board_item in board.board_items:
        opportunity_item = opportunity_by_hypothesis.get(board_item.source_hypothesis_id)
        hypotheses.append(
            DemoStatusHypothesisRow(
                source_hypothesis_id=board_item.source_hypothesis_id,
                trades_evaluated=board_item.trades_evaluated,
                current_summary_rating=board_item.current_summary_rating,
                promotion_readiness=board_item.promotion_readiness,
                board_recommendation=board_item.board_recommendation,
                board_reason=board_item.board_reason,
                current_opportunity_rating=(
                    opportunity_item.current_opportunity_rating
                    if opportunity_item is not None
                    else "unknown"
                ),
                action=opportunity_item.action if opportunity_item is not None else "no_new_entry",
            )
        )

    rating_counts = {
        "not_ready": 0,
        "monitor": 0,
        "review_later": 0,
        "blocked": 0,
        "attractive_now": 0,
        "current_no_new_entry": 0,
    }
    for item in board.board_items:
        rating_counts[item.board_recommendation] = rating_counts.get(item.board_recommendation, 0) + 1
    for item in opportunity.ratings:
        if item.current_opportunity_rating == "attractive_now":
            rating_counts["attractive_now"] += 1
        if item.action == "no_new_entry":
            rating_counts["current_no_new_entry"] += 1

    exit_counts = {
        "exit_hold": 0,
        "exit_needs_more_time": 0,
        "exit_candidate": 0,
        "risk_exit_candidate": 0,
        "exit_unknown": 0,
    }
    for trade in trades:
        if trade.exit_readiness == "hold":
            exit_counts["exit_hold"] += 1
        elif trade.exit_readiness == "needs_more_time":
            exit_counts["exit_needs_more_time"] += 1
        elif trade.exit_readiness == "exit_candidate":
            exit_counts["exit_candidate"] += 1
        elif trade.exit_readiness == "risk_exit_candidate":
            exit_counts["risk_exit_candidate"] += 1
        elif trade.exit_readiness == "unknown":
            exit_counts["exit_unknown"] += 1
    rating_counts.update(exit_counts)

    completed_evaluation_windows = sum(
        trade.evaluation_window_complete is True for trade in trades
    )
    incomplete_evaluation_windows = sum(
        trade.evaluation_window_complete is False for trade in trades
    )
    remaining_days = [
        trade.evaluation_days_remaining
        for trade in trades
        if trade.evaluation_days_remaining is not None
    ]
    rating_counts.update(
        {
            "completed_evaluation_windows": completed_evaluation_windows,
            "incomplete_evaluation_windows": incomplete_evaluation_windows,
            "min_evaluation_days_remaining": min(remaining_days) if remaining_days else None,
            "max_evaluation_days_remaining": max(remaining_days) if remaining_days else None,
        }
    )

    return DemoStatusDashboardResult(
        symbol=symbol,
        records_modified=False,
        position_snapshot=performance_dashboard.position_snapshot,
        trades=tuple(trades),
        hypotheses=tuple(hypotheses),
        open_demo_trades=sum(1 for trade in performance_dashboard.trades if trade.status == "open"),
        total_entry_value=sum(
            trade.entry_value or 0.0 for trade in performance_dashboard.trades
        ),
        total_current_value=sum(
            trade.current_value or 0.0 for trade in performance_dashboard.trades
        ),
        total_unrealized_pl=sum(
            trade.unrealized_pl or 0.0 for trade in performance_dashboard.trades
        ),
        total_unrealized_plpc=(
            sum(trade.unrealized_pl or 0.0 for trade in performance_dashboard.trades)
            / sum(trade.entry_value or 0.0 for trade in performance_dashboard.trades)
            if sum(trade.entry_value or 0.0 for trade in performance_dashboard.trades) > 0
            else 0.0
        ),
        rating_counts=rating_counts,
        latest_daily_ai_review=latest_daily_ai_review,
        **freshness,
    )