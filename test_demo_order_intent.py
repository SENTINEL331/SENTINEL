import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ai.storage import Storage
from research.demo_order_intent import DemoOrderIntent
from research.demo_order_intent import DemoOrderIntentStatus
from research.demo_order_intent import validate_demo_order_intent
from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import DemoTradeCandidateStatus
from research.demo_trade_queue import DemoTradeQueueItem
from research.demo_trade_queue import DemoTradeQueueStatus


def _candidate(**overrides):
    base = {
        "trade_candidate_id": "dtc-001",
        "symbol": "NVDA",
        "source_hypothesis_id": "hyp-001",
        "source_research_candidate_decision": "candidate",
        "created_at": datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc),
        "status": DemoTradeCandidateStatus.GATE_PASSED,
        "entry_logic": "Enter on breakout close above prior range.",
        "exit_logic": "Exit on trailing stop or target.",
        "invalidation_logic": "Invalidate on range breakdown.",
        "maximum_holding_period": "5D",
        "position_sizing_rule": "Risk 50 bps of equity.",
        "max_loss_per_trade": 0.01,
        "max_portfolio_exposure": 0.05,
        "demo_only": True,
        "monitoring_frequency": "15m",
        "pause_conditions": ("halted_market",),
        "source_evidence_summary": {"completed_experiments": 2, "trade_count": 160},
        "source_review_action": "keep",
        "source_review_confidence": 0.72,
        "risk_flags": ("limited_experiment_count",),
        "created_by": "human",
    }
    base.update(overrides)
    return DemoTradeCandidate(**base)


def _queue_item(**overrides):
    base = {
        "queue_item_id": "dtq-NVDA-001",
        "symbol": "NVDA",
        "demo_trade_candidate_id": "dtc-001",
        "source_hypothesis_id": "hyp-001",
        "created_at": datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
        "status": DemoTradeQueueStatus.QUEUED,
        "demo_only": True,
        "queue_reason": "candidate_passed_demo_trade_gate",
        "risk_summary": "limited_experiment_count",
        "requested_action": "prepare_demo_order",
        "created_by": "sentinel",
    }
    base.update(overrides)
    return DemoTradeQueueItem(**base)


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


class DemoOrderIntentTests(unittest.TestCase):
    def test_demo_order_intent_can_be_created(self):
        intent = _intent()

        self.assertEqual("doi-NVDA-001", intent.order_intent_id)
        self.assertEqual(DemoOrderIntentStatus.PREPARED, intent.status)
        self.assertTrue(intent.demo_only)

    def test_valid_demo_only_prepared_intent_passes_validation(self):
        storage = Storage()
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)
            storage.save_demo_trade_queue_item(_queue_item())
            storage.save_demo_trade_candidate(_candidate())
            validate_demo_order_intent(_intent(), storage=storage)

    def test_validation_fails_demo_only_false(self):
        with self.assertRaisesRegex(ValueError, "demo_only must be true"):
            validate_demo_order_intent(_intent(demo_only=False))

    def test_validation_fails_missing_queue_candidate_and_hypothesis_ids(self):
        with self.assertRaisesRegex(ValueError, "queue_item_id is required"):
            validate_demo_order_intent(_intent(queue_item_id=""))

        with self.assertRaisesRegex(ValueError, "demo_trade_candidate_id is required"):
            validate_demo_order_intent(_intent(demo_trade_candidate_id=""))

        with self.assertRaisesRegex(ValueError, "source_hypothesis_id is required"):
            validate_demo_order_intent(_intent(source_hypothesis_id=""))

    def test_validation_fails_invalid_status(self):
        with self.assertRaisesRegex(ValueError, "status must be allowed"):
            validate_demo_order_intent(_intent(status="invalid_status"))

    def test_validation_fails_invalid_side(self):
        with self.assertRaisesRegex(ValueError, "side must be buy or sell"):
            validate_demo_order_intent(_intent(side="hold"))

    def test_validation_fails_invalid_order_type(self):
        with self.assertRaisesRegex(ValueError, "order_type must be market or limit"):
            validate_demo_order_intent(_intent(order_type="stop"))

    def test_validation_fails_non_day_time_in_force(self):
        with self.assertRaisesRegex(ValueError, "time_in_force must be day"):
            validate_demo_order_intent(_intent(time_in_force="gtc"))

    def test_validation_fails_notional_and_quantity_both_present(self):
        with self.assertRaisesRegex(ValueError, "notional and quantity cannot both be set"):
            validate_demo_order_intent(_intent(quantity=10, notional=100.0))

    def test_validation_fails_notional_above_cap(self):
        with self.assertRaisesRegex(ValueError, "notional must be <= DEMO_MAX_ORDER_NOTIONAL"):
            validate_demo_order_intent(_intent(notional=250.0))

    def test_storage_appends_and_loads(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)
            storage.save_demo_order_intent(_intent(order_intent_id="doi-001"))
            storage.save_demo_order_intent(_intent(order_intent_id="doi-002", symbol="AAPL"))

            loaded = storage.load_demo_order_intents()
            self.assertEqual(2, len(loaded))
            self.assertEqual("doi-001", loaded[0].order_intent_id)

    def test_symbol_filter_works(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)
            storage.save_demo_order_intent(_intent(order_intent_id="doi-001", symbol="NVDA"))
            storage.save_demo_order_intent(_intent(order_intent_id="doi-002", symbol="AAPL"))

            loaded = storage.load_demo_order_intents(symbol="NVDA")
            self.assertEqual(1, len(loaded))
            self.assertEqual("NVDA", loaded[0].symbol)


if __name__ == "__main__":
    unittest.main()
