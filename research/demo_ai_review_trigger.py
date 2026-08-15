"""Deterministic read-only decisions about whether demo AI review is warranted."""

from __future__ import annotations

from dataclasses import dataclass, field

from research.demo_exit_readiness import build_demo_exit_readiness
from research.demo_status_dashboard import build_demo_status_dashboard


TRIGGER_NONE = "none"
TRIGGER_SCHEDULED = "scheduled_review_candidate"
TRIGGER_WINDOW_COMPLETE = "evaluation_window_complete"
TRIGGER_RISK_BREACH = "risk_breach"
TRIGGER_EXIT = "exit_candidate"
TRIGGER_PROMOTION = "promotion_review_candidate"
TRIGGER_DISAGREEMENT = "disagreement_review_candidate"
TRIGGER_UNKNOWN = "unknown"

TRIGGER_ORDER = (
    TRIGGER_NONE,
    TRIGGER_SCHEDULED,
    TRIGGER_WINDOW_COMPLETE,
    TRIGGER_RISK_BREACH,
    TRIGGER_EXIT,
    TRIGGER_PROMOTION,
    TRIGGER_DISAGREEMENT,
    TRIGGER_UNKNOWN,
)


@dataclass(frozen=True, slots=True)
class DemoAIReviewTriggerItem:
    source_hypothesis_id: str
    trade_evaluation_status: str
    evaluation_window_complete: bool | None
    board_recommendation: str
    current_opportunity_rating: str
    exit_readiness: str
    ai_review_needed: bool
    trigger: str
    reason: str


@dataclass(frozen=True, slots=True)
class DemoAIReviewTriggerResult:
    symbol: str
    evaluations_loaded: int
    open_demo_trades: int
    completed_evaluation_windows: int
    risk_breaches: int
    exit_candidates: int
    risk_exit_candidates: int
    promotion_review_candidates: int
    disagreement_candidates: int
    ai_review_needed: bool
    primary_trigger: str
    recommended_action: str
    reason: str
    review_scope: str
    credits_spend_recommended: bool
    records_modified: bool = False
    items: tuple[DemoAIReviewTriggerItem, ...] = field(default_factory=tuple)


def _item_decision(*, trade, exit_item):
    evaluation_status = trade.trade_evaluation_status
    window_complete = exit_item.evaluation_window_complete if exit_item else None
    board_recommendation = trade.board_recommendation
    opportunity_rating = trade.current_opportunity_rating
    exit_readiness = exit_item.exit_readiness if exit_item else trade.exit_readiness
    risk_breached = bool(exit_item.risk_breached) if exit_item else False

    if risk_breached:
        return True, TRIGGER_RISK_BREACH, "risk_breach_detected"
    if exit_readiness == "risk_exit_candidate":
        return True, TRIGGER_RISK_BREACH, "risk_exit_candidate_detected"
    if exit_readiness == "exit_candidate":
        return True, TRIGGER_EXIT, "exit_candidate_detected"
    if window_complete is True and evaluation_status != "needs_more_time":
        return True, TRIGGER_WINDOW_COMPLETE, "evaluation_window_complete"
    if board_recommendation == "review_later":
        return True, TRIGGER_PROMOTION, "promotion_review_candidate"
    if board_recommendation == "blocked":
        return True, TRIGGER_RISK_BREACH, "blocked_demo_evidence"
    if (
        trade.entry_performance_rating in {"positive_open", "promising_demo"}
        and opportunity_rating in {"risk_warning", "blocked"}
    ):
        return True, TRIGGER_DISAGREEMENT, "entry_and_current_opportunity_disagree"
    if window_complete is None or not evaluation_status:
        return False, TRIGGER_UNKNOWN, "missing_demo_review_data"
    if evaluation_status == "needs_more_time" and window_complete is False:
        return False, TRIGGER_NONE, "evaluation_window_incomplete"
    return False, TRIGGER_NONE, "no_review_trigger"


def build_demo_ai_review_trigger(*, symbol: str, storage) -> DemoAIReviewTriggerResult:
    """Decide whether local demo evidence warrants AI review; never calls AI."""

    if not symbol:
        raise ValueError("symbol is required")

    status_dashboard = build_demo_status_dashboard(symbol=symbol, storage=storage)
    exit_result = build_demo_exit_readiness(symbol=symbol, storage=storage)
    exit_by_key = {}
    exit_by_hypothesis = {}
    for item in exit_result.items:
        key = item.broker_order_id or item.order_intent_id
        if key:
            exit_by_key[key] = item
        if item.source_hypothesis_id:
            exit_by_hypothesis[item.source_hypothesis_id] = item

    items = []
    for trade in status_dashboard.trades:
        key = str(getattr(trade, "broker_order_id", "") or "") or str(
            getattr(trade, "order_intent_id", "") or ""
        )
        exit_item = exit_by_key.get(key) or exit_by_hypothesis.get(
            trade.source_hypothesis_id
        )
        needed, trigger, reason = _item_decision(trade=trade, exit_item=exit_item)
        items.append(
            DemoAIReviewTriggerItem(
                source_hypothesis_id=trade.source_hypothesis_id,
                trade_evaluation_status=trade.trade_evaluation_status,
                evaluation_window_complete=(
                    exit_item.evaluation_window_complete if exit_item else None
                ),
                board_recommendation=trade.board_recommendation,
                current_opportunity_rating=trade.current_opportunity_rating,
                exit_readiness=exit_item.exit_readiness if exit_item else trade.exit_readiness,
                ai_review_needed=needed,
                trigger=trigger,
                reason=reason,
            )
        )

    completed_windows = sum(item.evaluation_window_complete is True for item in items)
    risk_breaches = sum(
        item.trigger == TRIGGER_RISK_BREACH or item.exit_readiness == "risk_exit_candidate"
        for item in items
    )
    exit_candidates = sum(item.exit_readiness == "exit_candidate" for item in items)
    risk_exit_candidates = sum(
        item.exit_readiness == "risk_exit_candidate" for item in items
    )
    promotion_candidates = sum(
        item.board_recommendation == "review_later" for item in items
    )
    disagreement_candidates = sum(
        item.trigger == TRIGGER_DISAGREEMENT for item in items
    )

    triggered = [item for item in items if item.ai_review_needed]
    priority = (
        TRIGGER_RISK_BREACH,
        TRIGGER_EXIT,
        TRIGGER_WINDOW_COMPLETE,
        TRIGGER_PROMOTION,
        TRIGGER_DISAGREEMENT,
    )
    primary_trigger = TRIGGER_NONE
    if triggered:
        primary_trigger = next(
            (trigger for trigger in priority if any(item.trigger == trigger for item in triggered)),
            triggered[0].trigger,
        )
    if not items:
        primary_trigger = TRIGGER_UNKNOWN
        reason = "missing_demo_review_data"
        ai_review_needed = False
    elif triggered:
        reason = next(item.reason for item in triggered if item.trigger == primary_trigger)
        ai_review_needed = True
    else:
        reason = "evaluation_window_incomplete"
        ai_review_needed = False

    return DemoAIReviewTriggerResult(
        symbol=symbol,
        evaluations_loaded=exit_result.evaluations_loaded,
        open_demo_trades=status_dashboard.open_demo_trades,
        completed_evaluation_windows=completed_windows,
        risk_breaches=risk_breaches,
        exit_candidates=exit_candidates,
        risk_exit_candidates=risk_exit_candidates,
        promotion_review_candidates=promotion_candidates,
        disagreement_candidates=disagreement_candidates,
        ai_review_needed=ai_review_needed,
        primary_trigger=primary_trigger,
        recommended_action=(
            "review_demo_evidence_with_ai" if ai_review_needed else "continue_demo_monitoring"
        ),
        reason=reason,
        review_scope=("demo_trade_and_hypothesis_evidence" if ai_review_needed else "none"),
        credits_spend_recommended=ai_review_needed,
        items=tuple(items),
    )