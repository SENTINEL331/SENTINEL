"""Deterministic read-only demo broker readiness checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from research.demo_trade_queue import DemoTradeQueueStatus


_ACTIVE_QUEUE_STATUSES = {
    DemoTradeQueueStatus.QUEUED.value,
    DemoTradeQueueStatus.SUBMITTED.value,
    DemoTradeQueueStatus.FILLED.value,
}
_ALLOWED_MODES = {"demo", "paper"}


@dataclass(frozen=True, slots=True)
class DemoBrokerReadiness:
    """Read-only readiness summary for demo broker configuration."""

    broker_mode: str
    live_mode_allowed: bool
    base_url_present: bool
    api_key_present: bool
    api_secret_present: bool
    queue_items_loaded: int
    active_queue_items: int
    demo_only_queue_safe: bool
    ready: bool
    failed_checks: tuple[str, ...] = field(default_factory=tuple)
    rationale: str = ""


def evaluate_demo_broker_readiness(
    *,
    broker_mode: str,
    broker_base_url: str,
    broker_api_key: str,
    broker_api_secret: str,
    queue_items,
) -> DemoBrokerReadiness:
    """Evaluate whether demo broker configuration is safe for demo-only readiness."""

    normalized_mode = (broker_mode or "").strip().casefold()
    base_url_present = bool((broker_base_url or "").strip())
    api_key_present = bool((broker_api_key or "").strip())
    api_secret_present = bool((broker_api_secret or "").strip())

    queue_items_loaded = 0
    active_queue_items = 0
    demo_only_queue_safe = True
    for item in queue_items:
        queue_items_loaded += 1
        item_status = getattr(item, "status", "")
        status_value = getattr(item_status, "value", item_status)
        if status_value in _ACTIVE_QUEUE_STATUSES:
            active_queue_items += 1

        if not bool(getattr(item, "demo_only", False)):
            demo_only_queue_safe = False

    failed_checks: list[str] = []
    if normalized_mode not in _ALLOWED_MODES:
        if normalized_mode == "live":
            failed_checks.append("live_mode_not_allowed")
        else:
            failed_checks.append("broker_mode_invalid")

    if not base_url_present:
        failed_checks.append("broker_base_url_missing")

    if not api_key_present:
        failed_checks.append("broker_api_key_missing")

    if not api_secret_present:
        failed_checks.append("broker_api_secret_missing")

    if not demo_only_queue_safe:
        failed_checks.append("queue_contains_non_demo_item")

    ready = not failed_checks
    rationale = (
        "Demo broker readiness checks passed for read-only demo operation."
        if ready
        else "Demo broker readiness checks failed."
    )

    return DemoBrokerReadiness(
        broker_mode=normalized_mode or "unset",
        live_mode_allowed=False,
        base_url_present=base_url_present,
        api_key_present=api_key_present,
        api_secret_present=api_secret_present,
        queue_items_loaded=queue_items_loaded,
        active_queue_items=active_queue_items,
        demo_only_queue_safe=demo_only_queue_safe,
        ready=ready,
        failed_checks=tuple(failed_checks),
        rationale=rationale,
    )