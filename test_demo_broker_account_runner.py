import unittest
from unittest.mock import Mock, patch

from research.demo_broker_account import DemoBrokerAccountCheck
from research.runner import run_manual_demo_broker_account


class ManualDemoBrokerAccountRunnerTests(unittest.TestCase):
    def test_runner_prints_connected_account_check(self):
        account_check = DemoBrokerAccountCheck(
            broker="alpaca",
            mode="paper",
            endpoint="paper",
            account_reachable=True,
            account_status="ACTIVE",
            trading_blocked=False,
            account_number="****5678",
            status="connected",
            rationale="Connected to the Alpaca paper account endpoint in read-only mode.",
        )

        with patch("research.runner.Storage") as mock_storage, patch(
            "builtins.print"
        ) as mock_print:
            result = run_manual_demo_broker_account(account_check_fn=Mock(return_value=account_check))

        self.assertEqual("connected", result.status)
        mock_storage.assert_not_called()
        mock_print.assert_any_call("Manual Demo Broker Account")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Broker Calls Allowed : yes")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Live Mode Allowed : no")
        mock_print.assert_any_call("- broker=alpaca")
        mock_print.assert_any_call("- mode=paper")
        mock_print.assert_any_call("- endpoint=paper")
        mock_print.assert_any_call("- account_reachable=yes")
        mock_print.assert_any_call("- account_status=ACTIVE")
        mock_print.assert_any_call("- trading_blocked=False")
        mock_print.assert_any_call("- account_number=****5678")
        mock_print.assert_any_call("status=connected")
        mock_print.assert_any_call(
            "This command only checks the paper/demo account. No orders were submitted."
        )

    def test_runner_never_prints_secrets(self):
        account_check = DemoBrokerAccountCheck(
            broker="alpaca",
            mode="paper",
            endpoint="paper",
            account_reachable=False,
            account_status="n/a",
            trading_blocked="n/a",
            account_number="n/a",
            status="not_connected",
            rationale="Authentication failed when reaching the Alpaca paper account endpoint.",
        )

        with patch("research.runner.settings.DEMO_BROKER", "alpaca"), patch(
            "research.runner.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.runner.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.runner.settings.ALPACA_API_KEY", "super-secret-key"
        ), patch("research.runner.settings.ALPACA_SECRET_KEY", "super-secret-secret"), patch(
            "builtins.print"
        ) as mock_print:
            run_manual_demo_broker_account(account_check_fn=Mock(return_value=account_check))

        printed_text = "\n".join(call.args[0] for call in mock_print.call_args_list if call.args)
        self.assertNotIn("super-secret-key", printed_text)
        self.assertNotIn("super-secret-secret", printed_text)


if __name__ == "__main__":
    unittest.main()