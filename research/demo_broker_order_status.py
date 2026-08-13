"""Append-only Alpaca paper order status sync for previously submitted demo orders."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from json import JSONDecodeError, loads
from socket import timeout as SocketTimeout
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from config import settings


_SUPPORTED_BROKER = "alpaca"
_ALLOWED_MODES = {"paper"}
_REQUEST_TIMEOUT_SECONDS = 10


@dataclass(frozen=True, slots=True)
class DemoBrokerOrderStatus:
    """Append-only status snapshot for one broker order."""

    broker_order_status_id: str
    broker_order_record_id: str
    order_intent_id: str
    symbol: str
    broker: str
    broker_mode: str
    broker_order_id: str
    synced_at: datetime
    status: str
    raw_status: str
    filled_qty: float | None = None
    filled_avg_price: float | None = None
    submitted_notional: float | None = None
    submitted_quantity: float | None = None
    demo_only: bool = True
    created_by: str = "sentinel"


@dataclass(frozen=True, slots=True)
class DemoBrokerOrderStatusSyncItem:
    order_intent_id: str
    broker_order_id: str
    symbol: str
    action: str
    status: str | None = None
    raw_status: str | None = None
    filled_qty: float | None = None
    filled_avg_price: float | None = None


@dataclass(frozen=True, slots=True)
class DemoBrokerOrderStatusSyncResult:
    records_loaded: int
    status_synced: int
    skipped_ineligible: int
    failed_sync: int
    records_modified: bool
    results: tuple[DemoBrokerOrderStatusSyncItem, ...] = field(default_factory=tuple)
    refused_reason: str | None = None


def _normalize(value: str) -> str:
    return (value or "").strip().casefold()


def _is_paper_endpoint(base_url: str) -> bool:
    parsed = urlparse((base_url or "").strip())
    hostname = (parsed.hostname or "").casefold()
    return bool(hostname) and "paper" in hostname


def _safe_float(value):
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _new_status_id(*, broker_order_record_id: str, broker_order_id: str, synced_at: datetime) -> str:
    digest = sha256(
        f"{broker_order_record_id}|{broker_order_id}|{synced_at.isoformat()}".encode("utf-8")
    ).hexdigest()[:12]
    return f"bos-{digest}"


def _build_status_record(*, record, payload: dict, synced_at: datetime) -> DemoBrokerOrderStatus:
    broker_order_record_id = str(
        getattr(record, "broker_order_record_id", "")
        or getattr(record, "broker_order_id", "")
        or getattr(record, "order_intent_id", "")
    )
    broker_order_id = str(getattr(record, "broker_order_id", "") or "")
    status_value = str(payload.get("status") or "n/a")
    broker = str(getattr(record, "broker", "alpaca") or "alpaca")
    broker_mode = str(getattr(record, "mode", "paper") or "paper")

    return DemoBrokerOrderStatus(
        broker_order_status_id=_new_status_id(
            broker_order_record_id=broker_order_record_id,
            broker_order_id=broker_order_id,
            synced_at=synced_at,
        ),
        broker_order_record_id=broker_order_record_id,
        order_intent_id=str(getattr(record, "order_intent_id", "") or ""),
        symbol=str(getattr(record, "symbol", "") or ""),
        broker=broker,
        broker_mode=broker_mode,
        broker_order_id=broker_order_id,
        synced_at=synced_at,
        status=status_value,
        raw_status=status_value,
        filled_qty=_safe_float(payload.get("filled_qty")),
        filled_avg_price=_safe_float(payload.get("filled_avg_price")),
        submitted_notional=_safe_float(getattr(record, "notional", None)),
        submitted_quantity=_safe_float(getattr(record, "quantity", None)),
        demo_only=bool(getattr(record, "demo_only", True)),
        created_by=str(getattr(record, "created_by", "sentinel") or "sentinel"),
    )


def _build_failed_status_record(*, record, synced_at: datetime, raw_status: str) -> DemoBrokerOrderStatus:
    broker_order_record_id = str(
        getattr(record, "broker_order_record_id", "")
        or getattr(record, "broker_order_id", "")
        or getattr(record, "order_intent_id", "")
    )
    broker_order_id = str(getattr(record, "broker_order_id", "") or "")
    broker = str(getattr(record, "broker", "alpaca") or "alpaca")
    broker_mode = str(getattr(record, "mode", "paper") or "paper")

    return DemoBrokerOrderStatus(
        broker_order_status_id=_new_status_id(
            broker_order_record_id=broker_order_record_id,
            broker_order_id=broker_order_id,
            synced_at=synced_at,
        ),
        broker_order_record_id=broker_order_record_id,
        order_intent_id=str(getattr(record, "order_intent_id", "") or ""),
        symbol=str(getattr(record, "symbol", "") or ""),
        broker=broker,
        broker_mode=broker_mode,
        broker_order_id=broker_order_id,
        synced_at=synced_at,
        status="failed_sync",
        raw_status=raw_status,
        filled_qty=None,
        filled_avg_price=None,
        submitted_notional=_safe_float(getattr(record, "notional", None)),
        submitted_quantity=_safe_float(getattr(record, "quantity", None)),
        demo_only=bool(getattr(record, "demo_only", True)),
        created_by=str(getattr(record, "created_by", "sentinel") or "sentinel"),
    )


def sync_demo_broker_order_statuses(
    *,
    symbol: str,
    storage=None,
    timeout_seconds: int = _REQUEST_TIMEOUT_SECONDS,
    urlopen_fn=urlopen,
) -> DemoBrokerOrderStatusSyncResult:
    """Sync append-only status snapshots for stored demo broker order records."""

    if not symbol:
        raise ValueError("symbol is required")

    if storage is None:
        from ai.storage import Storage

        storage = Storage()

    demo_broker_settings = settings.get_demo_broker_settings()
    normalized_broker = _normalize(demo_broker_settings.get("broker"))
    normalized_mode = _normalize(demo_broker_settings.get("mode"))
    base_url = (demo_broker_settings.get("base_url") or "").strip().rstrip("/")
    api_key = (demo_broker_settings.get("api_key") or "").strip()
    secret_key = (demo_broker_settings.get("secret_key") or "").strip()

    if normalized_broker != _SUPPORTED_BROKER:
        return DemoBrokerOrderStatusSyncResult(
            records_loaded=0,
            status_synced=0,
            skipped_ineligible=0,
            failed_sync=0,
            records_modified=False,
            results=(),
            refused_reason="Demo broker order status sync supports only DEMO_BROKER=alpaca in this slice.",
        )

    if normalized_mode == "live":
        return DemoBrokerOrderStatusSyncResult(
            records_loaded=0,
            status_synced=0,
            skipped_ineligible=0,
            failed_sync=0,
            records_modified=False,
            results=(),
            refused_reason="Live mode is not allowed for demo broker order status sync.",
        )

    if normalized_mode not in _ALLOWED_MODES:
        return DemoBrokerOrderStatusSyncResult(
            records_loaded=0,
            status_synced=0,
            skipped_ineligible=0,
            failed_sync=0,
            records_modified=False,
            results=(),
            refused_reason="DEMO_BROKER_MODE must be paper for demo broker order status sync.",
        )

    if not base_url:
        return DemoBrokerOrderStatusSyncResult(
            records_loaded=0,
            status_synced=0,
            skipped_ineligible=0,
            failed_sync=0,
            records_modified=False,
            results=(),
            refused_reason="Alpaca paper base URL is missing.",
        )

    if not _is_paper_endpoint(base_url):
        return DemoBrokerOrderStatusSyncResult(
            records_loaded=0,
            status_synced=0,
            skipped_ineligible=0,
            failed_sync=0,
            records_modified=False,
            results=(),
            refused_reason="Alpaca base URL must point to a paper or demo endpoint, not a live endpoint.",
        )

    if not api_key or not secret_key:
        return DemoBrokerOrderStatusSyncResult(
            records_loaded=0,
            status_synced=0,
            skipped_ineligible=0,
            failed_sync=0,
            records_modified=False,
            results=(),
            refused_reason="Alpaca paper credentials are missing.",
        )

    records = storage.load_demo_broker_order_records(symbol=symbol)
    results: list[DemoBrokerOrderStatusSyncItem] = []
    status_synced = 0
    skipped_ineligible = 0
    failed_sync = 0

    for record in records:
        broker_order_id = str(getattr(record, "broker_order_id", "") or "")
        if not broker_order_id:
            skipped_ineligible += 1
            results.append(
                DemoBrokerOrderStatusSyncItem(
                    order_intent_id=str(getattr(record, "order_intent_id", "") or ""),
                    broker_order_id="",
                    symbol=str(getattr(record, "symbol", symbol) or symbol),
                    action="skipped_ineligible",
                )
            )
            continue

        if _normalize(getattr(record, "broker", "")) != _SUPPORTED_BROKER:
            skipped_ineligible += 1
            results.append(
                DemoBrokerOrderStatusSyncItem(
                    order_intent_id=str(getattr(record, "order_intent_id", "") or ""),
                    broker_order_id=broker_order_id,
                    symbol=str(getattr(record, "symbol", symbol) or symbol),
                    action="skipped_ineligible",
                )
            )
            continue

        if _normalize(getattr(record, "mode", "")) != "paper":
            skipped_ineligible += 1
            results.append(
                DemoBrokerOrderStatusSyncItem(
                    order_intent_id=str(getattr(record, "order_intent_id", "") or ""),
                    broker_order_id=broker_order_id,
                    symbol=str(getattr(record, "symbol", symbol) or symbol),
                    action="skipped_ineligible",
                )
            )
            continue

        if not bool(getattr(record, "demo_only", True)):
            skipped_ineligible += 1
            results.append(
                DemoBrokerOrderStatusSyncItem(
                    order_intent_id=str(getattr(record, "order_intent_id", "") or ""),
                    broker_order_id=broker_order_id,
                    symbol=str(getattr(record, "symbol", symbol) or symbol),
                    action="skipped_ineligible",
                )
            )
            continue

        if _normalize(getattr(record, "status", "")) != "submitted":
            skipped_ineligible += 1
            results.append(
                DemoBrokerOrderStatusSyncItem(
                    order_intent_id=str(getattr(record, "order_intent_id", "") or ""),
                    broker_order_id=broker_order_id,
                    symbol=str(getattr(record, "symbol", symbol) or symbol),
                    action="skipped_ineligible",
                )
            )
            continue

        request = Request(
            f"{base_url}/v2/orders/{broker_order_id}",
            headers={
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": secret_key,
                "accept": "application/json",
            },
            method="GET",
        )

        synced_at = datetime.now(timezone.utc)
        try:
            with urlopen_fn(request, timeout=timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
                payload = loads(response_body) if response_body else {}
        except HTTPError as exc:
            raw_status = f"http_{exc.code}"
            failed_sync += 1
            status_record = _build_failed_status_record(
                record=record,
                synced_at=synced_at,
                raw_status=raw_status,
            )
            storage.save_demo_broker_order_status(status_record)
            results.append(
                DemoBrokerOrderStatusSyncItem(
                    order_intent_id=status_record.order_intent_id,
                    broker_order_id=status_record.broker_order_id,
                    symbol=status_record.symbol,
                    action="failed_sync",
                    status=status_record.status,
                    raw_status=status_record.raw_status,
                )
            )
            continue
        except (SocketTimeout, TimeoutError):
            raw_status = "timeout"
            failed_sync += 1
            status_record = _build_failed_status_record(
                record=record,
                synced_at=synced_at,
                raw_status=raw_status,
            )
            storage.save_demo_broker_order_status(status_record)
            results.append(
                DemoBrokerOrderStatusSyncItem(
                    order_intent_id=status_record.order_intent_id,
                    broker_order_id=status_record.broker_order_id,
                    symbol=status_record.symbol,
                    action="failed_sync",
                    status=status_record.status,
                    raw_status=status_record.raw_status,
                )
            )
            continue
        except URLError:
            raw_status = "unreachable"
            failed_sync += 1
            status_record = _build_failed_status_record(
                record=record,
                synced_at=synced_at,
                raw_status=raw_status,
            )
            storage.save_demo_broker_order_status(status_record)
            results.append(
                DemoBrokerOrderStatusSyncItem(
                    order_intent_id=status_record.order_intent_id,
                    broker_order_id=status_record.broker_order_id,
                    symbol=status_record.symbol,
                    action="failed_sync",
                    status=status_record.status,
                    raw_status=status_record.raw_status,
                )
            )
            continue
        except (JSONDecodeError, UnicodeDecodeError):
            raw_status = "unreadable_response"
            failed_sync += 1
            status_record = _build_failed_status_record(
                record=record,
                synced_at=synced_at,
                raw_status=raw_status,
            )
            storage.save_demo_broker_order_status(status_record)
            results.append(
                DemoBrokerOrderStatusSyncItem(
                    order_intent_id=status_record.order_intent_id,
                    broker_order_id=status_record.broker_order_id,
                    symbol=status_record.symbol,
                    action="failed_sync",
                    status=status_record.status,
                    raw_status=status_record.raw_status,
                )
            )
            continue

        status_record = _build_status_record(record=record, payload=payload, synced_at=synced_at)
        storage.save_demo_broker_order_status(status_record)
        status_synced += 1
        results.append(
            DemoBrokerOrderStatusSyncItem(
                order_intent_id=status_record.order_intent_id,
                broker_order_id=status_record.broker_order_id,
                symbol=status_record.symbol,
                action="synced",
                status=status_record.status,
                raw_status=status_record.raw_status,
                filled_qty=status_record.filled_qty,
                filled_avg_price=status_record.filled_avg_price,
            )
        )

    return DemoBrokerOrderStatusSyncResult(
        records_loaded=len(records),
        status_synced=status_synced,
        skipped_ineligible=skipped_ineligible,
        failed_sync=failed_sync,
        records_modified=bool(status_synced or failed_sync),
        results=tuple(results),
    )