import tempfile
import unittest
import json
from datetime import datetime, timezone
from pathlib import Path

from ai.storage import Storage
from research.experiment import ExperimentTestType
from research.experiment_result import (
    ExperimentMetrics,
    ExperimentResult,
    ExperimentResultStatus,
)


class ExperimentResultStorageTests(unittest.TestCase):
    def test_save_and_load_experiment_results_for_symbol(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            started_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
            completed_at = datetime(2026, 8, 3, 0, 10, tzinfo=timezone.utc)

            metrics = ExperimentMetrics(
                total_return=0.11,
                win_rate=0.57,
                max_drawdown=-0.08,
                trade_count=38,
                average_return=0.003,
                average_holding_period=3.2,
                profit_factor=1.35,
                annualized_return=0.22,
                volatility=0.14,
                sharpe_ratio=1.18,
                expectancy=0.002,
                extra_metrics={"benchmark_relative_return": 0.04},
            )

            result = ExperimentResult(
                experiment_result_id="expr-001",
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                metrics=metrics,
                summary="Initial backtest completed with positive expectancy.",
                created_at=started_at,
                updated_at=completed_at,
            )

            storage.save_experiment_results("NVDA", [result])

            loaded = storage.load_experiment_results("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertIsInstance(loaded[0], ExperimentResult)
            self.assertEqual("expr-001", loaded[0].experiment_result_id)
            self.assertEqual("expreq-001", loaded[0].experiment_request_id)
            self.assertEqual("hyp-001", loaded[0].hypothesis_id)
            self.assertEqual("NVDA", loaded[0].symbol)
            self.assertEqual(ExperimentTestType.INITIAL_BACKTEST, loaded[0].test_type)
            self.assertEqual(ExperimentResultStatus.COMPLETED, loaded[0].status)
            self.assertEqual(started_at, loaded[0].started_at)
            self.assertEqual(completed_at, loaded[0].completed_at)
            self.assertEqual(
                "Initial backtest completed with positive expectancy.",
                loaded[0].summary,
            )
            self.assertIsNone(loaded[0].failure_reason)
            self.assertEqual(0.11, loaded[0].metrics.total_return)
            self.assertEqual(0.57, loaded[0].metrics.win_rate)
            self.assertEqual(-0.08, loaded[0].metrics.max_drawdown)
            self.assertEqual(38, loaded[0].metrics.trade_count)
            self.assertEqual(0.003, loaded[0].metrics.average_return)
            self.assertEqual(3.2, loaded[0].metrics.average_holding_period)
            self.assertEqual(1.35, loaded[0].metrics.profit_factor)
            self.assertEqual(0.22, loaded[0].metrics.annualized_return)
            self.assertEqual(0.14, loaded[0].metrics.volatility)
            self.assertEqual(1.18, loaded[0].metrics.sharpe_ratio)
            self.assertEqual(0.002, loaded[0].metrics.expectancy)
            self.assertEqual(
                0.04,
                loaded[0].metrics.extra_metrics["benchmark_relative_return"],
            )
            self.assertEqual({}, dict(loaded[0].diagnostics))

            results_file = Path(tmp_dir) / "experiments" / "results" / "NVDA.json"
            self.assertTrue(results_file.exists())

    def test_save_experiment_results_is_append_only_by_identity(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            started_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
            completed_at = datetime(2026, 8, 3, 0, 5, tzinfo=timezone.utc)

            first = ExperimentResult(
                experiment_result_id="expr-001",
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                test_type=ExperimentTestType.EXPLORATORY,
                status=ExperimentResultStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                metrics=ExperimentMetrics(total_return=0.05),
                summary="First summary.",
                created_at=started_at,
                updated_at=completed_at,
            )

            duplicate = ExperimentResult(
                experiment_result_id="expr-001",
                experiment_request_id="expreq-001",
                hypothesis_id="hyp-001",
                symbol="NVDA",
                test_type=ExperimentTestType.EXPLORATORY,
                status=ExperimentResultStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                metrics=ExperimentMetrics(total_return=0.09),
                summary="Updated summary.",
                created_at=started_at,
                updated_at=completed_at,
            )

            storage.save_experiment_results("NVDA", [first])
            storage.save_experiment_results("NVDA", [duplicate])

            loaded = storage.load_experiment_results("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertEqual("First summary.", loaded[0].summary)
            self.assertEqual(0.05, loaded[0].metrics.total_return)

    def test_save_and_load_experiment_result_diagnostics(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)

            started_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
            completed_at = datetime(2026, 8, 3, 0, 10, tzinfo=timezone.utc)

            result = ExperimentResult(
                experiment_result_id="expr-200",
                experiment_request_id="expreq-200",
                hypothesis_id="hyp-200",
                symbol="NVDA",
                test_type=ExperimentTestType.INITIAL_BACKTEST,
                status=ExperimentResultStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                metrics=ExperimentMetrics(
                    total_return=0.02,
                    trade_count=3,
                    extra_metrics={
                        "rows_loaded": 503,
                        "rows_after_cleaning": 484,
                        "matching_setups": 4,
                        "forward_returns_available": 3,
                        "forward_returns_missing": 1,
                        "forward_horizon": 5,
                    },
                ),
                diagnostics={
                    "first_match_date": "2025-01-02",
                    "last_match_date": "2026-07-31",
                },
                summary="Backtest completed with diagnostics.",
                created_at=started_at,
                updated_at=completed_at,
            )

            storage.save_experiment_results("NVDA", [result])
            loaded = storage.load_experiment_results("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertEqual("2025-01-02", loaded[0].diagnostics["first_match_date"])
            self.assertEqual("2026-07-31", loaded[0].diagnostics["last_match_date"])
            self.assertEqual(503.0, loaded[0].metrics.extra_metrics["rows_loaded"])
            self.assertEqual(484.0, loaded[0].metrics.extra_metrics["rows_after_cleaning"])

    def test_load_old_result_records_without_diagnostics(self):
        storage = Storage()

        with tempfile.TemporaryDirectory() as tmp_dir:
            storage.base = Path(tmp_dir)
            results_path = Path(tmp_dir) / "experiments" / "results" / "NVDA.json"
            results_path.parent.mkdir(parents=True, exist_ok=True)
            results_path.write_text(
                json.dumps(
                    [
                        {
                            "experiment_result_id": "expr-legacy-001",
                            "experiment_request_id": "expreq-legacy-001",
                            "hypothesis_id": "hyp-legacy-001",
                            "symbol": "NVDA",
                            "test_type": "initial_backtest",
                            "status": "completed",
                            "started_at": "2026-08-03T00:00:00+00:00",
                            "completed_at": "2026-08-03T00:05:00+00:00",
                            "metrics": {
                                "total_return": 0.05,
                                "trade_count": 2,
                                "extra_metrics": {
                                    "best_return": 0.04,
                                },
                            },
                            "summary": "Legacy completed result.",
                            "failure_reason": None,
                            "created_at": "2026-08-03T00:00:00+00:00",
                            "updated_at": "2026-08-03T00:05:00+00:00",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            loaded = storage.load_experiment_results("NVDA")

            self.assertEqual(1, len(loaded))
            self.assertEqual("expr-legacy-001", loaded[0].experiment_result_id)
            self.assertEqual({}, dict(loaded[0].diagnostics))


if __name__ == "__main__":
    unittest.main()