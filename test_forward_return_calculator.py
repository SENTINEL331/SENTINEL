import unittest

import pandas as pd

from research.forward_return_calculator import calculate_forward_returns


class ForwardReturnCalculatorTests(unittest.TestCase):
    def test_calculates_forward_returns_for_setup_indexes(self):
        feature_data = pd.DataFrame(
            {"Close": [100.0, 103.0, 101.0, 110.0]},
            index=pd.Index(
                ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
                name="Date",
            ),
        )

        results = calculate_forward_returns(
            feature_data,
            ["2024-01-02", "2024-01-03"],
            2,
        )

        self.assertEqual(2, len(results))
        self.assertEqual("2024-01-02", results[0].setup_index)
        self.assertEqual(100.0, results[0].entry_close)
        self.assertEqual(101.0, results[0].exit_close)
        self.assertEqual(2, results[0].horizon)
        self.assertAlmostEqual(0.01, results[0].forward_return)
        self.assertTrue(results[0].is_available)

        self.assertEqual("2024-01-03", results[1].setup_index)
        self.assertEqual(103.0, results[1].entry_close)
        self.assertEqual(110.0, results[1].exit_close)
        self.assertAlmostEqual((110.0 - 103.0) / 103.0, results[1].forward_return)
        self.assertTrue(results[1].is_available)

    def test_calculates_forward_returns_for_setup_positions(self):
        feature_data = pd.DataFrame(
            {"Close": [100.0, 103.0, 101.0, 110.0]},
            index=pd.Index([10, 11, 12, 13], name="row_id"),
        )

        results = calculate_forward_returns(
            feature_data,
            [0, 1],
            1,
            setup_rows_are_positions=True,
        )

        self.assertEqual(10, results[0].setup_index)
        self.assertEqual(103.0, results[0].exit_close)
        self.assertAlmostEqual(0.03, results[0].forward_return)
        self.assertEqual(11, results[1].setup_index)
        self.assertEqual(101.0, results[1].exit_close)

    def test_marks_unavailable_when_not_enough_future_data_exists(self):
        feature_data = pd.DataFrame(
            {"Close": [100.0, 103.0, 101.0]},
            index=pd.Index(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )

        results = calculate_forward_returns(feature_data, ["2024-01-04"], 1)

        self.assertEqual(1, len(results))
        self.assertEqual("2024-01-04", results[0].setup_index)
        self.assertEqual(101.0, results[0].entry_close)
        self.assertIsNone(results[0].exit_close)
        self.assertIsNone(results[0].forward_return)
        self.assertFalse(results[0].is_available)

    def test_raises_clear_error_for_missing_close_column(self):
        feature_data = pd.DataFrame({"Adj Close": [100.0, 101.0]})

        with self.assertRaisesRegex(ValueError, "missing required price column: Close"):
            calculate_forward_returns(feature_data, [0], 1, setup_rows_are_positions=True)

    def test_raises_clear_error_for_invalid_horizon(self):
        feature_data = pd.DataFrame({"Close": [100.0, 101.0]})

        with self.assertRaisesRegex(ValueError, "horizon must be a positive integer"):
            calculate_forward_returns(feature_data, [0], 0, setup_rows_are_positions=True)

    def test_raises_clear_error_for_invalid_setup_indexes(self):
        feature_data = pd.DataFrame(
            {"Close": [100.0, 101.0]},
            index=pd.Index(["2024-01-02", "2024-01-03"]),
        )

        with self.assertRaisesRegex(ValueError, "invalid setup index: '2024-01-04'"):
            calculate_forward_returns(feature_data, ["2024-01-04"], 1)

    def test_raises_clear_error_for_invalid_setup_positions(self):
        feature_data = pd.DataFrame({"Close": [100.0, 101.0]})

        with self.assertRaisesRegex(ValueError, "setup position out of range: 2"):
            calculate_forward_returns(feature_data, [2], 1, setup_rows_are_positions=True)


if __name__ == "__main__":
    unittest.main()