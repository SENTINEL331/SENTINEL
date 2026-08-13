"""Read-only Alpaca paper account connectivity checks."""

from __future__ import annotations

from dataclasses import dataclass
from json import JSONDecodeError, loads
from socket import timeout as SocketTimeout
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


_SUPPORTED_BROKER = "alpaca"
_ALLOWED_MODES = {"paper", "demo"}
_REQUEST_TIMEOUT_SECONDS = 10


@dataclass(frozen=True, slots=True)
class DemoBrokerAccountCheck:
    """Read-only broker account connectivity result."""

    broker: str
    mode: str
    endpoint: str
    account_reachable: bool
    account_status: str
    trading_blocked: bool | str
    account_number: str
    status: str
    rationale: str


def _normalize(value: str) -> str:
    return (value or "").strip().casefold()


def _is_paper_endpoint(base_url: str) -> bool:
    parsed = urlparse((base_url or "").strip())
    hostname = (parsed.hostname or "").casefold()
    return bool(hostname) and "paper" in hostname


def _endpoint_label(base_url: str) -> str:
    if _is_paper_endpoint(base_url):
        return "paper"

    hostname = (urlparse((base_url or "").strip()).hostname or "").casefold()
    if hostname:
        return "live"

    return "n/a"


def _mask_account_number(account_number: str | None) -> str:
    digits = str(account_number or "").strip()
    if not digits:
        return "n/a"

    suffix = digits[-4:] if len(digits) >= 4 else digits
    return f"****{suffix}"


def check_demo_broker_account(
    *,
    broker: str,
    mode: str,
    base_url: str,
    api_key: str,
    secret_key: str,
    timeout_seconds: int = _REQUEST_TIMEOUT_SECONDS,
    urlopen_fn=urlopen,
) -> DemoBrokerAccountCheck:
    """Call Alpaca paper account endpoint in read-only mode and summarize reachability."""

    normalized_broker = _normalize(broker)
    normalized_mode = _normalize(mode)
    endpoint = _endpoint_label(base_url)
    safe_base_url = (base_url or "").strip().rstrip("/")

    if normalized_broker != _SUPPORTED_BROKER:
        return DemoBrokerAccountCheck(
            broker=normalized_broker or "unset",
            mode=normalized_mode or "unset",
            endpoint=endpoint,
            account_reachable=False,
            account_status="n/a",
            trading_blocked="n/a",
            account_number="n/a",
            status="refused",
            rationale="Demo broker account check supports only DEMO_BROKER=alpaca in this slice.",
        )

    if normalized_mode == "live":
        return DemoBrokerAccountCheck(
            broker=normalized_broker,
            mode=normalized_mode,
            endpoint=endpoint,
            account_reachable=False,
            account_status="n/a",
            trading_blocked="n/a",
            account_number="n/a",
            status="refused",
            rationale="Live mode is not allowed for demo broker account checks.",
        )

    if normalized_mode not in _ALLOWED_MODES:
        return DemoBrokerAccountCheck(
            broker=normalized_broker,
            mode=normalized_mode or "unset",
            endpoint=endpoint,
            account_reachable=False,
            account_status="n/a",
            trading_blocked="n/a",
            account_number="n/a",
            status="refused",
            rationale="DEMO_BROKER_MODE must be paper or demo for this command.",
        )

    if not safe_base_url:
        return DemoBrokerAccountCheck(
            broker=normalized_broker,
            mode=normalized_mode,
            endpoint="n/a",
            account_reachable=False,
            account_status="n/a",
            trading_blocked="n/a",
            account_number="n/a",
            status="not_connected",
            rationale="Alpaca paper base URL is missing.",
        )

    if not _is_paper_endpoint(safe_base_url):
        return DemoBrokerAccountCheck(
            broker=normalized_broker,
            mode=normalized_mode,
            endpoint=endpoint,
            account_reachable=False,
            account_status="n/a",
            trading_blocked="n/a",
            account_number="n/a",
            status="refused",
            rationale="Alpaca base URL must point to a paper or demo endpoint, not a live endpoint.",
        )

    if not (api_key or "").strip() or not (secret_key or "").strip():
        return DemoBrokerAccountCheck(
            broker=normalized_broker,
            mode=normalized_mode,
            endpoint=endpoint,
            account_reachable=False,
            account_status="n/a",
            trading_blocked="n/a",
            account_number="n/a",
            status="not_connected",
            rationale="Alpaca paper credentials are missing.",
        )

    request = Request(
        f"{safe_base_url}/v2/account",
        headers={
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key,
            "accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen_fn(request, timeout=timeout_seconds) as response:
            payload = loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 401:
            rationale = "Authentication failed when reaching the Alpaca paper account endpoint."
        else:
            rationale = f"Alpaca paper account endpoint returned HTTP {exc.code}."

        return DemoBrokerAccountCheck(
            broker=normalized_broker,
            mode=normalized_mode,
            endpoint=endpoint,
            account_reachable=False,
            account_status="n/a",
            trading_blocked="n/a",
            account_number="n/a",
            status="not_connected",
            rationale=rationale,
        )
    except (SocketTimeout, TimeoutError):
        return DemoBrokerAccountCheck(
            broker=normalized_broker,
            mode=normalized_mode,
            endpoint=endpoint,
            account_reachable=False,
            account_status="n/a",
            trading_blocked="n/a",
            account_number="n/a",
            status="not_connected",
            rationale="Timed out while reaching the Alpaca paper account endpoint.",
        )
    except URLError:
        return DemoBrokerAccountCheck(
            broker=normalized_broker,
            mode=normalized_mode,
            endpoint=endpoint,
            account_reachable=False,
            account_status="n/a",
            trading_blocked="n/a",
            account_number="n/a",
            status="not_connected",
            rationale="Unable to reach the Alpaca paper account endpoint.",
        )
    except (JSONDecodeError, UnicodeDecodeError):
        return DemoBrokerAccountCheck(
            broker=normalized_broker,
            mode=normalized_mode,
            endpoint=endpoint,
            account_reachable=False,
            account_status="n/a",
            trading_blocked="n/a",
            account_number="n/a",
            status="not_connected",
            rationale="Alpaca paper account endpoint returned an unreadable response.",
        )

    return DemoBrokerAccountCheck(
        broker=normalized_broker,
        mode=normalized_mode,
        endpoint=endpoint,
        account_reachable=True,
        account_status=str(payload.get("status", "n/a") or "n/a"),
        trading_blocked=(
            payload.get("trading_blocked")
            if isinstance(payload.get("trading_blocked"), bool)
            else "n/a"
        ),
        account_number=_mask_account_number(payload.get("account_number")),
        status="connected",
        rationale="Connected to the Alpaca paper account endpoint in read-only mode.",
    )