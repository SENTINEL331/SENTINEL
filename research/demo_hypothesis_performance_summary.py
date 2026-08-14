"""Append-only deterministic demo evidence summaries aggregated per source hypothesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256

from config import settings
from research.demo_trade_evaluation import (
    EVALUATION_STATUS_FLAT_WINDOW,
    EVALUATION_STATUS_NEEDS_MORE_TIME,
    EVALUATION_STATUS_RISK_BREACH,
    EVALUATION_STATUS_SUCCESSFUL_WINDOW,
    EVALUATION_STATUS_UNKNOWN,
    EVALUATION_STATUS_WEAK_WINDOW,
)


RATING_RISK_BREACH = "risk_breach"
RATING_NEEDS_MORE_TIME = "needs_more_time"
RATING_PROMISING_DEMO = "promising_demo"
RATING_WEAK_DEMO = "weak_demo"
RATING_FLAT_DEMO = "flat_demo"
RATING_UNKNOWN = "unknown"

READINESS_NOT_READY = "not_ready"
READINESS_MONITOR = "monitor"
READINESS_REVIEW_LATER = "review_later"

SUMMARY_NOTE = "Demo evidence summary only. Not a promotion decision."

SUMMARY_RATING_ORDER = (
    RATING_NEEDS_MORE_TIME,
    RATING_PROMISING_DEMO,
    RATING_FLAT_DEMO,
    RATING_WEAK_DEMO,
    RATING_RISK_BREACH,
    RATING_UNKNOWN,
)

_MINIMUM_TRADES_FOR_REVIEW = 3


@dataclass(frozen=True, slots=True)
class DemoHypothesisPerformanceSummary:
    demo_hypothesis_summary_id: str
    symbol: str
    source_hypothesis_id: str
    summarized_at: datetime
    evaluation_fingerprint: str
    evaluation_ids: tuple[str, ...] = field(default_factory=tuple)
    demo_trade_candidate_ids: tuple[str, ...] = field(default_factory=tuple)
    trades_evaluated: int = 0
    unique_demo_trade_candidates: int = 0
    needs_more_time_count: int = 0
    successful_window_count: int = 0
    flat_window_count: int = 0
    weak_window_count: int = 0
    risk_breach_count: int = 0
    unknown_count: int = 0
    evaluation_window_complete_count: int = 0
    open_count: int = 0
    total_entry_value: float = 0.0
    total_current_value: float = 0.0
    total_unrealized_pl: float = 0.0
    total_unrealized_plpc: float = 0.0
    average_unrealized_plpc: float = 0.0
    best_unrealized_plpc: float | None = None
    worst_unrealized_plpc: float | None = None
    risk_breach_rate: float = 0.0
    completion_rate: float = 0.0
    current_summary_rating: str = RATING_UNKNOWN
    promotion_readiness: str = READINESS_NOT_READY
    note: str = SUMMARY_NOTE
    demo_only: bool = True
    created_by: str = "sentinel"


@dataclass(frozen=True, slots=True)
class DemoHypothesisPerformanceSummaryResult:
    symbol: str
    trade_evaluations_loaded: int
    hypotheses_summarized: int
    summaries_created: int
    skipped_existing: int
    skipped_ineligible: int
    failed_summaries: int
    records_modified: bool
    summaries: tuple[DemoHypothesisPerformanceSummary, ...] = field(default_factory=tuple)
    rating_counts: dict[str, int] = field(default_factory=dict)


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


def build_evaluation_fingerprint(evaluation_ids) -> str:
    """Stable fingerprint of the exact evaluation set behind a summary."""

    joined = "|".join(sorted(str(item) for item in evaluation_ids if item))
    return sha256(joined.encode("utf-8")).hexdigest()[:16]


def _new_demo_hypothesis_summary_id(*, symbol: str, source_hypothesis_id: str, fingerprint: str) -> str:
    digest = sha256(f"{symbol}|{source_hypothesis_id}|{fingerprint}".encode("utf-8")).hexdigest()[:12]
    return f"dhps-{symbol}-{digest}"


def classify_summary_rating(
    *,
    trades_evaluated: int,
    needs_more_time_count: int,
    successful_window_count: int,
    flat_window_count: int,
    weak_window_count: int,
    risk_breach_count: int,
) -> str:
    """Deterministic demo evidence rating. Not a promotion decision."""

    if risk_breach_count > 0:
        return RATING_RISK_BREACH

    if trades_evaluated > 0 and needs_more_time_count == trades_evaluated:
        return RATING_NEEDS_MORE_TIME

    if successful_window_count > 0:
        return RATING_PROMISING_DEMO

    if weak_window_count > 0:
        return RATING_WEAK_DEMO

    if flat_window_count > 0:
        return RATING_FLAT_DEMO

    return RATING_UNKNOWN


def classify_promotion_readiness(
    *,
    trades_evaluated: int,
    needs_more_time_count: int,
    evaluation_window_complete_count: int,
) -> str:
    """Informational readiness only for v0. Never returns promote."""

    if trades_evaluated < _MINIMUM_TRADES_FOR_REVIEW:
        return READINESS_NOT_READY

    if trades_evaluated >= 1 and needs_more_time_count == trades_evaluated:
        return READINESS_MONITOR

    if evaluation_window_complete_count == 0:
        return READINESS_NOT_READY

    return READINESS_REVIEW_LATER


def _latest_evaluations(evaluations):
    latest: dict[str, object] = {}
    for evaluation in evaluations:
        key = str(getattr(evaluation, "broker_order_id", "") or "") or str(
            getattr(evaluation, "order_intent_id", "") or ""
        )
        if not key:
            key = str(getattr(evaluation, "demo_trade_evaluation_id", "") or "")
        if not key:
            continue

        existing = latest.get(key)
        if existing is None:
            latest[key] = evaluation
            continue

        evaluated_at = _as_datetime(getattr(evaluation, "evaluated_at", None)) or datetime.min.replace(
            tzinfo=timezone.utc
        )
        existing_at = _as_datetime(getattr(existing, "evaluated_at", None)) or datetime.min.replace(
            tzinfo=timezone.utc
        )
        if evaluated_at >= existing_at:
            latest[key] = evaluation

    return latest


def build_demo_hypothesis_performance_summaries(*, symbol: str, storage) -> DemoHypothesisPerformanceSummaryResult:
    """Append deterministic per-hypothesis demo evidence summaries from stored evaluations only."""

    if not symbol:
        raise ValueError("symbol is required")

    demo_broker_settings = settings.get_demo_broker_settings()
    if _normalize(demo_broker_settings.get("mode")) == "live":
        raise ValueError("live trading is not allowed")

    evaluations = list(storage.load_demo_trade_evaluations(symbol=symbol) or [])
    existing_summaries = list(storage.load_demo_hypothesis_performance_summaries(symbol=symbol) or [])

    existing_keys = {
        (
            str(getattr(summary, "source_hypothesis_id", "") or ""),
            str(getattr(summary, "evaluation_fingerprint", "") or ""),
        )
        for summary in existing_summaries
    }

    grouped: dict[str, list] = {}
    skipped_ineligible = 0
    failed_summaries = 0
    for evaluation in _latest_evaluations(evaluations).values():
        if not str(getattr(evaluation, "demo_trade_evaluation_id", "") or ""):
            failed_summaries += 1
            continue

        source_hypothesis_id = str(getattr(evaluation, "source_hypothesis_id", "") or "")
        if not source_hypothesis_id:
            skipped_ineligible += 1
            continue

        grouped.setdefault(source_hypothesis_id, []).append(evaluation)

    summaries: list[DemoHypothesisPerformanceSummary] = []
    skipped_existing = 0
    rating_counts = {rating: 0 for rating in SUMMARY_RATING_ORDER}

    for source_hypothesis_id in sorted(grouped):
        group = grouped[source_hypothesis_id]
        evaluation_ids = tuple(
            sorted(str(getattr(item, "demo_trade_evaluation_id", "") or "") for item in group)
        )
        fingerprint = build_evaluation_fingerprint(evaluation_ids)
        if (source_hypothesis_id, fingerprint) in existing_keys:
            skipped_existing += 1
            continue

        demo_trade_candidate_ids = tuple(
            sorted(
                {
                    str(getattr(item, "demo_trade_candidate_id", "") or "")
                    for item in group
                    if getattr(item, "demo_trade_candidate_id", "")
                }
            )
        )

        trades_evaluated = len(group)
        status_counts = {
            EVALUATION_STATUS_NEEDS_MORE_TIME: 0,
            EVALUATION_STATUS_SUCCESSFUL_WINDOW: 0,
            EVALUATION_STATUS_FLAT_WINDOW: 0,
            EVALUATION_STATUS_WEAK_WINDOW: 0,
            EVALUATION_STATUS_RISK_BREACH: 0,
            EVALUATION_STATUS_UNKNOWN: 0,
        }
        evaluation_window_complete_count = 0
        open_count = 0
        total_entry_value = 0.0
        total_current_value = 0.0
        total_unrealized_pl = 0.0
        plpc_values: list[float] = []

        for item in group:
            status = str(getattr(item, "evaluation_status", "") or EVALUATION_STATUS_UNKNOWN)
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts[EVALUATION_STATUS_UNKNOWN] += 1

            if bool(getattr(item, "evaluation_window_complete", False)):
                evaluation_window_complete_count += 1

            plpc = _safe_float(getattr(item, "unrealized_plpc", None))
            if plpc is not None:
                # Open here means the trade still has a live mark-to-market value.
                open_count += 1
                plpc_values.append(plpc)

            entry_value = _safe_float(getattr(item, "entry_value", None))
            if entry_value is not None:
                total_entry_value += entry_value

            current_value = _safe_float(getattr(item, "current_value", None))
            if current_value is not None:
                total_current_value += current_value

            unrealized_pl = _safe_float(getattr(item, "unrealized_pl", None))
            if unrealized_pl is not None:
                total_unrealized_pl += unrealized_pl

        total_unrealized_plpc = (
            (total_unrealized_pl / total_entry_value) if total_entry_value > 0 else 0.0
        )
        average_unrealized_plpc = (sum(plpc_values) / len(plpc_values)) if plpc_values else 0.0
        best_unrealized_plpc = max(plpc_values) if plpc_values else None
        worst_unrealized_plpc = min(plpc_values) if plpc_values else None
        risk_breach_count = status_counts[EVALUATION_STATUS_RISK_BREACH]
        risk_breach_rate = (risk_breach_count / trades_evaluated) if trades_evaluated > 0 else 0.0
        completion_rate = (
            (evaluation_window_complete_count / trades_evaluated) if trades_evaluated > 0 else 0.0
        )

        current_summary_rating = classify_summary_rating(
            trades_evaluated=trades_evaluated,
            needs_more_time_count=status_counts[EVALUATION_STATUS_NEEDS_MORE_TIME],
            successful_window_count=status_counts[EVALUATION_STATUS_SUCCESSFUL_WINDOW],
            flat_window_count=status_counts[EVALUATION_STATUS_FLAT_WINDOW],
            weak_window_count=status_counts[EVALUATION_STATUS_WEAK_WINDOW],
            risk_breach_count=risk_breach_count,
        )
        promotion_readiness = classify_promotion_readiness(
            trades_evaluated=trades_evaluated,
            needs_more_time_count=status_counts[EVALUATION_STATUS_NEEDS_MORE_TIME],
            evaluation_window_complete_count=evaluation_window_complete_count,
        )

        summary = DemoHypothesisPerformanceSummary(
            demo_hypothesis_summary_id=_new_demo_hypothesis_summary_id(
                symbol=symbol,
                source_hypothesis_id=source_hypothesis_id,
                fingerprint=fingerprint,
            ),
            symbol=symbol,
            source_hypothesis_id=source_hypothesis_id,
            summarized_at=datetime.now(timezone.utc),
            evaluation_fingerprint=fingerprint,
            evaluation_ids=evaluation_ids,
            demo_trade_candidate_ids=demo_trade_candidate_ids,
            trades_evaluated=trades_evaluated,
            unique_demo_trade_candidates=len(demo_trade_candidate_ids),
            needs_more_time_count=status_counts[EVALUATION_STATUS_NEEDS_MORE_TIME],
            successful_window_count=status_counts[EVALUATION_STATUS_SUCCESSFUL_WINDOW],
            flat_window_count=status_counts[EVALUATION_STATUS_FLAT_WINDOW],
            weak_window_count=status_counts[EVALUATION_STATUS_WEAK_WINDOW],
            risk_breach_count=risk_breach_count,
            unknown_count=status_counts[EVALUATION_STATUS_UNKNOWN],
            evaluation_window_complete_count=evaluation_window_complete_count,
            open_count=open_count,
            total_entry_value=total_entry_value,
            total_current_value=total_current_value,
            total_unrealized_pl=total_unrealized_pl,
            total_unrealized_plpc=total_unrealized_plpc,
            average_unrealized_plpc=average_unrealized_plpc,
            best_unrealized_plpc=best_unrealized_plpc,
            worst_unrealized_plpc=worst_unrealized_plpc,
            risk_breach_rate=risk_breach_rate,
            completion_rate=completion_rate,
            current_summary_rating=current_summary_rating,
            promotion_readiness=promotion_readiness,
            demo_only=all(bool(getattr(item, "demo_only", True)) for item in group),
            created_by="sentinel",
        )

        storage.save_demo_hypothesis_performance_summary(summary)
        summaries.append(summary)
        existing_keys.add((source_hypothesis_id, fingerprint))
        rating_counts[current_summary_rating] += 1

    return DemoHypothesisPerformanceSummaryResult(
        symbol=symbol,
        trade_evaluations_loaded=len(evaluations),
        hypotheses_summarized=len(grouped),
        summaries_created=len(summaries),
        skipped_existing=skipped_existing,
        skipped_ineligible=skipped_ineligible,
        failed_summaries=failed_summaries,
        records_modified=bool(summaries),
        summaries=tuple(summaries),
        rating_counts=rating_counts,
    )
