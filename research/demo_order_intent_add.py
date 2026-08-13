"""Append-only local demo order intent preparation from queued demo trade candidates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ai.storage import Storage
from research.demo_order_intent import DemoOrderIntentStatus
from research.demo_order_intent import build_demo_order_intent_from_queue_item
from research.demo_order_intent import validate_demo_order_intent
from research.demo_trade_queue import DemoTradeQueueItem
from research.demo_trade_queue import DemoTradeQueueStatus


@dataclass(frozen=True, slots=True)
class DemoOrderIntentAddItem:
    queue_item_id: str
    demo_trade_candidate_id: str
    source_hypothesis_id: str
    action: str
    order_intent_id: str | None = None
    notional: float | None = None


@dataclass(frozen=True, slots=True)
class DemoOrderIntentAddResult:
    apply_mode: bool
    queued_items_loaded: int
    would_prepare: int
    prepared: int
    skipped_existing: int
    skipped_ineligible: int
    failed_validation: int
    results: tuple[DemoOrderIntentAddItem, ...] = field(default_factory=tuple)


class DemoOrderIntentAddService:
    """Prepare local demo order intents for queued demo trade candidates."""

    def __init__(self, storage=None):
        self.storage = storage or Storage()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _blocking_intent_by_queue_item_id(self, intents) -> dict[str, object]:
        latest_by_queue: dict[str, object] = {}
        for intent in intents:
            if intent.status not in {
                DemoOrderIntentStatus.PREPARED,
                DemoOrderIntentStatus.SUBMITTED,
                DemoOrderIntentStatus.FILLED,
            }:
                continue
            existing = latest_by_queue.get(intent.queue_item_id)
            if existing is None or intent.created_at >= existing.created_at:
                latest_by_queue[intent.queue_item_id] = intent
        return latest_by_queue

    def apply_for_symbol(self, symbol: str, apply_mode: bool = False) -> DemoOrderIntentAddResult:
        if not symbol:
            raise ValueError("symbol is required")

        queue_items = self.storage.load_demo_trade_queue_items(symbol=symbol)
        candidates = self.storage.load_demo_trade_candidates(symbol=symbol)
        candidates_by_id = {item.trade_candidate_id: item for item in candidates}
        existing_intents = self.storage.load_demo_order_intents(symbol=symbol)
        blocking_by_queue = self._blocking_intent_by_queue_item_id(existing_intents)

        would_prepare = 0
        prepared = 0
        skipped_existing = 0
        skipped_ineligible = 0
        failed_validation = 0
        results: list[DemoOrderIntentAddItem] = []

        for queue_item in queue_items:
            if not isinstance(queue_item, DemoTradeQueueItem):
                skipped_ineligible += 1
                results.append(
                    DemoOrderIntentAddItem(
                        queue_item_id=str(getattr(queue_item, "queue_item_id", "")),
                        demo_trade_candidate_id=str(getattr(queue_item, "demo_trade_candidate_id", "")),
                        source_hypothesis_id=str(getattr(queue_item, "source_hypothesis_id", "")),
                        action="skipped_ineligible",
                    )
                )
                continue

            if queue_item.status != DemoTradeQueueStatus.QUEUED:
                skipped_ineligible += 1
                results.append(
                    DemoOrderIntentAddItem(
                        queue_item_id=queue_item.queue_item_id,
                        demo_trade_candidate_id=queue_item.demo_trade_candidate_id,
                        source_hypothesis_id=queue_item.source_hypothesis_id,
                        action="skipped_ineligible",
                    )
                )
                continue

            if not queue_item.demo_only:
                skipped_ineligible += 1
                results.append(
                    DemoOrderIntentAddItem(
                        queue_item_id=queue_item.queue_item_id,
                        demo_trade_candidate_id=queue_item.demo_trade_candidate_id,
                        source_hypothesis_id=queue_item.source_hypothesis_id,
                        action="skipped_ineligible",
                    )
                )
                continue

            candidate = candidates_by_id.get(queue_item.demo_trade_candidate_id)
            if candidate is None:
                skipped_ineligible += 1
                results.append(
                    DemoOrderIntentAddItem(
                        queue_item_id=queue_item.queue_item_id,
                        demo_trade_candidate_id=queue_item.demo_trade_candidate_id,
                        source_hypothesis_id=queue_item.source_hypothesis_id,
                        action="skipped_ineligible",
                    )
                )
                continue

            existing_intent = blocking_by_queue.get(queue_item.queue_item_id)
            if existing_intent is not None:
                skipped_existing += 1
                results.append(
                    DemoOrderIntentAddItem(
                        queue_item_id=queue_item.queue_item_id,
                        demo_trade_candidate_id=queue_item.demo_trade_candidate_id,
                        source_hypothesis_id=queue_item.source_hypothesis_id,
                        action="skipped_existing",
                        order_intent_id=getattr(existing_intent, "order_intent_id", None),
                        notional=getattr(existing_intent, "notional", None),
                    )
                )
                continue

            try:
                intent = build_demo_order_intent_from_queue_item(
                    queue_item=queue_item,
                    candidate=candidate,
                    created_at=self._now(),
                    created_by="sentinel",
                )
                validate_demo_order_intent(intent, storage=self.storage)
            except ValueError:
                failed_validation += 1
                results.append(
                    DemoOrderIntentAddItem(
                        queue_item_id=queue_item.queue_item_id,
                        demo_trade_candidate_id=queue_item.demo_trade_candidate_id,
                        source_hypothesis_id=queue_item.source_hypothesis_id,
                        action="failed_validation",
                        order_intent_id=None,
                        notional=None,
                    )
                )
                continue

            would_prepare += 1
            action = "would_prepare"
            order_intent_id = intent.order_intent_id
            notional = intent.notional

            if apply_mode:
                self.storage.save_demo_order_intent(intent)
                prepared += 1
                action = "prepared"

            results.append(
                DemoOrderIntentAddItem(
                    queue_item_id=queue_item.queue_item_id,
                    demo_trade_candidate_id=queue_item.demo_trade_candidate_id,
                    source_hypothesis_id=queue_item.source_hypothesis_id,
                    action=action,
                    order_intent_id=order_intent_id,
                    notional=notional,
                )
            )

        return DemoOrderIntentAddResult(
            apply_mode=apply_mode,
            queued_items_loaded=len(queue_items),
            would_prepare=would_prepare,
            prepared=prepared,
            skipped_existing=skipped_existing,
            skipped_ineligible=skipped_ineligible,
            failed_validation=failed_validation,
            results=tuple(results),
        )
