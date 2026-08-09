import unittest
from datetime import datetime, timezone

from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import DemoTradeCandidateStatus
from research.demo_trade_candidate import validate_demo_trade_candidate


def _candidate(**overrides):
    base = {
        "trade_candidate_id": "dtc-001",
        "symbol": "NVDA",
        "source_hypothesis_id": "hyp-001",
        "source_research_candidate_decision": "candidate",
        "created_at": datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc),
        "status": DemoTradeCandidateStatus.PROPOSED,
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


class DemoTradeCandidateTests(unittest.TestCase):
    def test_demo_trade_candidate_can_be_created(self):
        candidate = _candidate()

        self.assertEqual("dtc-001", candidate.trade_candidate_id)
        self.assertEqual(DemoTradeCandidateStatus.PROPOSED, candidate.status)
        self.assertTrue(candidate.demo_only)

    def test_valid_candidate_passes_validation(self):
        candidate = _candidate()
        validate_demo_trade_candidate(candidate)

    def test_demo_only_false_fails_validation(self):
        candidate = _candidate(demo_only=False)

        with self.assertRaisesRegex(ValueError, "demo_only must be true"):
            validate_demo_trade_candidate(candidate)

    def test_missing_entry_exit_and_invalidation_fail_validation(self):
        with self.assertRaisesRegex(ValueError, "entry_logic is required"):
            validate_demo_trade_candidate(_candidate(entry_logic=""))

        with self.assertRaisesRegex(ValueError, "exit_logic is required"):
            validate_demo_trade_candidate(_candidate(exit_logic=""))

        with self.assertRaisesRegex(ValueError, "invalidation_logic is required"):
            validate_demo_trade_candidate(_candidate(invalidation_logic=""))

    def test_excessive_max_loss_per_trade_fails_validation(self):
        candidate = _candidate(max_loss_per_trade=0.03)

        with self.assertRaisesRegex(ValueError, "max_loss_per_trade must not exceed 0.02"):
            validate_demo_trade_candidate(candidate)

    def test_excessive_max_portfolio_exposure_fails_validation(self):
        candidate = _candidate(max_portfolio_exposure=0.11)

        with self.assertRaisesRegex(ValueError, "max_portfolio_exposure must not exceed 0.10"):
            validate_demo_trade_candidate(candidate)

    def test_invalid_status_fails_validation(self):
        candidate = _candidate(status="invalid_status")

        with self.assertRaisesRegex(ValueError, "status must be allowed"):
            validate_demo_trade_candidate(candidate)


if __name__ == "__main__":
    unittest.main()