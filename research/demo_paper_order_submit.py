"""Deterministic append-only Alpaca paper order submission for prepared demo order intents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from json import JSONDecodeError, loads
from socket import timeout as SocketTimeout
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ai.storage import Storage
from config import settings
from research.demo_broker_account import check_demo_broker_account
from research.demo_broker_readiness import evaluate_demo_broker_readiness
from research.demo_order_intent import DemoOrderIntent, DemoOrderIntentStatus


_SUPPORTED_BROKER = "alpaca"
_ALLOWED_MODES = {"paper", "demo"}


@dataclass(frozen=True, slots=True)
class DemoPaperOrderSubmitItem:
    order_intent_id: str
    queue_item_id: str
    demo_trade_candidate_id: str
    symbol: str
    source_hypothesis_id: str
    action: str
    broker_order_id: str | None = None
    status: str | None = None
    notional: float | None = None


@dataclass(frozen=True, slots=True)
class DemoPaperOrderSubmitResult:
    apply_mode: bool
    confirm_paper_submit: bool
    intents_loaded: int
    would_submit: int
    submitted: int
    skipped_existing: int
    skipped_ineligible: int
    refused_without_confirmation: int
    results: tuple[DemoPaperOrderSubmitItem, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class DemoBrokerOrderRecord:
    broker_order_id: str
    order_intent_id: str
    symbol: str
    queue_item_id: str
    demo_trade_candidate_id: str
    source_hypothesis_id: str
    created_at: datetime
    status: str = "submitted"
    demo_only: bool = True
    side: str = "buy"
    order_type: str = "market"
    time_in_force: str = "day"
    notional: float | None = None
    quantity: float | None = None
    limit_price: float | None = None
    stop_price: float | None = None
    broker: str = "alpaca"
    mode: str = "paper"
    api_response_status: str = "accepted"
    rationale: str = ""
    created_by: str = "sentinel"


class DemoPaperOrderSubmitService:
    """Submit prepared demo order intents to the Alpaca paper endpoint after explicit confirmation."""

    def __init__(self, storage=None):
        self.storage = storage or Storage()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _new_broker_order_id(self, symbol: str, order_intent_id: str, created_at: datetime) -> str:
        digest = sha256(f"{symbol}|{order_intent_id}|submitted|{created_at.isoformat()}".encode("utf-8")).hexdigest()[:12]
        return f"dbo-{symbol}-{digest}"

    def _submit_to_paper_endpoint(
        self,
        *,
        intent: DemoOrderIntent,
        created_at: datetime,
    ) -> DemoBrokerOrderRecord:
        demo_broker_settings = settings.get_demo_broker_settings()
        normalized_broker = (demo_broker_settings.get("broker") or "").strip().casefold()
        normalized_mode = (demo_broker_settings.get("mode") or "").strip().casefold()
        if normalized_broker != _SUPPORTED_BROKER:
            raise ValueError("DEMO_BROKER must be alpaca for paper submission")
        if normalized_mode == "live":
            raise ValueError("live trading is not allowed")
        if normalized_mode not in _ALLOWED_MODES:
            raise ValueError("DEMO_BROKER_MODE must be paper or demo for paper submission")

        base_url = (demo_broker_settings.get("base_url") or "").strip().rstrip("/")
        api_key = (demo_broker_settings.get("api_key") or "").strip()
        secret_key = (demo_broker_settings.get("secret_key") or "").strip()
        if not base_url or not api_key or not secret_key:
            raise ValueError("demo broker settings are incomplete")

        parsed = urlparse(base_url)
        hostname = (parsed.hostname or "").casefold()
        if "paper" not in hostname:
            raise ValueError("Alpaca base URL must point to a paper or demo endpoint")

        payload = {
            "symbol": intent.symbol,
            "side": intent.side,
            "type": intent.order_type,
            "time_in_force": intent.time_in_force,
        }
        if intent.quantity is not None:
            payload["qty"] = str(intent.quantity)
        if intent.notional is not None:
            payload["notional"] = str(intent.notional)
        if intent.limit_price is not None:
            payload["limit_price"] = str(intent.limit_price)
        if intent.stop_price is not None:
            payload["stop_price"] = str(intent.stop_price)

        request = Request(
            f"{base_url}/v2/orders",
            headers={
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": secret_key,
                "accept": "application/json",
                "content-type": "application/json",
            },
            data=__import__("json").dumps(payload).encode("utf-8"),
            method="POST",
        )

        response_payload = {}
        try:
            with urlopen(request, timeout=10) as response:
                response_body = response.read().decode("utf-8")
                response_payload = loads(response_body) if response_body else {}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"paper order submission rejected by Alpaca: {detail or exc.reason}") from exc
        except (SocketTimeout, TimeoutError, URLError) as exc:
            raise ValueError("unable to reach the Alpaca paper order endpoint") from exc
        except (JSONDecodeError, UnicodeDecodeError):
            response_payload = {}

        broker_order_id = str(response_payload.get("id") or self._new_broker_order_id(intent.symbol, intent.order_intent_id, created_at))
        return DemoBrokerOrderRecord(
            broker_order_id=broker_order_id,
            order_intent_id=intent.order_intent_id,
            symbol=intent.symbol,
            queue_item_id=intent.queue_item_id,
            demo_trade_candidate_id=intent.demo_trade_candidate_id,
            source_hypothesis_id=intent.source_hypothesis_id,
            created_at=created_at,
            status="submitted",
            demo_only=True,
            side=intent.side,
            order_type=intent.order_type,
            time_in_force=intent.time_in_force,
            notional=intent.notional,
            quantity=intent.quantity,
            limit_price=intent.limit_price,
            stop_price=intent.stop_price,
            broker=normalized_broker,
            mode=normalized_mode,
            api_response_status=str(response_payload.get("status") or "accepted"),
            rationale="Demo paper order submitted append-only.",
            created_by="sentinel",
        )

    def apply_for_symbol(
        self,
        symbol: str,
        apply_mode: bool = False,
        confirm_paper_submit: bool = False,
    ) -> DemoPaperOrderSubmitResult:
        if not symbol:
            raise ValueError("symbol is required")

        intents = self.storage.load_demo_order_intents(symbol=symbol)
        queue_items = self.storage.load_demo_trade_queue_items(symbol=symbol)
        queue_by_id = {item.queue_item_id: item for item in queue_items}
        existing_records = self.storage.load_demo_broker_order_records(symbol=symbol)
        submitted_by_intent = {record.order_intent_id: record for record in existing_records}

        would_submit = 0
        submitted = 0
        skipped_existing = 0
        skipped_ineligible = 0
        refused_without_confirmation = 0
        results: list[DemoPaperOrderSubmitItem] = []

        for intent in intents:
            if not isinstance(intent, DemoOrderIntent):
                skipped_ineligible += 1
                results.append(
                    DemoPaperOrderSubmitItem(
                        order_intent_id=str(getattr(intent, "order_intent_id", "")),
                        queue_item_id=str(getattr(intent, "queue_item_id", "")),
                        demo_trade_candidate_id=str(getattr(intent, "demo_trade_candidate_id", "")),
                        symbol=str(getattr(intent, "symbol", symbol)),
                        source_hypothesis_id=str(getattr(intent, "source_hypothesis_id", "")),
                        action="skipped_ineligible",
                        notional=getattr(intent, "notional", None),
                    )
                )
                continue

            if intent.status != DemoOrderIntentStatus.PREPARED:
                skipped_ineligible += 1
                results.append(
                    DemoPaperOrderSubmitItem(
                        order_intent_id=intent.order_intent_id,
                        queue_item_id=intent.queue_item_id,
                        demo_trade_candidate_id=intent.demo_trade_candidate_id,
                        symbol=intent.symbol,
                        source_hypothesis_id=intent.source_hypothesis_id,
                        action="skipped_ineligible",
                        notional=intent.notional,
                    )
                )
                continue

            if not intent.demo_only:
                skipped_ineligible += 1
                results.append(
                    DemoPaperOrderSubmitItem(
                        order_intent_id=intent.order_intent_id,
                        queue_item_id=intent.queue_item_id,
                        demo_trade_candidate_id=intent.demo_trade_candidate_id,
                        symbol=intent.symbol,
                        source_hypothesis_id=intent.source_hypothesis_id,
                        action="skipped_ineligible",
                        notional=intent.notional,
                    )
                )
                continue

            queue_item = queue_by_id.get(intent.queue_item_id)
            if queue_item is not None and getattr(queue_item, "status", None) not in {"queued", "submitted", "filled"}:
                skipped_ineligible += 1
                results.append(
                    DemoPaperOrderSubmitItem(
                        order_intent_id=intent.order_intent_id,
                        queue_item_id=intent.queue_item_id,
                        demo_trade_candidate_id=intent.demo_trade_candidate_id,
                        symbol=intent.symbol,
                        source_hypothesis_id=intent.source_hypothesis_id,
                        action="skipped_ineligible",
                        notional=intent.notional,
                    )
                )
                continue

            if intent.order_intent_id in submitted_by_intent:
                skipped_existing += 1
                results.append(
                    DemoPaperOrderSubmitItem(
                        order_intent_id=intent.order_intent_id,
                        queue_item_id=intent.queue_item_id,
                        demo_trade_candidate_id=intent.demo_trade_candidate_id,
                        symbol=intent.symbol,
                        source_hypothesis_id=intent.source_hypothesis_id,
                        action="skipped_existing",
                        broker_order_id=submitted_by_intent[intent.order_intent_id].broker_order_id,
                        status=submitted_by_intent[intent.order_intent_id].status,
                        notional=intent.notional,
                    )
                )
                continue

            would_submit += 1

            if apply_mode and not confirm_paper_submit:
                refused_without_confirmation += 1
                results.append(
                    DemoPaperOrderSubmitItem(
                        order_intent_id=intent.order_intent_id,
                        queue_item_id=intent.queue_item_id,
                        demo_trade_candidate_id=intent.demo_trade_candidate_id,
                        symbol=intent.symbol,
                        source_hypothesis_id=intent.source_hypothesis_id,
                        action="refused_without_confirmation",
                        notional=intent.notional,
                    )
                )
                continue

            if not apply_mode:
                results.append(
                    DemoPaperOrderSubmitItem(
                        order_intent_id=intent.order_intent_id,
                        queue_item_id=intent.queue_item_id,
                        demo_trade_candidate_id=intent.demo_trade_candidate_id,
                        symbol=intent.symbol,
                        source_hypothesis_id=intent.source_hypothesis_id,
                        action="would_submit",
                        notional=intent.notional,
                    )
                )
                continue

            try:
                readiness = evaluate_demo_broker_readiness(
                    broker=(settings.DEMO_BROKER or "").strip(),
                    broker_mode=(settings.DEMO_BROKER_MODE or "").strip(),
                    broker_base_url=(settings.ALPACA_BASE_URL or "").strip(),
                    broker_api_key=(settings.ALPACA_API_KEY or "").strip(),
                    broker_api_secret=(settings.ALPACA_SECRET_KEY or "").strip(),
                    queue_items=queue_items,
                )
                if not readiness.ready:
                    raise ValueError("demo broker readiness failed")

                account_check = check_demo_broker_account(
                    broker=(settings.DEMO_BROKER or "").strip(),
                    mode=(settings.DEMO_BROKER_MODE or "").strip(),
                    base_url=(settings.ALPACA_BASE_URL or "").strip(),
                    api_key=(settings.ALPACA_API_KEY or "").strip(),
                    secret_key=(settings.ALPACA_SECRET_KEY or "").strip(),
                )
                if not account_check.account_reachable:
                    raise ValueError(account_check.rationale or "broker account not reachable")

                record = self._submit_to_paper_endpoint(intent=intent, created_at=self._now())
                self.storage.save_demo_broker_order_record(record)
                submitted += 1
                results.append(
                    DemoPaperOrderSubmitItem(
                        order_intent_id=intent.order_intent_id,
                        queue_item_id=intent.queue_item_id,
                        demo_trade_candidate_id=intent.demo_trade_candidate_id,
                        symbol=intent.symbol,
                        source_hypothesis_id=intent.source_hypothesis_id,
                        action="submitted",
                        broker_order_id=record.broker_order_id,
                        status=record.status,
                        notional=intent.notional,
                    )
                )
            except ValueError:
                skipped_ineligible += 1
                results.append(
                    DemoPaperOrderSubmitItem(
                        order_intent_id=intent.order_intent_id,
                        queue_item_id=intent.queue_item_id,
                        demo_trade_candidate_id=intent.demo_trade_candidate_id,
                        symbol=intent.symbol,
                        source_hypothesis_id=intent.source_hypothesis_id,
                        action="skipped_ineligible",
                        notional=intent.notional,
                    )
                )

        return DemoPaperOrderSubmitResult(
            apply_mode=apply_mode,
            confirm_paper_submit=confirm_paper_submit,
            intents_loaded=len(intents),
            would_submit=would_submit,
            submitted=submitted,
            skipped_existing=skipped_existing,
            skipped_ineligible=skipped_ineligible,
            refused_without_confirmation=refused_without_confirmation,
            results=tuple(results),
        )
