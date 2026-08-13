import unittest
from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from research.demo_broker_order_status import sync_demo_broker_order_statuses
from research.runner import run_manual_demo_broker_order_status_sync


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


def _broker_record(**overrides):
    base = {
        "broker_order_id": "br-001",
        "order_intent_id": "doi-NVDA-001",
        "symbol": "NVDA",
        "queue_item_id": "dtq-NVDA-001",
        "demo_trade_candidate_id": "dtc-001",
        "source_hypothesis_id": "hyp-001",
        "created_at": datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        "status": "submitted",
        "demo_only": True,
        "side": "buy",
        "order_type": "market",
        "time_in_force": "day",
        "notional": 100.0,
        "quantity": None,
        "limit_price": None,
        "stop_price": None,
        "broker": "alpaca",
        "mode": "paper",
        "api_response_status": "accepted",
        "rationale": "Demo paper order submitted append-only.",
        "created_by": "sentinel",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class DemoBrokerOrderStatusSyncTests(unittest.TestCase):
    def test_live_mode_is_refused_before_http_call(self):
        calls = []

        def _urlopen(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("HTTP call should not occur")

        storage = Mock()
        storage.load_demo_broker_order_records.return_value = []

        with patch("research.demo_broker_order_status.settings.DEMO_BROKER", "alpaca"), patch(
            "research.demo_broker_order_status.settings.DEMO_BROKER_MODE", "live"
        ), patch("research.demo_broker_order_status.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.demo_broker_order_status.settings.ALPACA_API_KEY", "key"
        ), patch("research.demo_broker_order_status.settings.ALPACA_SECRET_KEY", "secret"):
            result = sync_demo_broker_order_statuses(
                symbol="NVDA",
                storage=storage,
                urlopen_fn=_urlopen,
            )

        self.assertEqual(0, result.records_loaded)
        self.assertEqual("Live mode is not allowed for demo broker order status sync.", result.refused_reason)
        self.assertEqual([], calls)

    def test_non_paper_base_url_is_refused_before_http_call(self):
        calls = []

        def _urlopen(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("HTTP call should not occur")

        storage = Mock()
        storage.load_demo_broker_order_records.return_value = []

        with patch("research.demo_broker_order_status.settings.DEMO_BROKER", "alpaca"), patch(
            "research.demo_broker_order_status.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.demo_broker_order_status.settings.ALPACA_BASE_URL", "https://api.alpaca.markets"), patch(
            "research.demo_broker_order_status.settings.ALPACA_API_KEY", "key"
        ), patch("research.demo_broker_order_status.settings.ALPACA_SECRET_KEY", "secret"):
            result = sync_demo_broker_order_statuses(
                symbol="NVDA",
                storage=storage,
                urlopen_fn=_urlopen,
            )

        self.assertEqual(0, result.records_loaded)
        self.assertEqual("Alpaca base URL must point to a paper or demo endpoint, not a live endpoint.", result.refused_reason)
        self.assertEqual([], calls)

    def test_skips_records_without_broker_order_id_and_non_demo_records(self):
        storage = Mock()
        storage.load_demo_broker_order_records.return_value = [
            _broker_record(broker_order_id=""),
            _broker_record(order_intent_id="doi-NVDA-002", broker="alpaca", mode="paper", demo_only=False),
        ]

        with patch("research.demo_broker_order_status.settings.DEMO_BROKER", "alpaca"), patch(
            "research.demo_broker_order_status.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.demo_broker_order_status.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.demo_broker_order_status.settings.ALPACA_API_KEY", "key"
        ), patch("research.demo_broker_order_status.settings.ALPACA_SECRET_KEY", "secret"):
            result = sync_demo_broker_order_statuses(symbol="NVDA", storage=storage, urlopen_fn=Mock())

        self.assertEqual(2, result.records_loaded)
        self.assertEqual(2, result.skipped_ineligible)
        self.assertEqual(0, result.status_synced)
        self.assertEqual(0, result.failed_sync)
        storage.save_demo_broker_order_status.assert_not_called()

    def test_successful_mocked_get_stores_append_only_status_snapshot(self):
        storage = Mock()
        storage.load_demo_broker_order_records.return_value = [_broker_record()]

        captured = {}

        def _urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["timeout"] = timeout
            return _FakeResponse(b'{"status": "filled", "filled_qty": "1", "filled_avg_price": "123.45"}')

        with patch("research.demo_broker_order_status.settings.DEMO_BROKER", "alpaca"), patch(
            "research.demo_broker_order_status.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.demo_broker_order_status.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.demo_broker_order_status.settings.ALPACA_API_KEY", "key"
        ), patch("research.demo_broker_order_status.settings.ALPACA_SECRET_KEY", "secret"):
            result = sync_demo_broker_order_statuses(symbol="NVDA", storage=storage, urlopen_fn=_urlopen)

        self.assertEqual(1, result.records_loaded)
        self.assertEqual(1, result.status_synced)
        self.assertEqual(0, result.failed_sync)
        self.assertTrue(result.records_modified)
        self.assertEqual("https://paper-api.alpaca.markets/v2/orders/br-001", captured["url"])
        self.assertEqual(10, captured["timeout"])
        self.assertEqual("key", captured["headers"]["Apca-api-key-id"])
        self.assertEqual("secret", captured["headers"]["Apca-api-secret-key"])
        storage.save_demo_broker_order_status.assert_called_once()
        saved_status = storage.save_demo_broker_order_status.call_args.args[0]
        self.assertEqual("filled", saved_status.status)
        self.assertEqual(1.0, saved_status.filled_qty)
        self.assertEqual(123.45, saved_status.filled_avg_price)

    def test_failed_http_response_records_failed_sync_without_crashing(self):
        storage = Mock()
        storage.load_demo_broker_order_records.return_value = [_broker_record()]

        def _urlopen(request, timeout):
            raise HTTPError(request.full_url, 404, "Not Found", hdrs=None, fp=BytesIO(b""))

        with patch("research.demo_broker_order_status.settings.DEMO_BROKER", "alpaca"), patch(
            "research.demo_broker_order_status.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.demo_broker_order_status.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.demo_broker_order_status.settings.ALPACA_API_KEY", "key"
        ), patch("research.demo_broker_order_status.settings.ALPACA_SECRET_KEY", "secret"):
            result = sync_demo_broker_order_statuses(symbol="NVDA", storage=storage, urlopen_fn=_urlopen)

        self.assertEqual(1, result.records_loaded)
        self.assertEqual(0, result.status_synced)
        self.assertEqual(1, result.failed_sync)
        self.assertTrue(result.records_modified)
        storage.save_demo_broker_order_status.assert_called_once()
        saved_status = storage.save_demo_broker_order_status.call_args.args[0]
        self.assertEqual("failed_sync", saved_status.status)
        self.assertEqual("http_404", saved_status.raw_status)

    def test_timeout_records_failed_sync_without_crashing(self):
        storage = Mock()
        storage.load_demo_broker_order_records.return_value = [_broker_record()]

        def _urlopen(request, timeout):
            raise TimeoutError()

        with patch("research.demo_broker_order_status.settings.DEMO_BROKER", "alpaca"), patch(
            "research.demo_broker_order_status.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.demo_broker_order_status.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.demo_broker_order_status.settings.ALPACA_API_KEY", "key"
        ), patch("research.demo_broker_order_status.settings.ALPACA_SECRET_KEY", "secret"):
            result = sync_demo_broker_order_statuses(symbol="NVDA", storage=storage, urlopen_fn=_urlopen)

        self.assertEqual(1, result.records_loaded)
        self.assertEqual(0, result.status_synced)
        self.assertEqual(1, result.failed_sync)
        storage.save_demo_broker_order_status.assert_called_once()
        saved_status = storage.save_demo_broker_order_status.call_args.args[0]
        self.assertEqual("failed_sync", saved_status.status)
        self.assertEqual("timeout", saved_status.raw_status)

    def test_runner_prints_readonly_status_summary(self):
        result = Mock(
            records_loaded=1,
            status_synced=1,
            skipped_ineligible=0,
            failed_sync=0,
            records_modified=True,
            refused_reason=None,
            results=(
                SimpleNamespace(
                    broker_order_id="br-001",
                    order_intent_id="doi-NVDA-001",
                    symbol="NVDA",
                    action="synced",
                    status="filled",
                    filled_qty=1.0,
                    filled_avg_price=123.45,
                ),
            ),
        )

        with patch("builtins.print") as mock_print:
            run_manual_demo_broker_order_status_sync(status_sync_fn=Mock(return_value=result))

        mock_print.assert_any_call("Manual Demo Broker Order Status Sync: NVDA")
        mock_print.assert_any_call("Records Modified : yes")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Broker Calls Allowed : yes")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Order Cancellation Allowed : no")
        mock_print.assert_any_call("Live Mode Allowed : no")
        mock_print.assert_any_call("Broker Order Records Loaded : 1")
        mock_print.assert_any_call("Status Synced : 1")
        mock_print.assert_any_call("Skipped Ineligible : 0")
        mock_print.assert_any_call("Failed Sync : 0")
        mock_print.assert_any_call("- broker_order_id=br-001")
        mock_print.assert_any_call("  order_intent_id=doi-NVDA-001")
        mock_print.assert_any_call("  symbol=NVDA")
        mock_print.assert_any_call("  action=synced")
        mock_print.assert_any_call("  status=filled")
        mock_print.assert_any_call("  filled_qty=1.0")
        mock_print.assert_any_call("  filled_avg_price=123.45")
        mock_print.assert_any_call(
            "Broker order statuses were synced append-only. No orders were submitted, cancelled, or modified."
        )


if __name__ == '__main__':
    unittest.main()