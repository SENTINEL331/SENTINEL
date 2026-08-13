import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import DemoTradeCandidateStatus
from research.demo_trade_queue import DemoTradeQueueItem
from research.demo_trade_queue import DemoTradeQueueStatus
from research.demo_trade_queue_add import DemoTradeQueueAddService


def _candidate(**overrides):
    base = {
        "trade_candidate_id": "dtc-001",
        "symbol": "NVDA",
        "source_hypothesis_id": "hyp-001",
        "source_research_candidate_decision": "candidate",
        "created_at": datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
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
        "source_evidence_summary": {"completed_experiments": 2},
        "source_review_action": "keep",
        "source_review_confidence": 0.72,
        "risk_flags": ("limited_experiment_count",),
        "gate_checked_at": datetime(2026, 8, 13, 12, 30, tzinfo=timezone.utc),
        "gate_decision": "gate_pass",
        "failed_checks": (),
        "gate_rationale": "Candidate passes deterministic demo gate checks.",
        "created_by": "sentinel",
    }
    base.update(overrides)
    return DemoTradeCandidate(**base)


def _queue_item(**overrides):
    base = {
        "queue_item_id": "dtq-NVDA-001",
        "symbol": "NVDA",
        "demo_trade_candidate_id": "dtc-001",
        "source_hypothesis_id": "hyp-001",
        "created_at": datetime(2026, 8, 13, 13, 0, tzinfo=timezone.utc),
        "status": DemoTradeQueueStatus.QUEUED,
        "demo_only": True,
        "queue_reason": "candidate_passed_demo_trade_gate",
        "risk_summary": "limited_experiment_count",
        "requested_action": "prepare_demo_order",
        "created_by": "sentinel",
    }
    base.update(overrides)
    return DemoTradeQueueItem(**base)


class DemoTradeQueueAddServiceTests(unittest.TestCase):
    def _build_storage(self, *, candidates, queue_items=None):
        storage = Mock(
            spec_set=[
                "load_demo_trade_candidates",
                "load_demo_trade_queue_items",
                "save_demo_trade_queue_item",
            ]
        )
        storage.load_demo_trade_candidates.return_value = candidates
        storage.load_demo_trade_queue_items.return_value = queue_items or []
        return storage

    def test_dry_run_writes_nothing(self):
        storage = self._build_storage(candidates=[_candidate()])
        service = DemoTradeQueueAddService(storage=storage)

        result = service.apply_for_symbol("NVDA", apply_mode=False)

        self.assertFalse(result.apply_mode)
        self.assertEqual(1, result.gate_passed_candidates_loaded)
        self.assertEqual(1, result.would_queue)
        self.assertEqual(0, result.queued)
        storage.save_demo_trade_queue_item.assert_not_called()

    def test_apply_queues_latest_gate_passed_candidates(self):
        older_gate_failed = _candidate(
            trade_candidate_id="dtc-001-old",
            source_trade_candidate_id="dtc-001",
            status=DemoTradeCandidateStatus.GATE_FAILED,
            created_at=datetime(2026, 8, 13, 11, 0, tzinfo=timezone.utc),
            gate_checked_at=datetime(2026, 8, 13, 11, 0, tzinfo=timezone.utc),
            gate_decision="gate_fail",
            failed_checks=("max_loss_per_trade_above_limit",),
            gate_rationale="Candidate fails deterministic demo gate checks.",
        )
        latest_gate_passed = _candidate(
            trade_candidate_id="dtc-001-new",
            source_trade_candidate_id="dtc-001",
            created_at=datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
            gate_checked_at=datetime(2026, 8, 13, 12, 30, tzinfo=timezone.utc),
        )
        storage = self._build_storage(candidates=[older_gate_failed, latest_gate_passed])
        service = DemoTradeQueueAddService(storage=storage)

        result = service.apply_for_symbol("NVDA", apply_mode=True)

        self.assertTrue(result.apply_mode)
        self.assertEqual(1, result.would_queue)
        self.assertEqual(1, result.queued)
        saved_item = storage.save_demo_trade_queue_item.call_args.args[0]
        self.assertEqual("dtc-001-new", saved_item.demo_trade_candidate_id)
        self.assertEqual(DemoTradeQueueStatus.QUEUED, saved_item.status)

    def test_proposed_candidates_are_not_queued(self):
        storage = self._build_storage(
            candidates=[_candidate(status=DemoTradeCandidateStatus.PROPOSED)]
        )
        service = DemoTradeQueueAddService(storage=storage)

        result = service.apply_for_symbol("NVDA", apply_mode=True)

        self.assertEqual(0, result.gate_passed_candidates_loaded)
        self.assertEqual(0, result.queued)
        storage.save_demo_trade_queue_item.assert_not_called()

    def test_gate_failed_candidates_are_not_queued(self):
        storage = self._build_storage(
            candidates=[_candidate(status=DemoTradeCandidateStatus.GATE_FAILED)]
        )
        service = DemoTradeQueueAddService(storage=storage)

        result = service.apply_for_symbol("NVDA", apply_mode=True)

        self.assertEqual(0, result.gate_passed_candidates_loaded)
        self.assertEqual(0, result.queued)
        storage.save_demo_trade_queue_item.assert_not_called()

    def test_invalid_candidate_is_skipped(self):
        storage = self._build_storage(candidates=[_candidate(entry_logic="")])
        service = DemoTradeQueueAddService(storage=storage)

        result = service.apply_for_symbol("NVDA", apply_mode=True)

        self.assertEqual(1, result.gate_passed_candidates_loaded)
        self.assertEqual(1, result.skipped_ineligible)
        self.assertEqual("skipped_ineligible", result.results[0].action)
        storage.save_demo_trade_queue_item.assert_not_called()

    def test_demo_only_false_is_skipped(self):
        storage = self._build_storage(candidates=[_candidate(demo_only=False)])
        service = DemoTradeQueueAddService(storage=storage)

        result = service.apply_for_symbol("NVDA", apply_mode=True)

        self.assertEqual(1, result.gate_passed_candidates_loaded)
        self.assertEqual(1, result.skipped_ineligible)
        self.assertEqual("skipped_ineligible", result.results[0].action)
        storage.save_demo_trade_queue_item.assert_not_called()

    def test_duplicate_queue_add_skips_existing_queued_submitted_or_filled(self):
        for status in (
            DemoTradeQueueStatus.QUEUED,
            DemoTradeQueueStatus.SUBMITTED,
            DemoTradeQueueStatus.FILLED,
        ):
            storage = self._build_storage(
                candidates=[_candidate()],
                queue_items=[_queue_item(status=status)],
            )
            service = DemoTradeQueueAddService(storage=storage)

            result = service.apply_for_symbol("NVDA", apply_mode=True)

            self.assertEqual(1, result.skipped_existing)
            self.assertEqual("skipped_existing", result.results[0].action)
            self.assertEqual("dtq-NVDA-001", result.results[0].queue_item_id)
            storage.save_demo_trade_queue_item.assert_not_called()

    def test_second_apply_skips_existing_items_and_writes_nothing(self):
        storage = self._build_storage(
            candidates=[
                _candidate(trade_candidate_id="dtc-001", source_hypothesis_id="hyp-001"),
                _candidate(trade_candidate_id="dtc-002", source_hypothesis_id="hyp-002"),
                _candidate(trade_candidate_id="dtc-003", source_hypothesis_id="hyp-003"),
                _candidate(trade_candidate_id="dtc-004", source_hypothesis_id="hyp-004"),
            ],
            queue_items=[
                _queue_item(queue_item_id="dtq-NVDA-001", demo_trade_candidate_id="dtc-001", source_hypothesis_id="hyp-001"),
                _queue_item(queue_item_id="dtq-NVDA-002", demo_trade_candidate_id="dtc-002", source_hypothesis_id="hyp-002"),
                _queue_item(queue_item_id="dtq-NVDA-003", demo_trade_candidate_id="dtc-003", source_hypothesis_id="hyp-003"),
                _queue_item(queue_item_id="dtq-NVDA-004", demo_trade_candidate_id="dtc-004", source_hypothesis_id="hyp-004"),
            ],
        )
        service = DemoTradeQueueAddService(storage=storage)

        result = service.apply_for_symbol("NVDA", apply_mode=True)

        self.assertEqual(0, result.queued)
        self.assertEqual(4, result.skipped_existing)
        self.assertEqual(
            ("dtq-NVDA-001", "dtq-NVDA-002", "dtq-NVDA-003", "dtq-NVDA-004"),
            tuple(item.queue_item_id for item in result.results),
        )
        storage.save_demo_trade_queue_item.assert_not_called()


if __name__ == "__main__":
    unittest.main()