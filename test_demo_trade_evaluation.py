import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ai.storage import Storage
from research.demo_trade_evaluation import (
    DemoTradeEvaluation,
    build_demo_trade_evaluations,
    classify_demo_trade_evaluation,
    count_trading_days,
)
from research.runner import _build_arg_parser, run_manual_demo_trade_evaluation


_ENTRY_TIME = datetime(2026, 8, 3, 14, 0, tzinfo=timezone.utc)


def _performance_snapshot(**overrides):
    base = {
        "performance_snapshot_id": "dpsp-NVDA-001",
        "symbol": "NVDA",
        "order_intent_id": "doi-NVDA-001",
        "broker_order_id": "br-001",
        "broker_order_record_id": "br-001",
        "queue_item_id": "dtq-NVDA-001",
        "demo_trade_candidate_id": "dtc-001",
        "source_hypothesis_id": "hyp-001",
        "snapshot_at": datetime(2026, 8, 4, 14, 0, tzinfo=timezone.utc),
        "status": "open",
        "side": "long",
        "filled_qty": 2.0,
        "filled_avg_price": 100.0,
        "current_price": 110.0,
        "entry_value": 200.0,
        "current_value": 220.0,
        "unrealized_pl": 20.0,
        "unrealized_plpc": 0.1,
        "position_snapshot_id": "dps-NVDA-001",
        "demo_only": True,
        "created_by": "sentinel",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _broker_order_record(**overrides):
    base = {
        "broker_order_id": "br-001",
        "order_intent_id": "doi-NVDA-001",
        "symbol": "NVDA",
        "created_at": _ENTRY_TIME,
        "demo_only": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _order_status(**overrides):
    base = {
        "broker_order_status_id": "bos-001",
        "broker_order_id": "br-001",
        "order_intent_id": "doi-NVDA-001",
        "symbol": "NVDA",
        "synced_at": _ENTRY_TIME,
        "status": "filled",
        "raw_status": "filled",
        "filled_qty": 2.0,
        "filled_avg_price": 100.0,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _intent(**overrides):
    base = {
        "order_intent_id": "doi-NVDA-001",
        "symbol": "NVDA",
        "queue_item_id": "dtq-NVDA-001",
        "demo_trade_candidate_id": "dtc-001",
        "source_hypothesis_id": "hyp-001",
        "created_at": _ENTRY_TIME,
        "status": "submitted",
        "max_loss_per_trade": 0.01,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _candidate(**overrides):
    base = {
        "trade_candidate_id": "dtc-001",
        "symbol": "NVDA",
        "source_hypothesis_id": "hyp-001",
        "max_loss_per_trade": 0.02,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _storage(
    snapshots=(),
    intents=(),
    candidates=(),
    records=(),
    statuses=(),
    evaluations=(),
):
    storage = Mock()
    storage.load_demo_trade_performance_snapshots.return_value = list(snapshots)
    storage.load_demo_order_intents.return_value = list(intents)
    storage.load_demo_trade_candidates.return_value = list(candidates)
    storage.load_demo_broker_order_records.return_value = list(records)
    storage.load_demo_broker_order_statuses.return_value = list(statuses)
    storage.load_demo_trade_evaluations.return_value = list(evaluations)
    return storage


def _build(snapshot_overrides=None, **storage_kwargs):
    snapshots = storage_kwargs.pop("snapshots", None)
    if snapshots is None:
        snapshots = [_performance_snapshot(**(snapshot_overrides or {}))]

    storage = _storage(
        snapshots=snapshots,
        intents=storage_kwargs.pop("intents", [_intent()]),
        candidates=storage_kwargs.pop("candidates", [_candidate()]),
        records=storage_kwargs.pop("records", [_broker_order_record()]),
        statuses=storage_kwargs.pop("statuses", [_order_status()]),
        evaluations=storage_kwargs.pop("evaluations", []),
    )

    with patch("research.demo_trade_evaluation.settings.DEMO_TRADE_EVALUATION_WINDOW_TRADING_DAYS", 5):
        result = build_demo_trade_evaluations(symbol="NVDA", storage=storage)

    return result, storage


class DemoTradeEvaluationTests(unittest.TestCase):
    def test_cli_help_includes_demo_trade_evaluation(self):
        parser = _build_arg_parser()

        self.assertIn("demo-trade-evaluation", parser.format_help())

    def test_makes_no_broker_or_http_calls(self):
        with patch("urllib.request.urlopen") as mock_urlopen:
            result, storage = _build()

        mock_urlopen.assert_not_called()
        called = {call[0] for call in storage.method_calls}
        self.assertEqual({"save_demo_trade_evaluation"}, {name for name in called if not name.startswith("load_")})
        self.assertEqual(1, result.evaluations_created)

    def test_creates_evaluation_from_latest_performance_snapshot(self):
        snapshots = [
            _performance_snapshot(
                performance_snapshot_id="dpsp-NVDA-old",
                snapshot_at=datetime(2026, 8, 4, 10, 0, tzinfo=timezone.utc),
                unrealized_plpc=-0.05,
            ),
            _performance_snapshot(
                performance_snapshot_id="dpsp-NVDA-new",
                snapshot_at=datetime(2026, 8, 4, 15, 0, tzinfo=timezone.utc),
            ),
        ]

        result, storage = _build(snapshots=snapshots)

        self.assertEqual(2, result.performance_snapshots_loaded)
        self.assertEqual(1, result.evaluations_created)
        self.assertTrue(result.records_modified)
        evaluation = result.evaluations[0]
        self.assertEqual("dpsp-NVDA-new", evaluation.performance_snapshot_id)
        self.assertEqual("hyp-001", evaluation.source_hypothesis_id)
        self.assertEqual(_ENTRY_TIME, evaluation.entry_reference_time)
        self.assertEqual(1, evaluation.trading_days_elapsed)
        self.assertEqual(5, evaluation.evaluation_window_trading_days)
        self.assertEqual(0.01, evaluation.max_loss_per_trade)
        storage.save_demo_trade_evaluation.assert_called_once()

    def test_skips_duplicate_performance_snapshot_id(self):
        existing = DemoTradeEvaluation(
            demo_trade_evaluation_id="dtev-NVDA-001",
            symbol="NVDA",
            performance_snapshot_id="dpsp-NVDA-001",
            order_intent_id="doi-NVDA-001",
            broker_order_id="br-001",
            broker_order_record_id="br-001",
            queue_item_id="dtq-NVDA-001",
            demo_trade_candidate_id="dtc-001",
            source_hypothesis_id="hyp-001",
            evaluated_at=datetime(2026, 8, 4, 15, 0, tzinfo=timezone.utc),
        )

        result, storage = _build(evaluations=[existing])

        self.assertEqual(0, result.evaluations_created)
        self.assertEqual(1, result.skipped_existing)
        self.assertFalse(result.records_modified)
        storage.save_demo_trade_evaluation.assert_not_called()

    def test_risk_breach_classification(self):
        result, _ = _build(snapshot_overrides={"unrealized_plpc": -0.04, "unrealized_pl": -40.0})

        evaluation = result.evaluations[0]
        self.assertEqual("risk_breach", evaluation.current_rating)
        self.assertEqual("risk_breach", evaluation.evaluation_status)
        self.assertEqual("exit_candidate", evaluation.recommended_action)
        self.assertTrue(evaluation.risk_breached)
        self.assertEqual(1, result.status_counts["risk_breach"])

    def test_positive_incomplete_window_is_needs_more_time(self):
        result, _ = _build(snapshot_overrides={"unrealized_plpc": 0.02})

        evaluation = result.evaluations[0]
        self.assertFalse(evaluation.evaluation_window_complete)
        self.assertEqual("positive_open", evaluation.current_rating)
        self.assertEqual("needs_more_time", evaluation.evaluation_status)
        self.assertEqual("continue_monitoring", evaluation.recommended_action)

    def test_flat_incomplete_window_is_needs_more_time(self):
        result, _ = _build(snapshot_overrides={"unrealized_plpc": 0.0})

        evaluation = result.evaluations[0]
        self.assertEqual("flat_open", evaluation.current_rating)
        self.assertEqual("needs_more_time", evaluation.evaluation_status)

    def test_positive_complete_window_is_successful_window(self):
        result, _ = _build(
            snapshot_overrides={
                "unrealized_plpc": 0.02,
                "snapshot_at": datetime(2026, 8, 12, 14, 0, tzinfo=timezone.utc),
            }
        )

        evaluation = result.evaluations[0]
        self.assertTrue(evaluation.evaluation_window_complete)
        self.assertEqual("successful_window", evaluation.evaluation_status)
        self.assertEqual("continue_or_review_for_promotion", evaluation.recommended_action)

    def test_flat_complete_window_is_flat_window(self):
        result, _ = _build(
            snapshot_overrides={
                "unrealized_plpc": 0.001,
                "snapshot_at": datetime(2026, 8, 12, 14, 0, tzinfo=timezone.utc),
            }
        )

        evaluation = result.evaluations[0]
        self.assertEqual("flat_window", evaluation.evaluation_status)
        self.assertEqual("needs_more_time_or_exit_review", evaluation.recommended_action)

    def test_weak_complete_window_is_weak_window(self):
        result, _ = _build(
            snapshot_overrides={
                "unrealized_plpc": -0.01,
                "snapshot_at": datetime(2026, 8, 12, 14, 0, tzinfo=timezone.utc),
            }
        )

        evaluation = result.evaluations[0]
        self.assertEqual("weak_open", evaluation.current_rating)
        self.assertEqual("weak_window", evaluation.evaluation_status)
        self.assertEqual("exit_candidate_or_continue_monitoring", evaluation.recommended_action)

    def test_missing_performance_data_is_unknown(self):
        result, _ = _build(snapshot_overrides={"unrealized_plpc": None})

        evaluation = result.evaluations[0]
        self.assertEqual("unknown", evaluation.current_rating)
        self.assertEqual("unknown", evaluation.evaluation_status)
        self.assertEqual("manual_review", evaluation.recommended_action)

    def test_missing_snapshot_id_is_skipped_safely(self):
        result, storage = _build(snapshot_overrides={"performance_snapshot_id": ""})

        self.assertEqual(1, result.skipped_ineligible)
        self.assertEqual(0, result.evaluations_created)
        storage.save_demo_trade_evaluation.assert_not_called()

    def test_missing_snapshot_time_is_failed_evaluation(self):
        result, storage = _build(snapshot_overrides={"snapshot_at": None})

        self.assertEqual(1, result.failed_evaluations)
        self.assertEqual(0, result.evaluations_created)
        storage.save_demo_trade_evaluation.assert_not_called()

    def test_handles_no_performance_snapshots_safely(self):
        result, storage = _build(snapshots=[])

        self.assertEqual(0, result.performance_snapshots_loaded)
        self.assertEqual((), result.evaluations)
        self.assertFalse(result.records_modified)
        storage.save_demo_trade_evaluation.assert_not_called()

    def test_falls_back_to_earliest_status_synced_at_when_no_broker_record(self):
        result, _ = _build(
            records=[],
            statuses=[
                _order_status(synced_at=datetime(2026, 8, 5, 14, 0, tzinfo=timezone.utc)),
                _order_status(broker_order_status_id="bos-002", synced_at=_ENTRY_TIME),
            ],
        )

        self.assertEqual(_ENTRY_TIME, result.evaluations[0].entry_reference_time)

    def test_count_trading_days_uses_weekdays_only(self):
        friday = datetime(2026, 8, 7, 14, 0, tzinfo=timezone.utc)
        monday = datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc)

        self.assertEqual(1, count_trading_days(friday, monday))
        self.assertEqual(0, count_trading_days(monday, monday))
        self.assertEqual(0, count_trading_days(monday, friday))
        self.assertEqual(0, count_trading_days(None, monday))
        self.assertEqual(5, count_trading_days(_ENTRY_TIME, datetime(2026, 8, 10, 14, 0, tzinfo=timezone.utc)))

    def test_classification_table(self):
        self.assertEqual(
            ("risk_breach", "exit_candidate"),
            classify_demo_trade_evaluation(current_rating="risk_breach", evaluation_window_complete=False),
        )
        self.assertEqual(
            ("unknown", "manual_review"),
            classify_demo_trade_evaluation(current_rating="unknown", evaluation_window_complete=True),
        )


class DemoTradeEvaluationStorageTests(unittest.TestCase):
    def _evaluation(self, **overrides):
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
            "evaluated_at": datetime(2026, 8, 4, 15, 0, tzinfo=timezone.utc),
            "entry_reference_time": _ENTRY_TIME,
            "trading_days_elapsed": 1,
            "evaluation_window_trading_days": 5,
            "evaluation_window_complete": False,
            "current_rating": "positive_open",
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
        return DemoTradeEvaluation(**base)

    def test_appends_and_loads_evaluations(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = Storage()
            storage.base = Path(temp_dir)
            storage.save_demo_trade_evaluation(self._evaluation())
            storage.save_demo_trade_evaluation(
                self._evaluation(demo_trade_evaluation_id="dtev-NVDA-002", performance_snapshot_id="dpsp-NVDA-002")
            )

            loaded = storage.load_demo_trade_evaluations()

            self.assertEqual(2, len(loaded))
            self.assertEqual("dtev-NVDA-001", loaded[0].demo_trade_evaluation_id)
            self.assertEqual(_ENTRY_TIME, loaded[0].entry_reference_time)
            self.assertEqual("needs_more_time", loaded[0].evaluation_status)

            lines = (Path(temp_dir) / "demo_trade_evaluations.jsonl").read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(2, len(lines))
            self.assertEqual("dpsp-NVDA-001", json.loads(lines[0])["performance_snapshot_id"])

    def test_symbol_filter_works(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = Storage()
            storage.base = Path(temp_dir)
            storage.save_demo_trade_evaluation(self._evaluation())
            storage.save_demo_trade_evaluation(
                self._evaluation(
                    demo_trade_evaluation_id="dtev-AAPL-001",
                    symbol="AAPL",
                    performance_snapshot_id="dpsp-AAPL-001",
                )
            )

            self.assertEqual(1, len(storage.load_demo_trade_evaluations(symbol="NVDA")))
            self.assertEqual(1, len(storage.load_demo_trade_evaluations(symbol="AAPL")))
            self.assertEqual(2, len(storage.load_demo_trade_evaluations()))

    def test_load_returns_empty_when_file_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = Storage()
            storage.base = Path(temp_dir)

            self.assertEqual([], storage.load_demo_trade_evaluations(symbol="NVDA"))


class DemoTradeEvaluationRunnerTests(unittest.TestCase):
    def test_runner_prints_evaluation_summary(self):
        storage = _storage(
            snapshots=[_performance_snapshot(unrealized_plpc=0.0)],
            intents=[_intent()],
            candidates=[_candidate()],
            records=[_broker_order_record()],
            statuses=[_order_status()],
        )

        with patch(
            "research.demo_trade_evaluation.settings.DEMO_TRADE_EVALUATION_WINDOW_TRADING_DAYS", 5
        ), patch("builtins.print") as mock_print:
            run_manual_demo_trade_evaluation(symbol="NVDA", storage=storage)

        mock_print.assert_any_call("Manual Demo Trade Evaluation: NVDA")
        mock_print.assert_any_call("Records Modified : yes")
        mock_print.assert_any_call("AI Calls Allowed : no")
        mock_print.assert_any_call("Broker Calls Allowed : no")
        mock_print.assert_any_call("Order Placement Allowed : no")
        mock_print.assert_any_call("Order Cancellation Allowed : no")
        mock_print.assert_any_call("Position Close Allowed : no")
        mock_print.assert_any_call("Live Mode Allowed : no")
        mock_print.assert_any_call("Performance Snapshots Loaded : 1")
        mock_print.assert_any_call("Evaluations Created : 1")
        mock_print.assert_any_call("Skipped Existing : 0")
        mock_print.assert_any_call("Skipped Ineligible : 0")
        mock_print.assert_any_call("Failed Evaluations : 0")
        mock_print.assert_any_call("  performance_snapshot_id=dpsp-NVDA-001")
        mock_print.assert_any_call("  evaluation_window_complete=False")
        mock_print.assert_any_call("  current_rating=flat_open")
        mock_print.assert_any_call("  evaluation_status=needs_more_time")
        mock_print.assert_any_call("  recommended_action=continue_monitoring")
        mock_print.assert_any_call("  risk_breached=False")
        mock_print.assert_any_call("  demo_only=True")
        mock_print.assert_any_call("needs_more_time=1")
        mock_print.assert_any_call("risk_breach=0")
        mock_print.assert_any_call(
            "Demo trade evaluations were appended locally. This is not promotion and not an exit order."
            " No broker calls were made. No orders were submitted, cancelled, replaced, or closed."
        )

    def test_runner_reports_no_records_modified_when_nothing_created(self):
        storage = _storage()

        with patch("builtins.print") as mock_print:
            run_manual_demo_trade_evaluation(symbol="NVDA", storage=storage)

        mock_print.assert_any_call("Records Modified : no")
        mock_print.assert_any_call("No new demo trade evaluations were created.")
        mock_print.assert_any_call(
            "No new demo trade evaluations were created. Existing evaluations were left unchanged."
            " This is not promotion and not an exit order. No broker calls were made."
            " No orders were submitted, cancelled, replaced, or closed."
        )
        storage.save_demo_trade_evaluation.assert_not_called()


if __name__ == "__main__":
    unittest.main()
