import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from research.demo_trade_queue import DemoTradeQueueItem
from research.demo_trade_queue import DemoTradeQueueStatus
from research.demo_trade_queue_add import DemoTradeQueueAddItem
from research.demo_trade_queue_add import DemoTradeQueueAddResult
from research.runner import (
    DEFAULT_SYMBOL,
    run_manual_demo_trade_queue,
    run_manual_demo_trade_queue_add,
)


def _queue_item(queue_item_id: str, symbol: str = "NVDA"):
    return DemoTradeQueueItem(
        queue_item_id=queue_item_id,
        symbol=symbol,
        demo_trade_candidate_id=f"dtc-{queue_item_id}",
        source_hypothesis_id=f"hyp-{queue_item_id}",
        created_at=datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        status=DemoTradeQueueStatus.QUEUED,
        demo_only=True,
        queue_reason="candidate_passed_demo_trade_gate",
        risk_summary="limited_experiment_count",
        requested_action="prepare_demo_order",
        created_by="sentinel",
    )


class ManualDemoTradeQueueRunnerTests(unittest.TestCase):
    def test_queue_runner_is_read_only_and_prints_items(self):
        storage = Mock()
        storage.load_demo_trade_queue_items.return_value = [_queue_item("dtq-001")]

        with patch("builtins.print") as mock_print:
            items = run_manual_demo_trade_queue(symbol="NVDA", storage=storage)

        self.assertEqual(1, len(items))
        mock_print.assert_any_call("Manual Demo Trade Queue: NVDA")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Queue Items Loaded : 1")
        mock_print.assert_any_call("Demo Trade Queue")
        mock_print.assert_any_call("- queue_item_id=dtq-001")
        mock_print.assert_any_call("  demo_trade_candidate_id=dtc-dtq-001")
        mock_print.assert_any_call("  source_hypothesis_id=hyp-dtq-001")
        mock_print.assert_any_call("  status=queued")
        mock_print.assert_any_call("  requested_action=prepare_demo_order")
        mock_print.assert_any_call("  demo_only=True")

        storage.load_demo_trade_queue_items.assert_called_once_with(symbol="NVDA")
        storage.save_demo_trade_queue_item.assert_not_called()

    def test_queue_runner_prints_empty_message_when_none_exist(self):
        storage = Mock()
        storage.load_demo_trade_queue_items.return_value = []

        with patch("builtins.print") as mock_print:
            items = run_manual_demo_trade_queue(symbol="NVDA", storage=storage)

        self.assertEqual([], items)
        mock_print.assert_any_call("No demo trade queue items found.")

    def test_queue_runner_uses_default_symbol(self):
        storage = Mock()
        storage.load_demo_trade_queue_items.return_value = []

        with patch("builtins.print"):
            run_manual_demo_trade_queue(storage=storage)

        storage.load_demo_trade_queue_items.assert_called_once_with(symbol=DEFAULT_SYMBOL)

    def test_queue_add_runner_defaults_to_dry_run(self):
        storage = Mock()
        service = Mock()
        service.apply_for_symbol.return_value = DemoTradeQueueAddResult(
            apply_mode=False,
            gate_passed_candidates_loaded=2,
            would_queue=1,
            queued=0,
            skipped_existing=0,
            skipped_ineligible=1,
            results=(
                DemoTradeQueueAddItem(
                    demo_trade_candidate_id="dtc-001",
                    source_hypothesis_id="hyp-001",
                    action="would_queue",
                    queue_item_id="dtq-NVDA-001",
                ),
            ),
        )

        with patch("builtins.print") as mock_print:
            result = run_manual_demo_trade_queue_add(
                symbol="NVDA",
                storage=storage,
                demo_trade_queue_add_service=service,
            )

        self.assertFalse(result.apply_mode)
        service.apply_for_symbol.assert_called_once_with(symbol="NVDA", apply_mode=False)
        mock_print.assert_any_call("Manual Demo Trade Queue Add: NVDA")
        mock_print.assert_any_call("Mode : dry-run")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Gate Passed Candidates Loaded : 2")
        mock_print.assert_any_call("Would Queue : 1")
        mock_print.assert_any_call("Queued : 0")
        mock_print.assert_any_call("Skipped Existing : 0")
        mock_print.assert_any_call("Skipped Ineligible : 1")
        mock_print.assert_any_call("Dry-run reminder:")
        mock_print.assert_any_call("Dry-run only. No queue records were created.")

    def test_queue_add_runner_prints_apply_mode(self):
        storage = Mock()
        service = Mock()
        service.apply_for_symbol.return_value = DemoTradeQueueAddResult(
            apply_mode=True,
            gate_passed_candidates_loaded=1,
            would_queue=1,
            queued=1,
            skipped_existing=0,
            skipped_ineligible=0,
            results=(
                DemoTradeQueueAddItem(
                    demo_trade_candidate_id="dtc-001",
                    source_hypothesis_id="hyp-001",
                    action="queued",
                    queue_item_id="dtq-NVDA-001",
                ),
            ),
        )

        with patch("builtins.print") as mock_print:
            result = run_manual_demo_trade_queue_add(
                symbol="NVDA",
                apply_changes=True,
                storage=storage,
                demo_trade_queue_add_service=service,
            )

        self.assertTrue(result.apply_mode)
        service.apply_for_symbol.assert_called_once_with(symbol="NVDA", apply_mode=True)
        mock_print.assert_any_call("Mode : apply")
        mock_print.assert_any_call("Records Modified : yes")
        mock_print.assert_any_call("Apply reminder:")
        mock_print.assert_any_call("Queue records were created append-only. No orders were submitted.")

    def test_queue_add_runner_prints_no_records_modified_when_apply_skips_all_existing(self):
        storage = Mock()
        service = Mock()
        service.apply_for_symbol.return_value = DemoTradeQueueAddResult(
            apply_mode=True,
            gate_passed_candidates_loaded=4,
            would_queue=0,
            queued=0,
            skipped_existing=4,
            skipped_ineligible=0,
            results=(
                DemoTradeQueueAddItem(
                    demo_trade_candidate_id="dtc-001",
                    source_hypothesis_id="hyp-001",
                    action="skipped_existing",
                    queue_item_id="dtq-NVDA-001",
                ),
            ),
        )

        with patch("builtins.print") as mock_print:
            result = run_manual_demo_trade_queue_add(
                symbol="NVDA",
                apply_changes=True,
                storage=storage,
                demo_trade_queue_add_service=service,
            )

        self.assertTrue(result.apply_mode)
        mock_print.assert_any_call("Mode : apply")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("  queue_item_id=dtq-NVDA-001")
        mock_print.assert_any_call("Apply reminder:")
        mock_print.assert_any_call(
            "No new queue records were created. Existing queue items were left unchanged. No orders were submitted."
        )


if __name__ == "__main__":
    unittest.main()