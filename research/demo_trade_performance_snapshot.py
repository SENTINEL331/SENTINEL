"""Local append-only demo trade performance snapshots derived from stored demo records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256

from config import settings


@dataclass(frozen=True, slots=True)
class DemoTradePerformanceSnapshot:
    performance_snapshot_id: str
    symbol: str
    order_intent_id: str
    broker_order_id: str
    broker_order_record_id: str
    queue_item_id: str
    demo_trade_candidate_id: str
    source_hypothesis_id: str
    snapshot_at: datetime
    status: str
    side: str
    filled_qty: float | None = None
    filled_avg_price: float | None = None
    current_price: float | None = None
    entry_value: float | None = None
    current_value: float | None = None
    unrealized_pl: float | None = None
    unrealized_plpc: float | None = None
    position_snapshot_id: str = ""
    demo_only: bool = True
    created_by: str = "sentinel"


@dataclass(frozen=True, slots=True)
class DemoTradePerformanceSnapshotResult:
    broker_orders_loaded: int
    filled_orders_evaluated: int
    performance_snapshots_created: int
    skipped_not_filled: int
    skipped_missing_position: int
    failed_calculations: int
    records_modified: bool
    snapshots: tuple[DemoTradePerformanceSnapshot, ...] = field(default_factory=tuple)
    total_entry_value: float = 0.0
    total_current_value: float = 0.0
    total_unrealized_pl: float = 0.0
    total_unrealized_plpc: float = 0.0


def _new_performance_snapshot_id(*, symbol: str, broker_order_id: str, snapshot_at: datetime) -> str:
    digest = sha256(f"{symbol}|{broker_order_id}|{snapshot_at.isoformat()}".encode("utf-8")).hexdigest()[:12]
    return f"dpsp-{symbol}-{digest}"


def _normalize(value: str) -> str:
    return (value or "").strip().casefold()


def _safe_float(value):
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_filled_status(status_record) -> bool:
    status_value = _normalize(str(getattr(status_record, "status", "") or ""))
    raw_status = _normalize(str(getattr(status_record, "raw_status", "") or ""))
    return status_value == "filled" or raw_status == "filled"


def _latest_by_key(items, key_name: str):
    latest = {}
    for item in items:
        key = getattr(item, key_name, "")
        if not key:
            continue

        existing = latest.get(key)
        if existing is None or getattr(item, "synced_at", getattr(item, "created_at", datetime.min.replace(tzinfo=timezone.utc))) >= getattr(existing, "synced_at", getattr(existing, "created_at", datetime.min.replace(tzinfo=timezone.utc))):
            latest[key] = item

    return latest


def build_demo_trade_performance_snapshots(*, symbol: str, storage) -> DemoTradePerformanceSnapshotResult:
    """Build local append-only performance snapshots without broker or AI calls."""

    if not symbol:
        raise ValueError("symbol is required")

    demo_broker_settings = settings.get_demo_broker_settings()
    normalized_mode = _normalize(demo_broker_settings.get("mode"))
    if normalized_mode == "live":
        raise ValueError("live trading is not allowed")

    order_records = storage.load_demo_broker_order_records(symbol=symbol)
    order_statuses = storage.load_demo_broker_order_statuses(symbol=symbol)
    position_snapshots = storage.load_demo_position_snapshots(symbol=symbol)
    order_intents = storage.load_demo_order_intents(symbol=symbol)

    latest_status_by_order_id = _latest_by_key(order_statuses, "broker_order_id")
    latest_position_snapshot = None
    for snapshot in position_snapshots:
        if getattr(snapshot, "status", "") == "open" and _safe_float(getattr(snapshot, "current_price", None)) is not None:
            if latest_position_snapshot is None or getattr(snapshot, "synced_at") >= getattr(latest_position_snapshot, "synced_at"):
                latest_position_snapshot = snapshot

    intents_by_id = {getattr(intent, "order_intent_id", ""): intent for intent in order_intents if getattr(intent, "order_intent_id", "")}

    snapshots: list[DemoTradePerformanceSnapshot] = []
    filled_orders_evaluated = 0
    skipped_not_filled = 0
    skipped_missing_position = 0
    failed_calculations = 0
    total_entry_value = 0.0
    total_current_value = 0.0
    total_unrealized_pl = 0.0

    for record in order_records:
        broker_order_id = str(getattr(record, "broker_order_id", "") or "")
        if not broker_order_id:
            continue

        status_record = latest_status_by_order_id.get(broker_order_id)
        if status_record is None or not _is_filled_status(status_record):
            skipped_not_filled += 1
            continue

        filled_qty = _safe_float(getattr(status_record, "filled_qty", None))
        filled_avg_price = _safe_float(getattr(status_record, "filled_avg_price", None))
        if filled_qty is None or filled_avg_price is None:
            failed_calculations += 1
            continue

        filled_orders_evaluated += 1

        if latest_position_snapshot is None:
            skipped_missing_position += 1
            continue

        current_price = _safe_float(getattr(latest_position_snapshot, "current_price", None))
        if current_price is None:
            skipped_missing_position += 1
            continue

        entry_value = filled_qty * filled_avg_price
        current_value = filled_qty * current_price
        unrealized_pl = current_value - entry_value
        unrealized_plpc = (unrealized_pl / entry_value) if entry_value > 0 else 0.0

        intent = intents_by_id.get(getattr(record, "order_intent_id", ""))
        snapshot_at = datetime.now(timezone.utc)
        snapshot = DemoTradePerformanceSnapshot(
            performance_snapshot_id=_new_performance_snapshot_id(
                symbol=symbol,
                broker_order_id=broker_order_id,
                snapshot_at=snapshot_at,
            ),
            symbol=symbol,
            order_intent_id=str(getattr(record, "order_intent_id", "") or ""),
            broker_order_id=broker_order_id,
            broker_order_record_id=str(getattr(record, "broker_order_id", "") or ""),
            queue_item_id=str(getattr(intent, "queue_item_id", getattr(record, "queue_item_id", "")) or ""),
            demo_trade_candidate_id=str(getattr(intent, "demo_trade_candidate_id", getattr(record, "demo_trade_candidate_id", "")) or ""),
            source_hypothesis_id=str(getattr(intent, "source_hypothesis_id", getattr(record, "source_hypothesis_id", "")) or ""),
            snapshot_at=snapshot_at,
            status="open",
            side="long",
            filled_qty=filled_qty,
            filled_avg_price=filled_avg_price,
            current_price=current_price,
            entry_value=entry_value,
            current_value=current_value,
            unrealized_pl=unrealized_pl,
            unrealized_plpc=unrealized_plpc,
            position_snapshot_id=str(getattr(latest_position_snapshot, "position_snapshot_id", "") or ""),
            demo_only=bool(getattr(record, "demo_only", True)),
            created_by=str(getattr(record, "created_by", "sentinel") or "sentinel"),
        )
        storage.save_demo_trade_performance_snapshot(snapshot)
        snapshots.append(snapshot)
        total_entry_value += entry_value
        total_current_value += current_value
        total_unrealized_pl += unrealized_pl

    total_unrealized_plpc = (total_unrealized_pl / total_entry_value) if total_entry_value > 0 else 0.0

    return DemoTradePerformanceSnapshotResult(
        broker_orders_loaded=len(order_records),
        filled_orders_evaluated=filled_orders_evaluated,
        performance_snapshots_created=len(snapshots),
        skipped_not_filled=skipped_not_filled,
        skipped_missing_position=skipped_missing_position,
        failed_calculations=failed_calculations,
        records_modified=bool(snapshots),
        snapshots=tuple(snapshots),
        total_entry_value=total_entry_value,
        total_current_value=total_current_value,
        total_unrealized_pl=total_unrealized_pl,
        total_unrealized_plpc=total_unrealized_plpc,
    )