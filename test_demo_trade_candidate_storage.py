import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from ai.storage import Storage
from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import DemoTradeCandidateStatus


def _candidate(*, trade_candidate_id: str, symbol: str):
    return DemoTradeCandidate(
        trade_candidate_id=trade_candidate_id,
        symbol=symbol,
        source_hypothesis_id=f"hyp-{trade_candidate_id}",
        source_research_candidate_decision="candidate",
        created_at=datetime(2026, 8, 9, 12, 0, tzinfo=timezone.utc),
        status=DemoTradeCandidateStatus.PROPOSED,
        entry_logic="Enter on breakout close above prior range.",
        exit_logic="Exit on trailing stop or target.",
        invalidation_logic="Invalidate on range breakdown.",
        maximum_holding_period="5D",
        position_sizing_rule="Risk 50 bps of equity.",
        max_loss_per_trade=0.01,
        max_portfolio_exposure=0.05,
        demo_only=True,
        monitoring_frequency="15m",
        pause_conditions=("halted_market",),
        source_evidence_summary={"completed_experiments": 2},
        source_review_action="keep",
        source_review_confidence=0.72,
        risk_flags=("limited_experiment_count",),
        created_by="human",
    )


class DemoTradeCandidateStorageTests(unittest.TestCase):
    def test_storage_appends_and_loads_candidates(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)
            first = _candidate(trade_candidate_id="dtc-001", symbol="NVDA")
            second = _candidate(trade_candidate_id="dtc-002", symbol="AAPL")

            storage.save_demo_trade_candidate(first)
            storage.save_demo_trade_candidate(second)

            loaded = storage.load_demo_trade_candidates()

            self.assertEqual(2, len(loaded))
            self.assertEqual("dtc-001", loaded[0].trade_candidate_id)
            self.assertEqual("dtc-002", loaded[1].trade_candidate_id)

    def test_symbol_filter_works(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)
            storage.save_demo_trade_candidate(_candidate(trade_candidate_id="dtc-001", symbol="NVDA"))
            storage.save_demo_trade_candidate(_candidate(trade_candidate_id="dtc-002", symbol="AAPL"))

            loaded = storage.load_demo_trade_candidates(symbol="NVDA")

            self.assertEqual(1, len(loaded))
            self.assertEqual("NVDA", loaded[0].symbol)

    def test_old_missing_optional_fields_load_safely(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)
            path = Path(tmp_dir) / "demo_trade_candidates.jsonl"
            path.write_text(
                "{\"trade_candidate_id\": \"dtc-legacy-001\", \"symbol\": \"NVDA\", \"source_hypothesis_id\": \"hyp-legacy\", \"source_research_candidate_decision\": \"candidate\", \"created_at\": \"2026-08-09T12:00:00+00:00\", \"status\": \"proposed\", \"entry_logic\": \"Entry\", \"exit_logic\": \"Exit\", \"invalidation_logic\": \"Invalidate\", \"maximum_holding_period\": \"5D\", \"position_sizing_rule\": \"Rule\", \"max_loss_per_trade\": 0.01, \"max_portfolio_exposure\": 0.05, \"demo_only\": true, \"monitoring_frequency\": \"15m\"}\n",
                encoding="utf-8",
            )

            loaded = storage.load_demo_trade_candidates(symbol="NVDA")

            self.assertEqual(1, len(loaded))
            self.assertEqual((), loaded[0].pause_conditions)
            self.assertEqual({}, dict(loaded[0].source_evidence_summary))
            self.assertEqual(None, loaded[0].source_review_action)
            self.assertEqual(None, loaded[0].source_review_confidence)
            self.assertEqual((), loaded[0].risk_flags)
            self.assertEqual("", loaded[0].created_by)


if __name__ == "__main__":
    unittest.main()