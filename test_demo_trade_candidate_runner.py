import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from ai.demo_trade_candidate_service import DemoTradeCandidateGenerationResult
from research.demo_trade_candidate import DemoTradeCandidate
from research.demo_trade_candidate import DemoTradeCandidateStatus
from research.runner import (
    DEFAULT_SYMBOL,
    run_manual_demo_trade_candidate_generation,
    run_manual_demo_trade_candidates,
)


def _candidate(trade_candidate_id: str, symbol: str = "NVDA"):
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


class ManualDemoTradeCandidateRunnerTests(unittest.TestCase):
    def test_runner_is_read_only_and_prints_candidates(self):
        storage = Mock()
        storage.load_demo_trade_candidates.return_value = [_candidate("dtc-001")]

        with patch("builtins.print") as mock_print:
            candidates = run_manual_demo_trade_candidates(symbol="NVDA", storage=storage)

        self.assertEqual(1, len(candidates))
        mock_print.assert_any_call("Manual Demo Trade Candidates: NVDA")
        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Candidates Loaded : 1")
        mock_print.assert_any_call("Demo Trade Candidates")
        mock_print.assert_any_call("- candidate_id=dtc-001")
        mock_print.assert_any_call("  source_hypothesis_id=hyp-dtc-001")
        mock_print.assert_any_call("  status=proposed")
        mock_print.assert_any_call("  demo_only=True")
        mock_print.assert_any_call("  validation=valid")

        storage.load_demo_trade_candidates.assert_called_once_with(symbol="NVDA")
        storage.save_demo_trade_candidate.assert_not_called()

    def test_runner_prints_empty_message_when_none_exist(self):
        storage = Mock()
        storage.load_demo_trade_candidates.return_value = []

        with patch("builtins.print") as mock_print:
            candidates = run_manual_demo_trade_candidates(symbol="NVDA", storage=storage)

        self.assertEqual([], candidates)
        mock_print.assert_any_call("No demo trade candidates found.")

    def test_runner_uses_default_symbol(self):
        storage = Mock()
        storage.load_demo_trade_candidates.return_value = []

        with patch("builtins.print"):
            run_manual_demo_trade_candidates(storage=storage)

        storage.load_demo_trade_candidates.assert_called_once_with(symbol=DEFAULT_SYMBOL)

    def test_generation_runner_prints_summary_and_generated_candidates(self):
        storage = Mock()
        service = Mock()
        generated_candidate = DemoTradeCandidate(
            trade_candidate_id="dtc-101",
            symbol="NVDA",
            source_hypothesis_id="hyp-dtc-101",
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
            created_by="ai",
        )
        service.generate_for_symbol.return_value = DemoTradeCandidateGenerationResult(
            research_candidates_loaded=3,
            generation_candidates=2,
            generated_candidates=(generated_candidate,),
            skipped_existing=1,
            failed_validation=1,
        )

        with patch("builtins.print") as mock_print:
            result = run_manual_demo_trade_candidate_generation(
                symbol="NVDA",
                storage=storage,
                demo_trade_candidate_service=service,
            )

        self.assertEqual(1, len(result.generated_candidates))
        service.generate_for_symbol.assert_called_once_with(symbol="NVDA")
        mock_print.assert_any_call("Manual Demo Trade Candidate Generation: NVDA")
        mock_print.assert_any_call("Records Modified : yes")
        mock_print.assert_any_call("AI Calls Allowed : yes")
        mock_print.assert_any_call("Research Candidates Loaded : 3")
        mock_print.assert_any_call("Generation Candidates : 2")
        mock_print.assert_any_call("Generated : 1")
        mock_print.assert_any_call("Skipped Existing : 1")
        mock_print.assert_any_call("Failed Validation : 1")
        mock_print.assert_any_call("Generated Demo Trade Candidates")
        mock_print.assert_any_call("- candidate_id=dtc-101")
        mock_print.assert_any_call("  source_hypothesis_id=hyp-dtc-101")
        mock_print.assert_any_call("  status=proposed")
        mock_print.assert_any_call("  validation=valid")

    def test_generation_runner_prints_empty_message_when_none_generated(self):
        storage = Mock()
        service = Mock()
        service.generate_for_symbol.return_value = DemoTradeCandidateGenerationResult(
            research_candidates_loaded=1,
            generation_candidates=1,
            generated_candidates=(),
            skipped_existing=0,
            failed_validation=1,
        )

        with patch("builtins.print") as mock_print:
            run_manual_demo_trade_candidate_generation(
                symbol="NVDA",
                storage=storage,
                demo_trade_candidate_service=service,
            )

        mock_print.assert_any_call("No demo trade candidates generated.")


if __name__ == "__main__":
    unittest.main()