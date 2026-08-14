import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai.storage import Storage
from research.demo_hypothesis_performance_summary import (
    DemoHypothesisPerformanceSummary,
    build_demo_hypothesis_performance_summaries,
    build_evaluation_fingerprint,
    classify_promotion_readiness,
    classify_summary_rating,
)
from research.runner import _build_arg_parser, run_manual_demo_hypothesis_performance_summary


def _evaluation(**overrides):
    base = {
        "demo_trade_evaluation_id": "dtev-NVDA-001",
        "symbol": "NVDA",
        "performance_snapshot_id": "dpsp-NVDA-001",
        "order_intent_id": "doi-NVDA-001",
        "broker_order_id": "br-001",
        "broker_order_record_id": "br-001",
        "queue_item_id": "dtq-NVDA-001",
        "demo_trade_candidate_id": "dtc-001",
        "source_hypothesis_id": "hyp-001",
        "evaluated_at": datetime(2026, 8, 12, 15, 0, tzinfo=timezone.utc),
        "entry_reference_time": datetime(2026, 8, 3, 14, 0, tzinfo=timezone.utc),
        "trading_days_elapsed": 1,
        "evaluation_window_trading_days": 5,
        "evaluation_window_complete": False,
        "current_rating": "flat_open",
        "evaluation_status": "needs_more_time",
        "recommended_action": "continue_monitoring",
        "side": "long",
        "filled_qty": 2.0,
        "filled_avg_price": 100.0,
        "current_price": 110.0,
        "entry_value": 200.0,
        "current_value": 220.0,
        "unrealized_pl": 20.0,
        "unrealized_plpc": 0.1,
        "max_loss_per_trade": 0.01,
        "risk_breached": False,
        "demo_only": True,
        "created_by": "sentinel",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _storage(evaluations=(), summaries=()):
    storage = Mock()
    storage.load_demo_trade_evaluations.return_value = list(evaluations)
    storage.load_demo_hypothesis_performance_summaries.return_value = list(summaries)
    return storage


def _build(evaluations=(), summaries=()):
    storage = _storage(evaluations=evaluations, summaries=summaries)
    result = build_demo_hypothesis_performance_summaries(symbol="NVDA", storage=storage)
    return result, storage


class DemoHypothesisPerformanceSummaryTests(unittest.TestCase):
    def test_cli_help_includes_demo_hypothesis_performance_summary(self):
        parser = _build_arg_parser()

        self.assertIn("demo-hypothesis-performance-summary", parser.format_help())

    def test_makes_no_broker_or_http_calls(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            result, storage = _build(evaluations=[_evaluation()])

        mock_urlopen.assert_not_called()
        non_load_calls = {name for name, *_ in storage.method_calls if not name.startswith("load_")}
        self.assertEqual({"save_demo_hypothesis_performance_summary"}, non_load_calls)
        self.assertEqual(1, result.summaries_created)

    def test_creates_one_summary_per_source_hypothesis_from_latest_evaluations(self):
        evaluations = [
            _evaluation(
                demo_trade_evaluation_id="dtev-NVDA-old",
                evaluated_at=datetime(2026, 8, 11, 15, 0, tzinfo=timezone.utc),
                evaluation_status="risk_breach",
            ),
            _evaluation(demo_trade_evaluation_id="dtev-NVDA-new"),
            _evaluation(
                demo_trade_evaluation_id="dtev-NVDA-002",
                broker_order_id="br-002",
                order_intent_id="doi-NVDA-002",
                demo_trade_candidate_id="dtc-002",
                source_hypothesis_id="hyp-002",
            ),
        ]

        result, storage = _build(evaluations=evaluations)

        self.assertEqual(3, result.trade_evaluations_loaded)
        self.assertEqual(2, result.hypotheses_summarized)
        self.assertEqual(2, result.summaries_created)
        self.assertTrue(result.records_modified)
        self.assertEqual(2, storage.save_demo_hypothesis_performance_summary.call_count)
        first = result.summaries[0]
        self.assertEqual("hyp-001", first.source_hypothesis_id)
        self.assertEqual(("dtev-NVDA-new",), first.evaluation_ids)
        self.assertEqual(("dtc-001",), first.demo_trade_candidate_ids)
        self.assertEqual(1, first.unique_demo_trade_candidates)
        self.assertEqual(0, first.risk_breach_count)

    def test_skips_duplicate_hypothesis_and_fingerprint(self):
        existing = DemoHypothesisPerformanceSummary(
            demo_hypothesis_summary_id="dhps-NVDA-001",
            symbol="NVDA",
            source_hypothesis_id="hyp-001",
            summarized_at=datetime(2026, 8, 12, 16, 0, tzinfo=timezone.utc),
            evaluation_fingerprint=build_evaluation_fingerprint(["dtev-NVDA-001"]),
        )

        result, storage = _build(evaluations=[_evaluation()], summaries=[existing])

        self.assertEqual(1, result.hypotheses_summarized)
        self.assertEqual(0, result.summaries_created)
        self.assertEqual(1, result.skipped_existing)
        self.assertFalse(result.records_modified)
        storage.save_demo_hypothesis_performance_summary.assert_not_called()

    def test_new_evaluation_changes_fingerprint_and_creates_new_summary(self):
        existing = DemoHypothesisPerformanceSummary(
            demo_hypothesis_summary_id="dhps-NVDA-001",
            symbol="NVDA",
            source_hypothesis_id="hyp-001",
            summarized_at=datetime(2026, 8, 12, 16, 0, tzinfo=timezone.utc),
            evaluation_fingerprint=build_evaluation_fingerprint(["dtev-NVDA-001"]),
        )
        evaluations = [
            _evaluation(),
            _evaluation(
                demo_trade_evaluation_id="dtev-NVDA-002",
                broker_order_id="br-002",
                order_intent_id="doi-NVDA-002",
            ),
        ]

        result, _ = _build(evaluations=evaluations, summaries=[existing])

        self.assertEqual(1, result.summaries_created)
        self.assertEqual(0, result.skipped_existing)
        self.assertEqual(("dtev-NVDA-001", "dtev-NVDA-002"), result.summaries[0].evaluation_ids)

    def test_calculates_totals(self):
        evaluations = [
            _evaluation(),
            _evaluation(
                demo_trade_evaluation_id="dtev-NVDA-002",
                broker_order_id="br-002",
                order_intent_id="doi-NVDA-002",
                demo_trade_candidate_id="dtc-002",
                entry_value=300.0,
                current_value=270.0,
                unrealized_pl=-30.0,
                unrealized_plpc=-0.1,
                evaluation_status="weak_window",
                evaluation_window_complete=True,
            ),
        ]

        result, _ = _build(evaluations=evaluations)

        summary = result.summaries[0]
        self.assertEqual(2, summary.trades_evaluated)
        self.assertEqual(2, summary.unique_demo_trade_candidates)
        self.assertEqual(500.0, summary.total_entry_value)
        self.assertEqual(490.0, summary.total_current_value)
        self.assertEqual(-10.0, summary.total_unrealized_pl)
        self.assertAlmostEqual(-0.02, summary.total_unrealized_plpc)
        self.assertEqual(1, summary.evaluation_window_complete_count)
        self.assertEqual(2, summary.open_count)
        self.assertEqual(0.5, summary.completion_rate)
        self.assertEqual(0.0, summary.risk_breach_rate)

    def test_calculates_average_best_and_worst_unrealized_plpc(self):
        evaluations = [
            _evaluation(unrealized_plpc=0.1),
            _evaluation(
                demo_trade_evaluation_id="dtev-NVDA-002",
                broker_order_id="br-002",
                order_intent_id="doi-NVDA-002",
                unrealized_plpc=-0.02,
            ),
            _evaluation(
                demo_trade_evaluation_id="dtev-NVDA-003",
                broker_order_id="br-003",
                order_intent_id="doi-NVDA-003",
                unrealized_plpc=0.04,
            ),
        ]

        result, _ = _build(evaluations=evaluations)

        summary = result.summaries[0]
        self.assertAlmostEqual(0.04, summary.average_unrealized_plpc)
        self.assertEqual(0.1, summary.best_unrealized_plpc)
        self.assertEqual(-0.02, summary.worst_unrealized_plpc)

    def test_all_needs_more_time_is_needs_more_time_rating(self):
        result, _ = _build(evaluations=[_evaluation()])

        summary = result.summaries[0]
        self.assertEqual("needs_more_time", summary.current_summary_rating)
        self.assertEqual(1, result.rating_counts["needs_more_time"])

    def test_risk_breach_count_produces_risk_breach_rating(self):
        evaluations = [
            _evaluation(evaluation_status="risk_breach", risk_breached=True, evaluation_window_complete=True),
            _evaluation(
                demo_trade_evaluation_id="dtev-NVDA-002",
                broker_order_id="br-002",
                order_intent_id="doi-NVDA-002",
                evaluation_status="successful_window",
                evaluation_window_complete=True,
            ),
        ]

        result, _ = _build(evaluations=evaluations)

        summary = result.summaries[0]
        self.assertEqual("risk_breach", summary.current_summary_rating)
        self.assertEqual(1, summary.risk_breach_count)
        self.assertEqual(0.5, summary.risk_breach_rate)

    def test_successful_window_without_risk_breach_is_promising_demo(self):
        evaluations = [
            _evaluation(evaluation_status="successful_window", evaluation_window_complete=True),
            _evaluation(
                demo_trade_evaluation_id="dtev-NVDA-002",
                broker_order_id="br-002",
                order_intent_id="doi-NVDA-002",
                evaluation_status="flat_window",
                evaluation_window_complete=True,
            ),
        ]

        result, _ = _build(evaluations=evaluations)

        self.assertEqual("promising_demo", result.summaries[0].current_summary_rating)

    def test_rating_and_readiness_tables(self):
        self.assertEqual(
            "weak_demo",
            classify_summary_rating(
                trades_evaluated=2,
                needs_more_time_count=1,
                successful_window_count=0,
                flat_window_count=0,
                weak_window_count=1,
                risk_breach_count=0,
            ),
        )
        self.assertEqual(
            "flat_demo",
            classify_summary_rating(
                trades_evaluated=2,
                needs_more_time_count=1,
                successful_window_count=0,
                flat_window_count=1,
                weak_window_count=0,
                risk_breach_count=0,
            ),
        )
        self.assertEqual(
            "unknown",
            classify_summary_rating(
                trades_evaluated=1,
                needs_more_time_count=0,
                successful_window_count=0,
                flat_window_count=0,
                weak_window_count=0,
                risk_breach_count=0,
            ),
        )
        self.assertEqual(
            "not_ready",
            classify_promotion_readiness(
                trades_evaluated=2,
                needs_more_time_count=2,
                evaluation_window_complete_count=0,
            ),
        )
        self.assertEqual(
            "monitor",
            classify_promotion_readiness(
                trades_evaluated=3,
                needs_more_time_count=3,
                evaluation_window_complete_count=0,
            ),
        )
        self.assertEqual(
            "review_later",
            classify_promotion_readiness(
                trades_evaluated=3,
                needs_more_time_count=1,
                evaluation_window_complete_count=2,
            ),
        )
        self.assertNotIn(
            "promote",
            {
                classify_promotion_readiness(
                    trades_evaluated=trades,
                    needs_more_time_count=0,
                    evaluation_window_complete_count=trades,
                )
                for trades in range(0, 10)
            },
        )

    def test_handles_no_evaluations_safely(self):
        result, storage = _build(evaluations=[])

        self.assertEqual(0, result.trade_evaluations_loaded)
        self.assertEqual(0, result.hypotheses_summarized)
        self.assertEqual((), result.summaries)
        self.assertFalse(result.records_modified)
        storage.save_demo_hypothesis_performance_summary.assert_not_called()

    def test_handles_missing_source_hypothesis_id_safely(self):
        result, storage = _build(evaluations=[_evaluation(source_hypothesis_id="")])

        self.assertEqual(1, result.skipped_ineligible)
        self.assertEqual(0, result.summaries_created)
        storage.save_demo_hypothesis_performance_summary.assert_not_called()

    def test_handles_missing_evaluation_id_safely(self):
        result, storage = _build(evaluations=[_evaluation(demo_trade_evaluation_id="")])

        self.assertEqual(1, result.failed_summaries)
        self.assertEqual(0, result.summaries_created)
        storage.save_demo_hypothesis_performance_summary.assert_not_called()

    def test_handles_missing_numeric_data_safely(self):
        result, _ = _build(
            evaluations=[
                _evaluation(
                    entry_value=None,
                    current_value=None,
                    unrealized_pl=None,
                    unrealized_plpc=None,
                    evaluation_status="unknown",
                )
            ]
        )

        summary = result.summaries[0]
        self.assertEqual(0.0, summary.total_entry_value)
        self.assertEqual(0.0, summary.total_unrealized_plpc)
        self.assertEqual(0.0, summary.average_unrealized_plpc)
        self.assertIsNone(summary.best_unrealized_plpc)
        self.assertIsNone(summary.worst_unrealized_plpc)
        self.assertEqual(0, summary.open_count)
        self.assertEqual(1, summary.unknown_count)
        self.assertEqual("unknown", summary.current_summary_rating)


class DemoHypothesisPerformanceSummaryStorageTests(unittest.TestCase):
    def _summary(self, **overrides):
        base = {
            "demo_hypothesis_summary_id": "dhps-NVDA-001",
            "symbol": "NVDA",
            "source_hypothesis_id": "hyp-001",
            "summarized_at": datetime(2026, 8, 12, 16, 0, tzinfo=timezone.utc),
            "evaluation_fingerprint": "abc123",
            "evaluation_ids": ("dtev-NVDA-001",),
            "demo_trade_candidate_ids": ("dtc-001",),
            "trades_evaluated": 1,
            "unique_demo_trade_candidates": 1,
            "needs_more_time_count": 1,
            "evaluation_window_complete_count": 0,
            "open_count": 1,
            "total_entry_value": 200.0,
            "total_current_value": 220.0,
            "total_unrealized_pl": 20.0,
            "total_unrealized_plpc": 0.1,
            "average_unrealized_plpc": 0.1,
            "best_unrealized_plpc": 0.1,
            "worst_unrealized_plpc": 0.1,
            "current_summary_rating": "needs_more_time",
            "promotion_readiness": "not_ready",
        }
        base.update(overrides)
        return DemoHypothesisPerformanceSummary(**base)

    def test_appends_and_loads_summaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = Storage()
            storage.base = Path(temp_dir)
            storage.save_demo_hypothesis_performance_summary(self._summary())
            storage.save_demo_hypothesis_performance_summary(
                self._summary(demo_hypothesis_summary_id="dhps-NVDA-002", evaluation_fingerprint="def456")
            )

            loaded = storage.load_demo_hypothesis_performance_summaries()

            self.assertEqual(2, len(loaded))
            self.assertEqual("dhps-NVDA-001", loaded[0].demo_hypothesis_summary_id)
            self.assertEqual(("dtev-NVDA-001",), loaded[0].evaluation_ids)
            self.assertEqual("needs_more_time", loaded[0].current_summary_rating)
            self.assertEqual("Demo evidence summary only. Not a promotion decision.", loaded[0].note)

            lines = (
                (Path(temp_dir) / "demo_hypothesis_performance_summaries.jsonl")
                .read_text(encoding="utf-8")
                .strip()
                .splitlines()
            )
            self.assertEqual(2, len(lines))
            self.assertEqual("abc123", json.loads(lines[0])["evaluation_fingerprint"])

    def test_symbol_filter_works(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = Storage()
            storage.base = Path(temp_dir)
            storage.save_demo_hypothesis_performance_summary(self._summary())
            storage.save_demo_hypothesis_performance_summary(
                self._summary(demo_hypothesis_summary_id="dhps-AAPL-001", symbol="AAPL")
            )

            self.assertEqual(1, len(storage.load_demo_hypothesis_performance_summaries(symbol="NVDA")))
            self.assertEqual(1, len(storage.load_demo_hypothesis_performance_summaries(symbol="AAPL")))
            self.assertEqual(2, len(storage.load_demo_hypothesis_performance_summaries()))

    def test_load_returns_empty_when_file_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = Storage()
            storage.base = Path(temp_dir)

            self.assertEqual([], storage.load_demo_hypothesis_performance_summaries(symbol="NVDA"))


class DemoHypothesisPerformanceSummaryRunnerTests(unittest.TestCase):
    def test_runner_prints_summary(self):
        storage = _storage(evaluations=[_evaluation()])

        with patch("builtins.print") as mock_print:
            run_manual_demo_hypothesis_performance_summary(symbol="NVDA", storage=storage)

        mock_print.assert_any_call("Manual Demo Hypothesis Performance Summary: NVDA")
        mock_print.assert_any_call("Records Modified : yes")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Broker Calls Allowed : no")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Order Cancellation Allowed : no")
        mock_print.assert_any_call("Position Close Allowed : no")
        mock_print.assert_any_call("Live Mode Allowed : no")
        mock_print.assert_any_call("Trade Evaluations Loaded : 1")
        mock_print.assert_any_call("Hypotheses Summarized : 1")
        mock_print.assert_any_call("Summaries Created : 1")
        mock_print.assert_any_call("Skipped Existing : 0")
        mock_print.assert_any_call("Skipped Ineligible : 0")
        mock_print.assert_any_call("Failed Summaries : 0")
        mock_print.assert_any_call("  source_hypothesis_id=hyp-001")
        mock_print.assert_any_call("  trades_evaluated=1")
        mock_print.assert_any_call("  current_summary_rating=needs_more_time")
        mock_print.assert_any_call("  promotion_readiness=not_ready")
        mock_print.assert_any_call("  note=Demo evidence summary only. Not a promotion decision.")
        mock_print.assert_any_call("  demo_only=True")
        mock_print.assert_any_call("hypotheses_summarized=1")
        mock_print.assert_any_call("needs_more_time=1")
        mock_print.assert_any_call("risk_breach=0")
        mock_print.assert_any_call(
            "Demo hypothesis performance summaries were appended locally. This is not promotion and not an exit order."
            " No broker calls were made. No orders were submitted, cancelled, replaced, or closed."
        )

    def test_runner_reports_no_records_modified_when_nothing_created(self):
        storage = _storage()

        with patch("builtins.print") as mock_print:
            run_manual_demo_hypothesis_performance_summary(symbol="NVDA", storage=storage)

        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("No new demo hypothesis performance summaries were created.")
        mock_print.assert_any_call(
            "No new demo hypothesis performance summaries were created. Existing summaries were left unchanged."
            " This is not promotion and not an exit order. No broker calls were made."
            " No orders were submitted, cancelled, replaced, or closed."
        )
        storage.save_demo_hypothesis_performance_summary.assert_not_called()


if __name__ == "__main__":
    unittest.main()
