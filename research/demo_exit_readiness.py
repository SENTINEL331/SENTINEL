"""Deterministic read-only exit readiness for currently open demo trades."""

from __future__ import annotations

from dataclasses import dataclass, field

from research.demo_current_opportunity_rating import build_demo_current_opportunity_ratings


EXIT_HOLD = "hold"
EXIT_NEEDS_MORE_TIME = "needs_more_time"
EXIT_CANDIDATE = "exit_candidate"
EXIT_RISK_CANDIDATE = "risk_exit_candidate"
EXIT_NO_POSITION = "no_position"
EXIT_UNKNOWN = "unknown"

EXIT_READINESS_ORDER = (
    EXIT_HOLD,
    EXIT_NEEDS_MORE_TIME,
    EXIT_CANDIDATE,
    EXIT_RISK_CANDIDATE,
    EXIT_NO_POSITION,
    EXIT_UNKNOWN,
)


@dataclass(frozen=True, slots=True)
class DemoExitReadinessItem:
    source_hypothesis_id: str
    demo_trade_candidate_id: str
    order_intent_id: str
    broker_order_id: str
    entry_price: float | None
    current_price: float | None
    entry_unrealized_plpc: float | None
    trade_evaluation_status: str
    evaluation_window_complete: bool | None
    risk_breached: bool
    current_opportunity_rating: str
    exit_readiness: str
    exit_reason: str
    action: str
    note: str = "Read-only exit readiness. No exit order was created and no position was closed."


@dataclass(frozen=True, slots=True)
class DemoExitReadinessResult:
    symbol: str
    performance_snapshots_loaded: int
    evaluations_loaded: int
    readiness_displayed: int
    records_modified: bool = False
    items: tuple[DemoExitReadinessItem, ...] = field(default_factory=tuple)
    readiness_counts: dict[str, int] = field(default_factory=dict)


def _number(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_demo_exit_readiness(*, trade, evaluation, summary_risk_breach: bool):
    is_open = str(getattr(trade, "status", "") or "").casefold() == "open"
    if not is_open:
        return EXIT_NO_POSITION, "no_open_demo_trade", "no_action"

    entry_unrealized_plpc = _number(
        getattr(
            trade,
            "entry_unrealized_plpc",
            getattr(trade, "unrealized_plpc", None),
        )
    )
    risk_breached = bool(getattr(evaluation, "risk_breached", False)) if evaluation else False
    risk_breached = risk_breached or summary_risk_breach
    if risk_breached or (
        entry_unrealized_plpc is not None and entry_unrealized_plpc <= -0.02
    ):
        return EXIT_RISK_CANDIDATE, "risk_breach_or_loss_threshold", "prepare_risk_exit_review_only"

    if evaluation is None:
        return EXIT_UNKNOWN, "missing_trade_evaluation", "manual_review"

    evaluation_status = str(getattr(evaluation, "evaluation_status", "") or "")
    evaluation_window_complete = getattr(evaluation, "evaluation_window_complete", None)
    current_rating = str(getattr(evaluation, "current_rating", "") or "")
    if (
        bool(evaluation_window_complete)
        and current_rating in {"weak_demo", "weak_window"}
    ) or evaluation_status == "weak_window":
        return EXIT_CANDIDATE, "weak_demo_evidence", "prepare_exit_review_only"

    if evaluation_status == "needs_more_time":
        return EXIT_NEEDS_MORE_TIME, "evaluation_window_incomplete", "continue_monitoring"

    if (
        evaluation_window_complete is False
        and current_rating in {"flat_open", "positive_open"}
    ):
        return EXIT_HOLD, "evaluation_window_incomplete", "continue_monitoring"

    return EXIT_UNKNOWN, "missing_or_unrecognized_exit_data", "manual_review"


def build_demo_exit_readiness(*, symbol: str, storage) -> DemoExitReadinessResult:
    """Review local open demo trades without writes, calls, or exit actions."""

    if not symbol:
        raise ValueError("symbol is required")

    from research.demo_status_dashboard import _latest_evaluations, build_demo_status_dashboard

    status_dashboard = build_demo_status_dashboard(symbol=symbol, storage=storage)
    evaluations = list(storage.load_demo_trade_evaluations(symbol=symbol) or [])
    latest_evaluations = _latest_evaluations(evaluations)
    opportunity_result = build_demo_current_opportunity_ratings(symbol=symbol, storage=storage)
    opportunity_by_key = {}
    opportunity_by_hypothesis = {}
    for rating in opportunity_result.ratings:
        key = rating.broker_order_id or rating.order_intent_id
        if key:
            opportunity_by_key[key] = rating
        if rating.source_hypothesis_id:
            opportunity_by_hypothesis[rating.source_hypothesis_id] = rating

    summary_risk_by_hypothesis = {}
    for hypothesis in status_dashboard.hypotheses:
        summary_risk_by_hypothesis[hypothesis.source_hypothesis_id] = (
            hypothesis.board_recommendation == "blocked"
        )

    items = []
    for trade in status_dashboard.trades:
        key = trade.broker_order_id or trade.order_intent_id
        evaluation = latest_evaluations.get(key)
        opportunity = opportunity_by_key.get(key) or opportunity_by_hypothesis.get(
            trade.source_hypothesis_id
        )
        readiness, reason, action = classify_demo_exit_readiness(
            trade=trade,
            evaluation=evaluation,
            summary_risk_breach=summary_risk_by_hypothesis.get(
                trade.source_hypothesis_id, False
            ),
        )
        items.append(
            DemoExitReadinessItem(
                source_hypothesis_id=trade.source_hypothesis_id,
                demo_trade_candidate_id=trade.demo_trade_candidate_id,
                order_intent_id=trade.order_intent_id,
                broker_order_id=trade.broker_order_id,
                entry_price=trade.entry_price,
                current_price=trade.current_price,
                entry_unrealized_plpc=trade.entry_unrealized_plpc,
                trade_evaluation_status=(
                    str(getattr(evaluation, "evaluation_status", "unknown") or "unknown")
                ),
                evaluation_window_complete=(
                    getattr(evaluation, "evaluation_window_complete", None)
                    if evaluation is not None
                    else None
                ),
                risk_breached=bool(getattr(evaluation, "risk_breached", False))
                or summary_risk_by_hypothesis.get(trade.source_hypothesis_id, False),
                current_opportunity_rating=(
                    opportunity.current_opportunity_rating
                    if opportunity is not None
                    else trade.current_opportunity_rating
                ),
                exit_readiness=readiness,
                exit_reason=reason,
                action=action,
            )
        )

    counts = {label: 0 for label in EXIT_READINESS_ORDER}
    for item in items:
        counts[item.exit_readiness] += 1
    return DemoExitReadinessResult(
        symbol=symbol,
        performance_snapshots_loaded=(
            opportunity_result.performance_snapshots_loaded
        ),
        evaluations_loaded=len(evaluations),
        readiness_displayed=len(items),
        items=tuple(items),
        readiness_counts=counts,
    )