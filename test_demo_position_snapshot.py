import unittest
from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from research.demo_position_snapshot import sync_demo_position_snapshot
from research.runner import run_manual_demo_position_snapshot


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


def _snapshot(**overrides):
    base = {
        "position_snapshot_id": "dps-NVDA-001",
        "symbol": "NVDA",
        "broker": "alpaca",
        "broker_mode": "paper",
        "synced_at": datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        "status": "open",
        "qty": 2.0,
        "side": "long",
        "market_value": 500.0,
        "cost_basis": 450.0,
        "avg_entry_price": 225.0,
        "current_price": 250.0,
        "unrealized_pl": 50.0,
        "unrealized_plpc": 0.1111,
        "asset_id": "asset-1",
        "exchange": "NASDAQ",
        "demo_only": True,
        "created_by": "sentinel",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class DemoPositionSnapshotTests(unittest.TestCase):
    def test_live_mode_is_refused_before_http_call(self):
        calls = []

        def _urlopen(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("HTTP call should not occur")

        storage = Mock()
        storage.load_demo_position_snapshots.return_value = []

        with patch("research.demo_position_snapshot.settings.DEMO_BROKER", "alpaca"), patch(
            "research.demo_position_snapshot.settings.DEMO_BROKER_MODE", "live"
        ), patch("research.demo_position_snapshot.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.demo_position_snapshot.settings.ALPACA_API_KEY", "key"
        ), patch("research.demo_position_snapshot.settings.ALPACA_SECRET_KEY", "secret"):
            result = sync_demo_position_snapshot(symbol="NVDA", storage=storage, urlopen_fn=_urlopen)

        self.assertEqual(0, result.snapshots_created)
        self.assertEqual("Live mode is not allowed for demo position snapshot sync.", result.refused_reason)
        self.assertEqual([], calls)

    def test_non_paper_base_url_is_refused_before_http_call(self):
        calls = []

        def _urlopen(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("HTTP call should not occur")

        storage = Mock()
        storage.load_demo_position_snapshots.return_value = []

        with patch("research.demo_position_snapshot.settings.DEMO_BROKER", "alpaca"), patch(
            "research.demo_position_snapshot.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.demo_position_snapshot.settings.ALPACA_BASE_URL", "https://api.alpaca.markets"), patch(
            "research.demo_position_snapshot.settings.ALPACA_API_KEY", "key"
        ), patch("research.demo_position_snapshot.settings.ALPACA_SECRET_KEY", "secret"):
            result = sync_demo_position_snapshot(symbol="NVDA", storage=storage, urlopen_fn=_urlopen)

        self.assertEqual(0, result.snapshots_created)
        self.assertEqual("Alpaca base URL must point to a paper or demo endpoint, not a live endpoint.", result.refused_reason)
        self.assertEqual([], calls)

    def test_successful_mocked_get_stores_append_only_position_snapshot(self):
        storage = Mock()
        storage.load_demo_position_snapshots.return_value = []

        captured = {}

        def _urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["method"] = request.method
            captured["headers"] = dict(request.header_items())
            captured["timeout"] = timeout
            return _FakeResponse(
                b'{"qty":"2","side":"long","market_value":"500","cost_basis":"450","avg_entry_price":"225","current_price":"250","unrealized_pl":"50","unrealized_plpc":"0.1111","asset_id":"asset-1","exchange":"NASDAQ"}'
            )

        with patch("research.demo_position_snapshot.settings.DEMO_BROKER", "alpaca"), patch(
            "research.demo_position_snapshot.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.demo_position_snapshot.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.demo_position_snapshot.settings.ALPACA_API_KEY", "key"
        ), patch("research.demo_position_snapshot.settings.ALPACA_SECRET_KEY", "secret"):
            result = sync_demo_position_snapshot(symbol="NVDA", storage=storage, urlopen_fn=_urlopen)

        self.assertTrue(result.position_found)
        self.assertEqual(1, result.snapshots_created)
        self.assertEqual(0, result.failed_snapshot)
        self.assertTrue(result.records_modified)
        self.assertEqual("GET", captured["method"])
        self.assertEqual("https://paper-api.alpaca.markets/v2/positions/NVDA", captured["url"])
        self.assertEqual(10, captured["timeout"])
        self.assertEqual("key", captured["headers"]["Apca-api-key-id"])
        self.assertEqual("secret", captured["headers"]["Apca-api-secret-key"])
        storage.save_demo_position_snapshot.assert_called_once()
        saved_snapshot = storage.save_demo_position_snapshot.call_args.args[0]
        self.assertEqual("open", saved_snapshot.status)
        self.assertEqual(2.0, saved_snapshot.qty)
        self.assertEqual("long", saved_snapshot.side)

    def test_404_stores_no_position_snapshot_without_crashing(self):
        storage = Mock()
        storage.load_demo_position_snapshots.return_value = []

        def _urlopen(request, timeout):
            raise HTTPError(request.full_url, 404, "Not Found", hdrs=None, fp=BytesIO(b""))

        with patch("research.demo_position_snapshot.settings.DEMO_BROKER", "alpaca"), patch(
            "research.demo_position_snapshot.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.demo_position_snapshot.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.demo_position_snapshot.settings.ALPACA_API_KEY", "key"
        ), patch("research.demo_position_snapshot.settings.ALPACA_SECRET_KEY", "secret"):
            result = sync_demo_position_snapshot(symbol="NVDA", storage=storage, urlopen_fn=_urlopen)

        self.assertFalse(result.position_found)
        self.assertEqual(1, result.snapshots_created)
        self.assertEqual(0, result.failed_snapshot)
        storage.save_demo_position_snapshot.assert_called_once()
        saved_snapshot = storage.save_demo_position_snapshot.call_args.args[0]
        self.assertEqual("no_position", saved_snapshot.status)

    def test_failed_http_response_reports_failed_snapshot_without_crashing(self):
        storage = Mock()
        storage.load_demo_position_snapshots.return_value = []

        def _urlopen(request, timeout):
            raise HTTPError(request.full_url, 422, "Unprocessable Entity", hdrs=None, fp=BytesIO(b""))

        with patch("research.demo_position_snapshot.settings.DEMO_BROKER", "alpaca"), patch(
            "research.demo_position_snapshot.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.demo_position_snapshot.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.demo_position_snapshot.settings.ALPACA_API_KEY", "key"
        ), patch("research.demo_position_snapshot.settings.ALPACA_SECRET_KEY", "secret"):
            result = sync_demo_position_snapshot(symbol="NVDA", storage=storage, urlopen_fn=_urlopen)

        self.assertFalse(result.position_found)
        self.assertEqual(0, result.snapshots_created)
        self.assertEqual(1, result.failed_snapshot)
        storage.save_demo_position_snapshot.assert_called_once()
        saved_snapshot = storage.save_demo_position_snapshot.call_args.args[0]
        self.assertEqual("failed", saved_snapshot.status)

    def test_timeout_reports_failed_snapshot_without_crashing(self):
        storage = Mock()
        storage.load_demo_position_snapshots.return_value = []

        def _urlopen(request, timeout):
            raise TimeoutError()

        with patch("research.demo_position_snapshot.settings.DEMO_BROKER", "alpaca"), patch(
            "research.demo_position_snapshot.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.demo_position_snapshot.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.demo_position_snapshot.settings.ALPACA_API_KEY", "key"
        ), patch("research.demo_position_snapshot.settings.ALPACA_SECRET_KEY", "secret"):
            result = sync_demo_position_snapshot(symbol="NVDA", storage=storage, urlopen_fn=_urlopen)

        self.assertFalse(result.position_found)
        self.assertEqual(1, result.failed_snapshot)
        storage.save_demo_position_snapshot.assert_called_once()
        saved_snapshot = storage.save_demo_position_snapshot.call_args.args[0]
        self.assertEqual("failed", saved_snapshot.status)

    def test_runner_prints_readonly_position_snapshot_summary(self):
        result = Mock(
            position_found=True,
            snapshots_loaded=2,
            snapshots_created=1,
            failed_snapshot=0,
            records_modified=True,
            refused_reason=None,
            snapshot=SimpleNamespace(
                position_snapshot_id="dps-NVDA-001",
                symbol="NVDA",
                status="open",
                qty=2.0,
                side="long",
                market_value=500.0,
                cost_basis=450.0,
                avg_entry_price=225.0,
                current_price=250.0,
                unrealized_pl=50.0,
                unrealized_plpc=0.1111,
                demo_only=True,
            ),
        )

        with patch("builtins.print") as mock_print:
            run_manual_demo_position_snapshot(snapshot_sync_fn=Mock(return_value=result))

        mock_print.assert_any_call("Manual Demo Position Snapshot: NVDA")
        mock_print.assert_any_call("Records Modified : yes")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Broker Calls Allowed : yes")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Order Cancellation Allowed : no")
        mock_print.assert_any_call("Position Close Allowed : no")
        mock_print.assert_any_call("Live Mode Allowed : no")
        mock_print.assert_any_call("Position Found : yes")
        mock_print.assert_any_call("Snapshots Loaded : 2")
        mock_print.assert_any_call("Snapshots Created : 1")
        mock_print.assert_any_call("Failed Snapshot : 0")
        mock_print.assert_any_call("- position_snapshot_id=dps-NVDA-001")
        mock_print.assert_any_call("  symbol=NVDA")
        mock_print.assert_any_call("  status=open")
        mock_print.assert_any_call("  qty=2.0")
        mock_print.assert_any_call("  side=long")
        mock_print.assert_any_call("  market_value=500.0")
        mock_print.assert_any_call("  cost_basis=450.0")
        mock_print.assert_any_call("  avg_entry_price=225.0")
        mock_print.assert_any_call("  current_price=250.0")
        mock_print.assert_any_call("  unrealized_pl=50.0")
        mock_print.assert_any_call("  unrealized_plpc=0.1111")
        mock_print.assert_any_call("  demo_only=True")
        mock_print.assert_any_call(
            "Position snapshot was appended locally. No orders were submitted, cancelled, replaced, or closed."
        )


if __name__ == "__main__":
    unittest.main()