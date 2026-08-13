import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from research.runner import run_manual_demo_broker_readiness


class ManualDemoBrokerReadinessRunnerTests(unittest.TestCase):
    def test_readiness_uses_same_demo_alpaca_settings_source_as_account(self):
        storage = Mock()
        storage.load_demo_trade_queue_items.return_value = [
            SimpleNamespace(status="queued", demo_only=True),
        ]

        with patch("research.runner.settings.DEMO_BROKER", "alpaca"), patch(
            "research.runner.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.runner.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.runner.settings.ALPACA_API_KEY", "demo-key"
        ), patch("research.runner.settings.ALPACA_SECRET_KEY", "demo-secret"), patch(
            "research.runner.settings.BROKER_MODE", "live"
        ), patch("research.runner.settings.BROKER_BASE_URL", ""), patch(
            "research.runner.settings.BROKER_API_KEY", ""
        ), patch("research.runner.settings.BROKER_API_SECRET", ""), patch(
            "builtins.print"
        ) as mock_print:
            readiness = run_manual_demo_broker_readiness(storage=storage)

        self.assertTrue(readiness.ready)
        mock_print.assert_any_call("- broker=alpaca")
        mock_print.assert_any_call("- broker_mode=paper")
        mock_print.assert_any_call("  base_url_present=True")
        mock_print.assert_any_call("  api_key_present=True")
        mock_print.assert_any_call("  api_secret_present=True")
        mock_print.assert_any_call("Ready : yes")

    def test_runner_reports_missing_keys_without_leaking_secrets(self):
        storage = Mock()
        storage.load_demo_trade_queue_items.return_value = []

        with patch("research.runner.settings.DEMO_BROKER", "alpaca"), patch(
            "research.runner.settings.DEMO_BROKER_MODE", "demo"
        ), patch("research.runner.settings.ALPACA_BASE_URL", ""), patch(
            "research.runner.settings.ALPACA_API_KEY", "super-secret-key"
        ), patch("research.runner.settings.ALPACA_SECRET_KEY", "super-secret-secret"
        ), patch("builtins.print") as mock_print:
            readiness = run_manual_demo_broker_readiness(storage=storage)

        self.assertFalse(readiness.ready)
        mock_print.assert_any_call("Manual Demo Broker Readiness")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Broker Calls Allowed : no")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Live Mode Allowed : no")
        mock_print.assert_any_call("Queue Items Loaded : 0")
        mock_print.assert_any_call("Ready : no")
        mock_print.assert_any_call("- broker=alpaca")
        mock_print.assert_any_call("  base_url_present=False")
        mock_print.assert_any_call("  api_key_present=True")
        mock_print.assert_any_call("  api_secret_present=True")
        mock_print.assert_any_call("- broker_base_url_missing")
        printed_text = "\n".join(call.args[0] for call in mock_print.call_args_list if call.args)
        self.assertNotIn("super-secret-key", printed_text)
        self.assertNotIn("super-secret-secret", printed_text)

        storage.save_demo_trade_queue_item.assert_not_called()

    def test_runner_rejects_live_mode(self):
        storage = Mock()
        storage.load_demo_trade_queue_items.return_value = []

        with patch("research.runner.settings.DEMO_BROKER", "alpaca"), patch(
            "research.runner.settings.DEMO_BROKER_MODE", "live"
        ), patch("research.runner.settings.ALPACA_BASE_URL", "https://paper.example.local"), patch(
            "research.runner.settings.ALPACA_API_KEY", "key"
        ), patch("research.runner.settings.ALPACA_SECRET_KEY", "secret"
        ), patch("builtins.print") as mock_print:
            readiness = run_manual_demo_broker_readiness(storage=storage)

        self.assertFalse(readiness.ready)
        mock_print.assert_any_call("Ready : no")
        mock_print.assert_any_call("- live_mode_not_allowed")

    def test_runner_reports_paper_mode_ready(self):
        storage = Mock()
        storage.load_demo_trade_queue_items.return_value = [
            SimpleNamespace(status="queued", demo_only=True),
            SimpleNamespace(status="completed", demo_only=True),
        ]

        with patch("research.runner.settings.DEMO_BROKER", "alpaca"), patch(
            "research.runner.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.runner.settings.ALPACA_BASE_URL", "https://paper.example.local"), patch(
            "research.runner.settings.ALPACA_API_KEY", "key"
        ), patch("research.runner.settings.ALPACA_SECRET_KEY", "secret"
        ), patch("builtins.print") as mock_print:
            readiness = run_manual_demo_broker_readiness(storage=storage)

        self.assertTrue(readiness.ready)
        mock_print.assert_any_call("Queue Items Loaded : 2")
        mock_print.assert_any_call("Active Queue Items : 1")
        mock_print.assert_any_call("Ready : yes")
        mock_print.assert_any_call("None.")


if __name__ == "__main__":
    unittest.main()