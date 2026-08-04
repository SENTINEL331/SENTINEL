import json
import unittest

import pandas as pd

from research.basic_backtest_runner import BasicBacktestRunner
from research.experiment import ExperimentRequest, ExperimentTestType
from research.experiment_result import ExperimentResultStatus


class BasicBacktestRunnerTests(unittest.TestCase):
    def test_run_returns_completed_experiment_result_with_metrics(self):
        request = ExperimentRequest(
            experiment_request_id="expreq-001",
            hypothesis_id="hyp-001",
            hypothesis_version_id="hyp-001:v1",
            symbol="NVDA",
            title="Validate RSI pullback recovery",
            objective="Test whether pullbacks below RSI 50 recover over the next two sessions.",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions=json.dumps(
                [
                    {"field": "Close", "operator": ">", "value": 100.0},
                    {"field": "RSI_14", "operator": "<", "value": 50.0},
                ]
            ),
            exit_conditions="Exit after fixed two-session horizon.",
            time_horizon="2D",
        )
        feature_data = pd.DataFrame(
            {
                "Close": [99.0, 101.0, 103.0, 100.0, 110.0],
                "RSI_14": [55.0, 45.0, 51.0, 52.0, 60.0],
            },
            index=pd.Index(
                ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08"],
                name="Date",
            ),
        )

        result = BasicBacktestRunner().run(request, feature_data)

        self.assertEqual(ExperimentResultStatus.COMPLETED, result.status)
        self.assertEqual("expreq-001", result.experiment_request_id)
        self.assertEqual("hyp-001", result.hypothesis_id)
        self.assertEqual("NVDA", result.symbol)
        self.assertEqual(ExperimentTestType.INITIAL_BACKTEST, result.test_type)
        self.assertEqual(1, result.metrics.trade_count)
        self.assertAlmostEqual((100.0 - 101.0) / 101.0, result.metrics.total_return)
        self.assertAlmostEqual((100.0 - 101.0) / 101.0, result.metrics.average_return)
        self.assertAlmostEqual(0.0, result.metrics.win_rate)
        self.assertAlmostEqual(1.0, result.metrics.extra_metrics["loss_rate"])
        self.assertIn("1 matching setups", result.summary)

    def test_run_handles_no_matching_setups_clearly(self):
        request = ExperimentRequest(
            experiment_request_id="expreq-002",
            hypothesis_id="hyp-002",
            hypothesis_version_id="hyp-002:v1",
            symbol="NVDA",
            title="Validate breakout continuation",
            objective="Test whether breakouts continue higher over the next two sessions.",
            test_type=ExperimentTestType.EXPLORATORY,
            entry_conditions=json.dumps(
                [
                    {"field": "Close", "operator": ">", "value": 200.0},
                ]
            ),
            exit_conditions="Exit after fixed two-session horizon.",
            time_horizon="2D",
        )
        feature_data = pd.DataFrame(
            {
                "Close": [99.0, 101.0, 103.0],
                "RSI_14": [55.0, 45.0, 48.0],
            },
            index=pd.Index(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )

        result = BasicBacktestRunner().run(request, feature_data)

        self.assertEqual(ExperimentResultStatus.COMPLETED, result.status)
        self.assertEqual(0, result.metrics.trade_count)
        self.assertEqual(0.0, result.metrics.total_return)
        self.assertIn("no matching setups", result.summary.lower())

    def test_run_handles_matching_setups_with_unavailable_forward_returns(self):
        request = ExperimentRequest(
            experiment_request_id="expreq-003",
            hypothesis_id="hyp-003",
            hypothesis_version_id="hyp-003:v1",
            symbol="NVDA",
            title="Validate late-horizon continuation",
            objective="Test whether late setups continue higher beyond the available sample.",
            test_type=ExperimentTestType.INITIAL_BACKTEST,
            entry_conditions=json.dumps(
                [
                    {"field": "Close", "operator": ">", "value": 100.0},
                ]
            ),
            exit_conditions="Exit after fixed two-session horizon.",
            time_horizon="2D",
        )
        feature_data = pd.DataFrame(
            {
                "Close": [99.0, 100.0, 101.0],
            },
            index=pd.Index(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )

        result = BasicBacktestRunner().run(request, feature_data)

        self.assertEqual(ExperimentResultStatus.COMPLETED, result.status)
        self.assertEqual(0, result.metrics.trade_count)
        self.assertEqual(0.0, result.metrics.total_return)
        self.assertIn("no available forward returns", result.summary.lower())


if __name__ == "__main__":
    unittest.main()