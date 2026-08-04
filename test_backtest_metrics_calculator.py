import unittest

from research.backtest_metrics_calculator import calculate_backtest_metrics
from research.experiment_result import ExperimentMetrics
from research.forward_return_calculator import ForwardReturnResult


class BacktestMetricsCalculatorTests(unittest.TestCase):
    def test_calculates_metrics_for_mixed_returns(self):
        results = [
            ForwardReturnResult(
                setup_index="2024-01-02",
                entry_close=100.0,
                exit_close=110.0,
                horizon=2,
                forward_return=0.10,
                is_available=True,
            ),
            ForwardReturnResult(
                setup_index="2024-01-03",
                entry_close=100.0,
                exit_close=95.0,
                horizon=2,
                forward_return=-0.05,
                is_available=True,
            ),
            ForwardReturnResult(
                setup_index="2024-01-04",
                entry_close=100.0,
                exit_close=100.0,
                horizon=2,
                forward_return=0.0,
                is_available=True,
            ),
        ]

        metrics = calculate_backtest_metrics(results)

        self.assertEqual(3, metrics["trade_count"])
        self.assertAlmostEqual((0.10 - 0.05 + 0.0) / 3, metrics["average_return"])
        self.assertAlmostEqual(0.05, metrics["total_return"])
        self.assertAlmostEqual(1 / 3, metrics["win_rate"])
        self.assertAlmostEqual(1 / 3, metrics["extra_metrics"]["loss_rate"])
        self.assertAlmostEqual(0.10, metrics["extra_metrics"]["best_return"])
        self.assertAlmostEqual(-0.05, metrics["extra_metrics"]["worst_return"])
        self.assertAlmostEqual(0.0, metrics["extra_metrics"]["median_return"])

    def test_calculates_metrics_for_positive_returns(self):
        metrics = calculate_backtest_metrics(
            [
                {
                    "is_available": True,
                    "forward_return": 0.03,
                },
                {
                    "is_available": True,
                    "forward_return": 0.05,
                },
            ]
        )

        self.assertEqual(2, metrics["trade_count"])
        self.assertAlmostEqual(0.04, metrics["average_return"])
        self.assertAlmostEqual(0.08, metrics["total_return"])
        self.assertAlmostEqual(1.0, metrics["win_rate"])
        self.assertAlmostEqual(0.0, metrics["extra_metrics"]["loss_rate"])

    def test_calculates_metrics_for_negative_returns(self):
        metrics = calculate_backtest_metrics(
            [
                {
                    "is_available": True,
                    "forward_return": -0.02,
                },
                {
                    "is_available": True,
                    "forward_return": -0.04,
                },
            ]
        )

        self.assertEqual(2, metrics["trade_count"])
        self.assertAlmostEqual(-0.03, metrics["average_return"])
        self.assertAlmostEqual(-0.06, metrics["total_return"])
        self.assertAlmostEqual(0.0, metrics["win_rate"])
        self.assertAlmostEqual(1.0, metrics["extra_metrics"]["loss_rate"])
        self.assertAlmostEqual(-0.02, metrics["extra_metrics"]["best_return"])
        self.assertAlmostEqual(-0.04, metrics["extra_metrics"]["worst_return"])

    def test_output_is_compatible_with_experiment_metrics(self):
        metrics = calculate_backtest_metrics(
            [
                {
                    "is_available": True,
                    "forward_return": 0.02,
                },
                {
                    "is_available": True,
                    "forward_return": -0.01,
                },
            ]
        )

        experiment_metrics = ExperimentMetrics(**metrics)

        self.assertEqual(2, experiment_metrics.trade_count)
        self.assertAlmostEqual(0.01, experiment_metrics.total_return)
        self.assertAlmostEqual(0.5, experiment_metrics.win_rate)
        self.assertAlmostEqual(0.5, experiment_metrics.extra_metrics["loss_rate"])

    def test_raises_clear_error_for_empty_input(self):
        with self.assertRaisesRegex(ValueError, "no available forward returns to summarize"):
            calculate_backtest_metrics([])

    def test_skips_unavailable_results(self):
        metrics = calculate_backtest_metrics(
            [
                ForwardReturnResult(
                    setup_index="2024-01-02",
                    entry_close=100.0,
                    exit_close=103.0,
                    horizon=1,
                    forward_return=0.03,
                    is_available=True,
                ),
                ForwardReturnResult(
                    setup_index="2024-01-03",
                    entry_close=103.0,
                    exit_close=None,
                    horizon=1,
                    forward_return=None,
                    is_available=False,
                ),
            ]
        )

        self.assertEqual(1, metrics["trade_count"])
        self.assertAlmostEqual(0.03, metrics["average_return"])
        self.assertAlmostEqual(0.03, metrics["total_return"])

    def test_raises_clear_error_when_all_results_are_unavailable(self):
        with self.assertRaisesRegex(ValueError, "no available forward returns to summarize"):
            calculate_backtest_metrics(
                [
                    {
                        "is_available": False,
                        "forward_return": None,
                    }
                ]
            )


if __name__ == "__main__":
    unittest.main()