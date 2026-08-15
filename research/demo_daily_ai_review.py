"""Confirmation-gated advisory AI review records for local demo monitoring."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256


AI_REVIEW_TYPE = "daily_light_demo_review"
SAFETY_NOTE = (
    "Advisory commentary only. No commands, trades, closes, promotions, or record mutations are allowed."
)

REQUIRED_FIELDS = (
    "overall_assessment",
    "what_changed_or_matters_today",
    "demo_trade_assessment",
    "exit_assessment",
    "promotion_assessment",
    "current_opportunity_assessment",
    "risk_notes",
    "recommended_human_attention",
    "deeper_ai_review_needed",
    "reason",
    "confidence",
)


@dataclass(frozen=True, slots=True)
class DemoDailyAIReview:
    demo_daily_ai_review_id: str
    symbol: str
    reviewed_at: datetime
    source_dashboard_fingerprint: str
    source_trigger_fingerprint: str
    ai_model: str
    ai_review_type: str
    ai_calls_made: int
    overall_assessment: str
    what_changed_or_matters_today: str
    demo_trade_assessment: str
    exit_assessment: str
    promotion_assessment: str
    current_opportunity_assessment: str
    risk_notes: str
    recommended_human_attention: str
    deeper_ai_review_needed: bool
    reason: str
    confidence: str
    safety_note: str = SAFETY_NOTE
    demo_only: bool = True
    created_by: str = "sentinel"


def _json_object(response):
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError("demo daily AI review response must be valid JSON") from exc
    if not isinstance(response, dict):
        raise ValueError("demo daily AI review response must be a JSON object")
    return response


def parse_demo_daily_ai_review(response):
    """Parse strict advisory JSON and reject unsafe or malformed output."""

    payload = _json_object(response)
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"demo daily AI review missing fields: {', '.join(missing)}")
    if payload["confidence"] not in {"low", "medium", "high"}:
        raise ValueError("demo daily AI review confidence must be low, medium, or high")
    if not isinstance(payload["deeper_ai_review_needed"], bool):
        raise ValueError("demo daily AI review deeper_ai_review_needed must be boolean")
    for field in REQUIRED_FIELDS:
        if field not in {"deeper_ai_review_needed", "confidence"} and not isinstance(payload[field], str):
            raise ValueError(f"demo daily AI review {field} must be a string")
    return payload


def fingerprint_context(value) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(serialized.encode("utf-8")).hexdigest()[:24]


def build_review_context(*, status_dashboard, exit_readiness, trigger):
    """Serialize deterministic local views for the advisory prompt and fingerprints."""

    dashboard_context = {
        "symbol": status_dashboard.symbol,
        "open_demo_trades": status_dashboard.open_demo_trades,
        "total_entry_value": status_dashboard.total_entry_value,
        "total_current_value": status_dashboard.total_current_value,
        "total_unrealized_pl": status_dashboard.total_unrealized_pl,
        "total_unrealized_plpc": status_dashboard.total_unrealized_plpc,
        "trades": [asdict(item) for item in status_dashboard.trades],
        "hypotheses": [asdict(item) for item in status_dashboard.hypotheses],
    }
    exit_context = {
        "items": [asdict(item) for item in exit_readiness.items],
        "readiness_counts": exit_readiness.readiness_counts,
    }
    trigger_context = {
        "ai_review_needed": trigger.ai_review_needed,
        "primary_trigger": trigger.primary_trigger,
        "recommended_action": trigger.recommended_action,
        "reason": trigger.reason,
        "items": [asdict(item) for item in trigger.items],
    }
    return dashboard_context, exit_context, trigger_context


def new_review_from_payload(*, symbol, dashboard_fingerprint, trigger_fingerprint, ai_model, payload, reviewed_at=None):
    reviewed_at = reviewed_at or datetime.now(timezone.utc)
    review_id = "ddair-" + sha256(
        f"{symbol}|{dashboard_fingerprint}|{trigger_fingerprint}|{reviewed_at.isoformat()}".encode("utf-8")
    ).hexdigest()[:16]
    return DemoDailyAIReview(
        demo_daily_ai_review_id=review_id,
        symbol=symbol,
        reviewed_at=reviewed_at,
        source_dashboard_fingerprint=dashboard_fingerprint,
        source_trigger_fingerprint=trigger_fingerprint,
        ai_model=ai_model,
        ai_review_type=AI_REVIEW_TYPE,
        ai_calls_made=1,
        overall_assessment=payload["overall_assessment"],
        what_changed_or_matters_today=payload["what_changed_or_matters_today"],
        demo_trade_assessment=payload["demo_trade_assessment"],
        exit_assessment=payload["exit_assessment"],
        promotion_assessment=payload["promotion_assessment"],
        current_opportunity_assessment=payload["current_opportunity_assessment"],
        risk_notes=payload["risk_notes"],
        recommended_human_attention=payload["recommended_human_attention"],
        deeper_ai_review_needed=payload["deeper_ai_review_needed"],
        reason=payload["reason"],
        confidence=payload["confidence"],
    )