import unittest
from datetime import datetime, timezone

from research.experiment import ExperimentTestType
from research.experiment_result import (
    ExperimentMetrics,
    ExperimentResult,
    ExperimentResultStatus,
)


class ExperimentResultTests(unittest.TestCase):
    def test_creation_and_defaults(self):
        started_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
        created_at = datetime(2026, 8, 3, 0, 1, tzinfo=timezone.utc)

        result = ExperimentResult(
            experiment_result_id="expr-001",
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            started_at=started_at,
            created_at=created_at,
            updated_at=created_at,
        )

        self.assertEqual("expr-001", result.experiment_result_id)
        self.assertEqual("expr-001", result.id)
        self.assertEqual("expreq-001", result.experiment_request_id)
        self.assertEqual("hyp-001", result.hypothesis_id)
        self.assertEqual("NVDA", result.symbol)
        self.assertEqual(ExperimentTestType.INITIAL_BACKTEST, result.test_type)
        self.assertEqual(ExperimentResultStatus.RUNNING, result.status)
        self.assertEqual(started_at, result.started_at)
        self.assertIsNone(result.completed_at)
        self.assertEqual("", result.summary)
        self.assertIsNone(result.failure_reason)
        self.assertEqual(ExperimentMetrics(), result.metrics)
        self.assertEqual({}, dict(result.diagnostics))
        self.assertEqual(created_at, result.created_at)
        self.assertEqual(created_at, result.updated_at)

    def test_metric_storage(self):
        metrics = ExperimentMetrics(
            total_return=0.12,
            win_rate=0.58,
            max_drawdown=-0.07,
            trade_count=42,
            average_return=0.004,
            average_holding_period=3.5,
            profit_factor=1.4,
            sharpe_ratio=1.2,
            extra_metrics={
                "turnover": 0.18,
                "benchmark_relative_return": 0.03,
            },
        )

        result = ExperimentResult(
            experiment_result_id="expr-002",
            experiment_request_id="expreq-002",
            hypothesis_id="hyp-002",
            symbol="NVDA",
            test_type=ExperimentTestType.EXPLORATORY,
            metrics=metrics,
        )

        self.assertEqual(0.12, result.metrics.total_return)
        self.assertEqual(0.58, result.metrics.win_rate)
        self.assertEqual(-0.07, result.metrics.max_drawdown)
        self.assertEqual(42, result.metrics.trade_count)
        self.assertEqual(0.004, result.metrics.average_return)
        self.assertEqual(3.5, result.metrics.average_holding_period)
        self.assertEqual(1.4, result.metrics.profit_factor)
        self.assertEqual(1.2, result.metrics.sharpe_ratio)
        self.assertEqual(0.18, result.metrics.extra_metrics["turnover"])
        self.assertEqual(
            0.03,
            result.metrics.extra_metrics["benchmark_relative_return"],
        )

    def test_mark_completed(self):
        started_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
        completed_at = datetime(2026, 8, 3, 0, 5, tzinfo=timezone.utc)

        result = ExperimentResult(
            experiment_result_id="expr-003",
            experiment_request_id="expreq-003",
            hypothesis_id="hyp-003",
            symbol="NVDA",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            started_at=started_at,
            created_at=started_at,
            updated_at=started_at,
        )

        metrics = ExperimentMetrics(total_return=0.09, win_rate=0.55, trade_count=30)

        completed = result.mark_completed(
            summary="Initial backtest completed with positive net return.",
            metrics=metrics,
            diagnostics={
                "first_match_date": "2025-01-02",
                "last_match_date": "2026-07-31",
            },
            completed_at=completed_at,
            updated_at=completed_at,
        )

        self.assertEqual(ExperimentResultStatus.RUNNING, result.status)
        self.assertEqual(ExperimentResultStatus.COMPLETED, completed.status)
        self.assertEqual(completed_at, completed.completed_at)
        self.assertEqual(
            "Initial backtest completed with positive net return.",
            completed.summary,
        )
        self.assertEqual(metrics, completed.metrics)
        self.assertEqual("2025-01-02", completed.diagnostics["first_match_date"])
        self.assertEqual("2026-07-31", completed.diagnostics["last_match_date"])
        self.assertIsNone(completed.failure_reason)

    def test_mark_failed(self):
        started_at = datetime(2026, 8, 3, 0, 0, tzinfo=timezone.utc)
        failed_at = datetime(2026, 8, 3, 0, 2, tzinfo=timezone.utc)

        result = ExperimentResult(
            experiment_result_id="expr-004",
            experiment_request_id="expreq-004",
            hypothesis_id="hyp-004",
            symbol="NVDA",
            test_type=ExperimentTestType.WALK_FORWARD,
            started_at=started_at,
            created_at=started_at,
            updated_at=started_at,
        )

        failed = result.mark_failed(
            failure_reason="missing required data partition for validation window",
            completed_at=failed_at,
            updated_at=failed_at,
            status=ExperimentResultStatus.FAILED,
        )

        self.assertEqual(ExperimentResultStatus.RUNNING, result.status)
        self.assertEqual(ExperimentResultStatus.FAILED, failed.status)
        self.assertEqual(failed_at, failed.completed_at)
        self.assertEqual(
            "missing required data partition for validation window",
            failed.failure_reason,
        )

    def test_rejects_invalid_failure_state(self):
        result = ExperimentResult(
            experiment_result_id="expr-005",
            experiment_request_id="expreq-005",
            hypothesis_id="hyp-005",
            symbol="NVDA",
            test_type=ExperimentTestType.REPRODUCTION,
        )

        with self.assertRaisesRegex(ValueError, "failure_reason is required"):
            result.mark_failed(
                failure_reason="",
            )


if __name__ == "__main__":
    unittest.main()