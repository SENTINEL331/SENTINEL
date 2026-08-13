import unittest
from io import BytesIO
from socket import timeout as SocketTimeout
from urllib.error import HTTPError

from research.demo_broker_account import check_demo_broker_account


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


class DemoBrokerAccountTests(unittest.TestCase):
    def test_live_mode_is_refused_before_http_call(self):
        calls = []

        def _urlopen(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("HTTP call should not occur")

        result = check_demo_broker_account(
            broker="alpaca",
            mode="live",
            base_url="https://paper-api.alpaca.markets",
            api_key="key",
            secret_key="secret",
            urlopen_fn=_urlopen,
        )

        self.assertEqual("refused", result.status)
        self.assertEqual([], calls)

    def test_missing_credentials_returns_not_connected_without_http_call(self):
        calls = []

        def _urlopen(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("HTTP call should not occur")

        result = check_demo_broker_account(
            broker="alpaca",
            mode="paper",
            base_url="https://paper-api.alpaca.markets",
            api_key="",
            secret_key="",
            urlopen_fn=_urlopen,
        )

        self.assertEqual("not_connected", result.status)
        self.assertEqual([], calls)

    def test_non_paper_base_url_is_refused_before_http_call(self):
        calls = []

        def _urlopen(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("HTTP call should not occur")

        result = check_demo_broker_account(
            broker="alpaca",
            mode="paper",
            base_url="https://api.alpaca.markets",
            api_key="key",
            secret_key="secret",
            urlopen_fn=_urlopen,
        )

        self.assertEqual("refused", result.status)
        self.assertEqual([], calls)

    def test_successful_account_response_connects_and_masks_account_number(self):
        captured = {}

        def _urlopen(request, timeout):
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["timeout"] = timeout
            return _FakeResponse(
                b'{"status": "ACTIVE", "trading_blocked": false, "account_number": "PA12345678"}'
            )

        result = check_demo_broker_account(
            broker="alpaca",
            mode="paper",
            base_url="https://paper-api.alpaca.markets",
            api_key="key",
            secret_key="secret",
            urlopen_fn=_urlopen,
        )

        self.assertEqual("connected", result.status)
        self.assertTrue(result.account_reachable)
        self.assertEqual("ACTIVE", result.account_status)
        self.assertFalse(result.trading_blocked)
        self.assertEqual("****5678", result.account_number)
        self.assertEqual("https://paper-api.alpaca.markets/v2/account", captured["url"])
        self.assertEqual(10, captured["timeout"])
        self.assertEqual("key", captured["headers"]["Apca-api-key-id"])
        self.assertEqual("secret", captured["headers"]["Apca-api-secret-key"])

    def test_http_401_returns_not_connected_with_safe_rationale(self):
        def _urlopen(request, timeout):
            raise HTTPError(request.full_url, 401, "Unauthorized", hdrs=None, fp=BytesIO(b""))

        result = check_demo_broker_account(
            broker="alpaca",
            mode="paper",
            base_url="https://paper-api.alpaca.markets",
            api_key="key",
            secret_key="secret",
            urlopen_fn=_urlopen,
        )

        self.assertEqual("not_connected", result.status)
        self.assertEqual("n/a", result.account_number)
        self.assertIn("Authentication failed", result.rationale)
        self.assertNotIn("key", result.rationale)
        self.assertNotIn("secret", result.rationale)

    def test_network_timeout_returns_not_connected_with_safe_rationale(self):
        def _urlopen(request, timeout):
            raise SocketTimeout()

        result = check_demo_broker_account(
            broker="alpaca",
            mode="demo",
            base_url="https://paper-api.alpaca.markets",
            api_key="key",
            secret_key="secret",
            urlopen_fn=_urlopen,
        )

        self.assertEqual("not_connected", result.status)
        self.assertIn("Timed out", result.rationale)
        self.assertNotIn("key", result.rationale)
        self.assertNotIn("secret", result.rationale)


if __name__ == "__main__":
    unittest.main()