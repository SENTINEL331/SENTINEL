"""Deterministic append-only queue-add flow for gated demo trade candidates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256

from ai.storage import Storage
from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import DemoTradeCandidateStatus
from research.demo_trade_candidate import validate_demo_trade_candidate
from research.demo_trade_queue import DemoTradeQueueItem
from research.demo_trade_queue import DemoTradeQueueStatus


_BLOCKING_QUEUE_STATUSES = {
    DemoTradeQueueStatus.QUEUED,
    DemoTradeQueueStatus.SUBMITTED,
    DemoTradeQueueStatus.FILLED,
}


@dataclass(frozen=True, slots=True)
class DemoTradeQueueAddItem:
    demo_trade_candidate_id: str
    source_hypothesis_id: str
    action: str
    queue_item_id: str | None = None


@dataclass(frozen=True, slots=True)
class DemoTradeQueueAddResult:
    apply_mode: bool
    gate_passed_candidates_loaded: int
    would_queue: int
    queued: int
    skipped_existing: int
    skipped_ineligible: int
    results: tuple[DemoTradeQueueAddItem, ...] = field(default_factory=tuple)


class DemoTradeQueueAddService:
    """Append queue items for eligible gate-passed demo trade candidates."""

    def __init__(self, storage=None):
        self.storage = storage or Storage()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _lineage_key(self, candidate: DemoTradeCandidate) -> str:
        return candidate.source_trade_candidate_id or candidate.trade_candidate_id

    def _latest_timestamp(self, candidate: DemoTradeCandidate) -> datetime:
        return candidate.gate_checked_at or candidate.created_at

    def _select_latest_candidates(self, candidates: list[DemoTradeCandidate]) -> list[DemoTradeCandidate]:
        ordered_keys: list[str] = []
        latest_by_key: dict[str, DemoTradeCandidate] = {}

        for candidate in candidates:
            key = self._lineage_key(candidate)
            existing = latest_by_key.get(key)
            if existing is None:
                ordered_keys.append(key)
                latest_by_key[key] = candidate
                continue

            if self._latest_timestamp(candidate) >= self._latest_timestamp(existing):
                latest_by_key[key] = candidate

        return [latest_by_key[key] for key in ordered_keys]

    def _select_blocking_queue_items(
        self,
        queue_items: list[DemoTradeQueueItem],
    ) -> dict[str, DemoTradeQueueItem]:
        latest_by_candidate_id: dict[str, DemoTradeQueueItem] = {}

        for item in queue_items:
            if item.status not in _BLOCKING_QUEUE_STATUSES:
                continue

            existing = latest_by_candidate_id.get(item.demo_trade_candidate_id)
            if existing is None or item.created_at >= existing.created_at:
                latest_by_candidate_id[item.demo_trade_candidate_id] = item

        return latest_by_candidate_id

    def _new_queue_item_id(
        self,
        symbol: str,
        demo_trade_candidate_id: str,
        created_at: datetime,
    ) -> str:
        digest = sha256(
            f"{symbol}|{demo_trade_candidate_id}|queued|{created_at.isoformat()}".encode("utf-8")
        ).hexdigest()[:12]
        return f"dtq-{symbol}-{digest}"

    def _build_risk_summary(self, candidate: DemoTradeCandidate) -> str:
        if candidate.risk_flags:
            return ", ".join(candidate.risk_flags)

        return "no_additional_risk_flags"

    def _build_queue_item(
        self,
        candidate: DemoTradeCandidate,
        created_at: datetime,
    ) -> DemoTradeQueueItem:
        return DemoTradeQueueItem(
            queue_item_id=self._new_queue_item_id(
                candidate.symbol,
                candidate.trade_candidate_id,
                created_at,
            ),
            symbol=candidate.symbol,
            demo_trade_candidate_id=candidate.trade_candidate_id,
            source_hypothesis_id=candidate.source_hypothesis_id,
            created_at=created_at,
            status=DemoTradeQueueStatus.QUEUED,
            demo_only=True,
            queue_reason="candidate_passed_demo_trade_gate",
            risk_summary=self._build_risk_summary(candidate),
            requested_action="prepare_demo_order",
            created_by="sentinel",
        )

    def apply_for_symbol(self, symbol: str, apply_mode: bool = False) -> DemoTradeQueueAddResult:
        if not symbol:
            raise ValueError("symbol is required")

        candidates = self.storage.load_demo_trade_candidates(symbol=symbol)
        latest_candidates = self._select_latest_candidates(candidates)
        gate_passed_candidates = [
            candidate
            for candidate in latest_candidates
            if candidate.status == DemoTradeCandidateStatus.GATE_PASSED
        ]
        queue_items = self.storage.load_demo_trade_queue_items(symbol=symbol)
        blocking_items_by_candidate_id = self._select_blocking_queue_items(queue_items)

        would_queue = 0
        queued = 0
        skipped_existing = 0
        skipped_ineligible = 0
        results: list[DemoTradeQueueAddItem] = []
        created_at = self._now()

        for candidate in gate_passed_candidates:
            try:
                validate_demo_trade_candidate(candidate)
            except ValueError:
                queue_item = self._build_queue_item(candidate, created_at)
                skipped_ineligible += 1
                results.append(
                    DemoTradeQueueAddItem(
                        demo_trade_candidate_id=candidate.trade_candidate_id,
                        source_hypothesis_id=candidate.source_hypothesis_id,
                        action="skipped_ineligible",
                        queue_item_id=queue_item.queue_item_id,
                    )
                )
                continue

            if not candidate.demo_only:
                queue_item = self._build_queue_item(candidate, created_at)
                skipped_ineligible += 1
                results.append(
                    DemoTradeQueueAddItem(
                        demo_trade_candidate_id=candidate.trade_candidate_id,
                        source_hypothesis_id=candidate.source_hypothesis_id,
                        action="skipped_ineligible",
                        queue_item_id=queue_item.queue_item_id,
                    )
                )
                continue

            existing_queue_item = blocking_items_by_candidate_id.get(candidate.trade_candidate_id)
            if existing_queue_item is not None:
                skipped_existing += 1
                results.append(
                    DemoTradeQueueAddItem(
                        demo_trade_candidate_id=candidate.trade_candidate_id,
                        source_hypothesis_id=candidate.source_hypothesis_id,
                        action="skipped_existing",
                        queue_item_id=existing_queue_item.queue_item_id,
                    )
                )
                continue

            queue_item = self._build_queue_item(candidate, created_at)
            would_queue += 1

            if apply_mode:
                self.storage.save_demo_trade_queue_item(queue_item)
                blocking_items_by_candidate_id[candidate.trade_candidate_id] = queue_item
                queued += 1
                action = "queued"
            else:
                action = "would_queue"

            results.append(
                DemoTradeQueueAddItem(
                    demo_trade_candidate_id=candidate.trade_candidate_id,
                    source_hypothesis_id=candidate.source_hypothesis_id,
                    action=action,
                    queue_item_id=queue_item.queue_item_id,
                )
            )

        return DemoTradeQueueAddResult(
            apply_mode=apply_mode,
            gate_passed_candidates_loaded=len(gate_passed_candidates),
            would_queue=would_queue,
            queued=queued,
            skipped_existing=skipped_existing,
            skipped_ineligible=skipped_ineligible,
            results=tuple(results),
        )