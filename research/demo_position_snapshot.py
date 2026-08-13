"""Append-only Alpaca paper position snapshot sync for one symbol."""

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
class DemoPositionSnapshot:
    """Append-only position snapshot for one broker symbol."""

    position_snapshot_id: str
    symbol: str
    broker: str
    broker_mode: str
    synced_at: datetime
    status: str
    qty: float | None = None
    side: str = "none"
    market_value: float | None = None
    cost_basis: float | None = None
    avg_entry_price: float | None = None
    current_price: float | None = None
    unrealized_pl: float | None = None
    unrealized_plpc: float | None = None
    asset_id: str = ""
    exchange: str = ""
    demo_only: bool = True
    created_by: str = "sentinel"


@dataclass(frozen=True, slots=True)
class DemoPositionSnapshotSyncResult:
    position_found: bool
    snapshots_loaded: int
    snapshots_created: int
    failed_snapshot: int
    records_modified: bool
    snapshot: DemoPositionSnapshot | None = None
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


def _new_snapshot_id(*, symbol: str, synced_at: datetime, status: str) -> str:
    digest = sha256(f"{symbol}|{synced_at.isoformat()}|{status}".encode("utf-8")).hexdigest()[:12]
    return f"dps-{symbol}-{digest}"


def _build_snapshot(*, symbol: str, broker: str, broker_mode: str, payload: dict, synced_at: datetime) -> DemoPositionSnapshot:
    return DemoPositionSnapshot(
        position_snapshot_id=_new_snapshot_id(symbol=symbol, synced_at=synced_at, status="open"),
        symbol=symbol,
        broker=broker,
        broker_mode=broker_mode,
        synced_at=synced_at,
        status="open",
        qty=_safe_float(payload.get("qty")),
        side=str(payload.get("side") or "none"),
        market_value=_safe_float(payload.get("market_value")),
        cost_basis=_safe_float(payload.get("cost_basis")),
        avg_entry_price=_safe_float(payload.get("avg_entry_price")),
        current_price=_safe_float(payload.get("current_price")),
        unrealized_pl=_safe_float(payload.get("unrealized_pl")),
        unrealized_plpc=_safe_float(payload.get("unrealized_plpc")),
        asset_id=str(payload.get("asset_id") or ""),
        exchange=str(payload.get("exchange") or ""),
        demo_only=True,
        created_by="sentinel",
    )


def _build_no_position_snapshot(*, symbol: str, broker: str, broker_mode: str, synced_at: datetime) -> DemoPositionSnapshot:
    return DemoPositionSnapshot(
        position_snapshot_id=_new_snapshot_id(symbol=symbol, synced_at=synced_at, status="no_position"),
        symbol=symbol,
        broker=broker,
        broker_mode=broker_mode,
        synced_at=synced_at,
        status="no_position",
        qty=None,
        side="none",
        market_value=None,
        cost_basis=None,
        avg_entry_price=None,
        current_price=None,
        unrealized_pl=None,
        unrealized_plpc=None,
        asset_id="",
        exchange="",
        demo_only=True,
        created_by="sentinel",
    )


def _build_failed_snapshot(*, symbol: str, broker: str, broker_mode: str, synced_at: datetime) -> DemoPositionSnapshot:
    return DemoPositionSnapshot(
        position_snapshot_id=_new_snapshot_id(symbol=symbol, synced_at=synced_at, status="failed"),
        symbol=symbol,
        broker=broker,
        broker_mode=broker_mode,
        synced_at=synced_at,
        status="failed",
        qty=None,
        side="none",
        market_value=None,
        cost_basis=None,
        avg_entry_price=None,
        current_price=None,
        unrealized_pl=None,
        unrealized_plpc=None,
        asset_id="",
        exchange="",
        demo_only=True,
        created_by="sentinel",
    )


def sync_demo_position_snapshot(
    *,
    symbol: str,
    storage=None,
    timeout_seconds: int = _REQUEST_TIMEOUT_SECONDS,
    urlopen_fn=urlopen,
) -> DemoPositionSnapshotSyncResult:
    """Sync one append-only paper position snapshot for a symbol."""

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

    existing_snapshots = storage.load_demo_position_snapshots(symbol=symbol)

    if normalized_broker != _SUPPORTED_BROKER:
        return DemoPositionSnapshotSyncResult(
            position_found=False,
            snapshots_loaded=len(existing_snapshots),
            snapshots_created=0,
            failed_snapshot=0,
            records_modified=False,
            snapshot=None,
            refused_reason="Demo position snapshot sync supports only DEMO_BROKER=alpaca in this slice.",
        )

    if normalized_mode == "live":
        return DemoPositionSnapshotSyncResult(
            position_found=False,
            snapshots_loaded=len(existing_snapshots),
            snapshots_created=0,
            failed_snapshot=0,
            records_modified=False,
            snapshot=None,
            refused_reason="Live mode is not allowed for demo position snapshot sync.",
        )

    if normalized_mode not in _ALLOWED_MODES:
        return DemoPositionSnapshotSyncResult(
            position_found=False,
            snapshots_loaded=len(existing_snapshots),
            snapshots_created=0,
            failed_snapshot=0,
            records_modified=False,
            snapshot=None,
            refused_reason="DEMO_BROKER_MODE must be paper for demo position snapshot sync.",
        )

    if not base_url:
        return DemoPositionSnapshotSyncResult(
            position_found=False,
            snapshots_loaded=len(existing_snapshots),
            snapshots_created=0,
            failed_snapshot=0,
            records_modified=False,
            snapshot=None,
            refused_reason="Alpaca paper base URL is missing.",
        )

    if not _is_paper_endpoint(base_url):
        return DemoPositionSnapshotSyncResult(
            position_found=False,
            snapshots_loaded=len(existing_snapshots),
            snapshots_created=0,
            failed_snapshot=0,
            records_modified=False,
            snapshot=None,
            refused_reason="Alpaca base URL must point to a paper or demo endpoint, not a live endpoint.",
        )

    if not api_key or not secret_key:
        return DemoPositionSnapshotSyncResult(
            position_found=False,
            snapshots_loaded=len(existing_snapshots),
            snapshots_created=0,
            failed_snapshot=0,
            records_modified=False,
            snapshot=None,
            refused_reason="Alpaca paper credentials are missing.",
        )

    request = Request(
        f"{base_url}/v2/positions/{symbol}",
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
            snapshot = _build_snapshot(
                symbol=symbol,
                broker=normalized_broker,
                broker_mode=normalized_mode,
                payload=payload,
                synced_at=synced_at,
            )
            storage.save_demo_position_snapshot(snapshot)
            return DemoPositionSnapshotSyncResult(
                position_found=True,
                snapshots_loaded=len(existing_snapshots),
                snapshots_created=1,
                failed_snapshot=0,
                records_modified=True,
                snapshot=snapshot,
            )
    except HTTPError as exc:
        if exc.code == 404:
            snapshot = _build_no_position_snapshot(
                symbol=symbol,
                broker=normalized_broker,
                broker_mode=normalized_mode,
                synced_at=synced_at,
            )
            storage.save_demo_position_snapshot(snapshot)
            return DemoPositionSnapshotSyncResult(
                position_found=False,
                snapshots_loaded=len(existing_snapshots),
                snapshots_created=1,
                failed_snapshot=0,
                records_modified=True,
                snapshot=snapshot,
            )

        snapshot = _build_failed_snapshot(
            symbol=symbol,
            broker=normalized_broker,
            broker_mode=normalized_mode,
            synced_at=synced_at,
        )
        storage.save_demo_position_snapshot(snapshot)
        return DemoPositionSnapshotSyncResult(
            position_found=False,
            snapshots_loaded=len(existing_snapshots),
            snapshots_created=0,
            failed_snapshot=1,
            records_modified=True,
            snapshot=snapshot,
        )
    except (SocketTimeout, TimeoutError):
        snapshot = _build_failed_snapshot(
            symbol=symbol,
            broker=normalized_broker,
            broker_mode=normalized_mode,
            synced_at=synced_at,
        )
        storage.save_demo_position_snapshot(snapshot)
        return DemoPositionSnapshotSyncResult(
            position_found=False,
            snapshots_loaded=len(existing_snapshots),
            snapshots_created=0,
            failed_snapshot=1,
            records_modified=True,
            snapshot=snapshot,
        )
    except URLError:
        snapshot = _build_failed_snapshot(
            symbol=symbol,
            broker=normalized_broker,
            broker_mode=normalized_mode,
            synced_at=synced_at,
        )
        storage.save_demo_position_snapshot(snapshot)
        return DemoPositionSnapshotSyncResult(
            position_found=False,
            snapshots_loaded=len(existing_snapshots),
            snapshots_created=0,
            failed_snapshot=1,
            records_modified=True,
            snapshot=snapshot,
        )
    except (JSONDecodeError, UnicodeDecodeError):
        snapshot = _build_failed_snapshot(
            symbol=symbol,
            broker=normalized_broker,
            broker_mode=normalized_mode,
            synced_at=synced_at,
        )
        storage.save_demo_position_snapshot(snapshot)
        return DemoPositionSnapshotSyncResult(
            position_found=False,
            snapshots_loaded=len(existing_snapshots),
            snapshots_created=0,
            failed_snapshot=1,
            records_modified=True,
            snapshot=snapshot,
        )