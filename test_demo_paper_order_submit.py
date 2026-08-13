import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from research.demo_order_intent import DemoOrderIntent
from research.demo_order_intent import DemoOrderIntentStatus
from research.demo_paper_order_submit import DemoPaperOrderSubmitService
from research.runner import main, run_manual_demo_paper_order_submit


def _intent(**overrides):
    base = {
        "order_intent_id": "doi-NVDA-001",
        "symbol": "NVDA",
        "queue_item_id": "dtq-NVDA-001",
        "demo_trade_candidate_id": "dtc-001",
        "source_hypothesis_id": "hyp-001",
        "created_at": datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        "status": DemoOrderIntentStatus.PREPARED,
        "demo_only": True,
        "side": "buy",
        "order_type": "market",
        "time_in_force": "day",
        "notional": 100.0,
        "quantity": None,
        "limit_price": None,
        "stop_price": None,
        "max_loss_per_trade": 0.01,
        "max_portfolio_exposure": 0.05,
        "intent_reason": "queued_demo_trade_candidate",
        "created_by": "sentinel",
    }
    base.update(overrides)
    return DemoOrderIntent(**base)


class DemoPaperOrderSubmitTests(unittest.TestCase):
    def test_cli_help_includes_demo_paper_order_submit(self):
        with patch("builtins.print"):
            with self.assertRaises(SystemExit):
                main(["--help"])

    def test_dry_run_is_default_and_does_not_call_http(self):
        storage = Mock()
        storage.load_demo_order_intents.return_value = [_intent()]
        storage.load_demo_trade_queue_items.return_value = []
        storage.load_demo_broker_order_records.return_value = []
        storage.load_demo_trade_candidates.return_value = []

        with patch("research.runner.settings.DEMO_BROKER", "alpaca"), patch(
            "research.runner.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.runner.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.runner.settings.ALPACA_API_KEY", "key"
        ), patch("research.runner.settings.ALPACA_SECRET_KEY", "secret"), patch(
            "research.runner.check_demo_broker_account"
        ) as mock_account, patch("builtins.print"):
            mock_account.return_value = Mock(account_reachable=True)
            result = DemoPaperOrderSubmitService(storage=storage).apply_for_symbol(
                symbol="NVDA",
                apply_mode=False,
                confirm_paper_submit=False,
            )

        self.assertEqual(1, result.would_submit)
        self.assertEqual(0, result.submitted)
        mock_account.assert_not_called()

    def test_apply_requires_confirm_before_http_call(self):
        storage = Mock()
        storage.load_demo_order_intents.return_value = [_intent()]
        storage.load_demo_trade_queue_items.return_value = []
        storage.load_demo_broker_order_records.return_value = []
        storage.load_demo_trade_candidates.return_value = []

        with patch("research.runner.settings.DEMO_BROKER", "alpaca"), patch(
            "research.runner.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.runner.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.runner.settings.ALPACA_API_KEY", "key"
        ), patch("research.runner.settings.ALPACA_SECRET_KEY", "secret"), patch(
            "builtins.print"
        ):
            result = DemoPaperOrderSubmitService(storage=storage).apply_for_symbol(
                symbol="NVDA",
                apply_mode=True,
                confirm_paper_submit=False,
            )

        self.assertEqual(0, result.submitted)
        self.assertEqual(1, result.refused_without_confirmation)
        self.assertEqual(1, result.would_submit)
        storage.save_demo_broker_order_record.assert_not_called()

    def test_dry_run_header_reports_no_no(self):
        storage = Mock()
        storage.load_demo_order_intents.return_value = []
        storage.load_demo_trade_queue_items.return_value = []
        storage.load_demo_broker_order_records.return_value = []

        with patch("builtins.print") as mock_print:
            run_manual_demo_paper_order_submit(
                symbol="NVDA",
                apply_changes=False,
                confirm_paper_submit=False,
                storage=storage,
            )

        mock_print.assert_any_call("Broker Calls Allowed : no")
        mock_print.assert_any_call("Order Placement Allowed : no")

    def test_apply_without_confirm_header_reports_no_no(self):
        storage = Mock()
        storage.load_demo_order_intents.return_value = [_intent()]
        storage.load_demo_trade_queue_items.return_value = []
        storage.load_demo_broker_order_records.return_value = []

        with patch("research.runner.settings.DEMO_BROKER", "alpaca"), patch(
            "research.runner.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.runner.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.runner.settings.ALPACA_API_KEY", "key"
        ), patch("research.runner.settings.ALPACA_SECRET_KEY", "secret"), patch(
            "builtins.print"
        ) as mock_print:
            run_manual_demo_paper_order_submit(
                symbol="NVDA",
                apply_changes=True,
                confirm_paper_submit=False,
                storage=storage,
            )

        mock_print.assert_any_call("Broker Calls Allowed : no")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Refused Without Confirmation : 1")

    def test_apply_with_confirm_header_reports_yes_yes(self):
        storage = Mock()
        storage.load_demo_order_intents.return_value = [_intent()]
        storage.load_demo_trade_queue_items.return_value = []
        storage.load_demo_broker_order_records.return_value = []

        with patch("research.runner.settings.DEMO_BROKER", "alpaca"), patch(
            "research.runner.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.runner.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.runner.settings.ALPACA_API_KEY", "key"
        ), patch("research.runner.settings.ALPACA_SECRET_KEY", "secret"), patch(
            "research.demo_paper_order_submit.check_demo_broker_account"
        ) as mock_account, patch(
            "research.demo_paper_order_submit.urlopen"
        ) as mock_urlopen, patch("builtins.print") as mock_print:
            mock_account.return_value = Mock(account_reachable=True)
            mock_response = Mock()
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_response.read.return_value = b'{"id":"br-1","status":"accepted"}'
            mock_urlopen.return_value = mock_response

            run_manual_demo_paper_order_submit(
                symbol="NVDA",
                apply_changes=True,
                confirm_paper_submit=True,
                storage=storage,
            )

        mock_print.assert_any_call("Broker Calls Allowed : yes")
        mock_print.assert_any_call("Order Placement Allowed : yes")
        self.assertTrue(storage.save_demo_broker_order_record.called)

    def test_apply_without_confirm_existing_only_shows_existing_record_message(self):
        storage = Mock()
        storage.load_demo_order_intents.return_value = [_intent()]
        storage.load_demo_trade_queue_items.return_value = []
        storage.load_demo_broker_order_records.return_value = [
            type(
                "record",
                (),
                {
                    "order_intent_id": "doi-NVDA-001",
                    "broker_order_id": "br-existing",
                    "status": "submitted",
                    "symbol": "NVDA",
                },
            )()
        ]

        with patch("research.runner.settings.DEMO_BROKER", "alpaca"), patch(
            "research.runner.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.runner.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.runner.settings.ALPACA_API_KEY", "key"
        ), patch("research.runner.settings.ALPACA_SECRET_KEY", "secret"), patch(
            "builtins.print"
        ) as mock_print:
            run_manual_demo_paper_order_submit(
                symbol="NVDA",
                apply_changes=True,
                confirm_paper_submit=False,
                storage=storage,
            )

        self.assertEqual(0, storage.save_demo_broker_order_record.call_count)
        mock_print.assert_any_call("Apply reminder:")
        printed_text = "\n".join(call.args[0] for call in mock_print.call_args_list if call.args)
        self.assertIn("No broker order records were created. Existing records were left unchanged. No live orders were submitted.", printed_text)

    def test_duplicate_apply_with_confirm_skips_existing_records(self):
        storage = Mock()
        storage.load_demo_order_intents.return_value = [_intent()]
        storage.load_demo_trade_queue_items.return_value = []
        storage.load_demo_broker_order_records.return_value = [
            type(
                "record",
                (),
                {
                    "order_intent_id": "doi-NVDA-001",
                    "broker_order_id": "br-existing",
                    "status": "submitted",
                    "symbol": "NVDA",
                },
            )()
        ]

        with patch("research.runner.settings.DEMO_BROKER", "alpaca"), patch(
            "research.runner.settings.DEMO_BROKER_MODE", "paper"
        ), patch("research.runner.settings.ALPACA_BASE_URL", "https://paper-api.alpaca.markets"), patch(
            "research.runner.settings.ALPACA_API_KEY", "key"
        ), patch("research.runner.settings.ALPACA_SECRET_KEY", "secret"), patch(
            "research.demo_paper_order_submit.urlopen"
        ) as mock_urlopen, patch("builtins.print"):
            run_manual_demo_paper_order_submit(
                symbol="NVDA",
                apply_changes=True,
                confirm_paper_submit=True,
                storage=storage,
            )

        mock_urlopen.assert_not_called()
        storage.save_demo_broker_order_record.assert_not_called()


if __name__ == "__main__":
    unittest.main()
