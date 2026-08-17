"""Append-only local audit record for a completed demo operator run."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class DemoOperatorRunRecord:
    run_id: str
    symbol: str
    created_at: datetime
    operator_status: str
    system_health: str
    system_blocked: bool
    monitoring_cycle_status: str
    dashboard_displayed: bool
    ai_review_requested: bool
    ai_review_confirmed: bool
    ai_calls_made: int
    daily_ai_reviews_created: int
    orders_submitted: int
    orders_cancelled: int
    positions_closed: int
    promotions_performed: int
    decision: str
    decision_reason: str
    position_state: str
    demo_trade_state: str
    evaluation_state: str
    evaluation_progress: str
    evaluation_days_remaining: int | str
    exit_action: str
    new_entry_action: str
    promotion_action: str
    ai_review_action: str
    ai_review_suggested_action: str
    freshness_state: str
    human_next_step: str
    blocked_actions: str
    action_ledger: dict[str, str]
    demo_only: bool = True


def new_demo_operator_run_record(*, symbol, operator_status, system_health, system_blocked,
                                 monitoring_cycle_status, dashboard_displayed,
                                 ai_review_requested, ai_review_confirmed, ai_calls_made,
                                 daily_ai_reviews_created, decision_packet, action_ledger):
    """Create an immutable local audit record from finalized operator output."""

    created_at = datetime.now(timezone.utc)
    run_id = "dor-" + sha256(
        f"{symbol}|{created_at.isoformat()}|{operator_status}|{decision_packet['decision']}".encode(
            "utf-8"
        )
    ).hexdigest()[:16]
    return DemoOperatorRunRecord(
        run_id=run_id,
        symbol=symbol,
        created_at=created_at,
        operator_status=operator_status,
        system_health=system_health,
        system_blocked=system_blocked,
        monitoring_cycle_status=monitoring_cycle_status,
        dashboard_displayed=dashboard_displayed,
        ai_review_requested=ai_review_requested,
        ai_review_confirmed=ai_review_confirmed,
        ai_calls_made=ai_calls_made,
        daily_ai_reviews_created=daily_ai_reviews_created,
        orders_submitted=0,
        orders_cancelled=0,
        positions_closed=0,
        promotions_performed=0,
        decision=decision_packet["decision"],
        decision_reason=decision_packet["decision_reason"],
        position_state=decision_packet["position_state"],
        demo_trade_state=decision_packet["demo_trade_state"],
        evaluation_state=decision_packet["evaluation_state"],
        evaluation_progress=decision_packet["evaluation_progress"],
        evaluation_days_remaining=decision_packet["evaluation_days_remaining"],
        exit_action=decision_packet["exit_action"],
        new_entry_action=decision_packet["new_entry_action"],
        promotion_action=decision_packet["promotion_action"],
        ai_review_action=decision_packet["ai_review_action"],
        ai_review_suggested_action=decision_packet["ai_review_suggested_action"],
        freshness_state=decision_packet["freshness_state"],
        human_next_step=decision_packet["human_next_step"],
        blocked_actions=decision_packet["blocked_actions"],
        action_ledger=dict(action_ledger),
    )