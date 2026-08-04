import unittest

import pandas as pd

from research.setup_scanner import scan_entry_setups


class SetupScannerTests(unittest.TestCase):
    def test_scan_entry_setups_returns_rows_matching_all_conditions(self):
        feature_data = pd.DataFrame(
            {
                "Close": [98.0, 101.0, 104.0],
                "EMA_20": [100.0, 100.0, 103.0],
                "RSI_14": [35.0, 44.0, 60.0],
            },
            index=pd.Index(
                ["2024-01-02", "2024-01-03", "2024-01-04"],
                name="Date",
            ),
        )

        matching_rows = scan_entry_setups(
            feature_data,
            [
                {"field": "Close", "operator": ">", "value": 100.0},
                {"field": "RSI_14", "operator": "<", "value": 50.0},
            ],
        )

        self.assertEqual(["2024-01-03"], list(matching_rows.index))
        self.assertEqual([101.0], list(matching_rows["Close"]))

    def test_scan_entry_setups_supports_field_to_field_conditions(self):
        feature_data = pd.DataFrame(
            {
                "Close": [99.0, 101.0, 105.0],
                "EMA_20": [100.0, 100.0, 104.0],
            },
            index=pd.Index([1, 2, 3], name="row_id"),
        )

        matching_rows = scan_entry_setups(
            feature_data,
            [
                {
                    "field": "Close",
                    "operator": ">",
                    "other_field": "EMA_20",
                }
            ],
        )

        self.assertEqual([2, 3], list(matching_rows.index))

    def test_scan_entry_setups_resolves_supported_feature_aliases(self):
        feature_data = pd.DataFrame(
            {
                "Close": [99.0, 101.0, 105.0],
                "BB_LOWER": [98.0, 100.0, 104.0],
                "BB_MIDDLE": [100.0, 102.0, 106.0],
                "BB_UPPER": [102.0, 104.0, 108.0],
            },
            index=pd.Index([1, 2, 3], name="row_id"),
        )

        matching_rows = scan_entry_setups(
            feature_data,
            [
                {
                    "field": "Close",
                    "operator": ">",
                    "other_field": "BB_Lower_20",
                },
                {
                    "field": "Close",
                    "operator": "<",
                    "other_field": "BB_Upper_20",
                },
            ],
        )

        self.assertEqual([1, 2, 3], list(matching_rows.index))

    def test_scan_entry_setups_resolves_aliases_to_canonical_columns(self):
        feature_data = pd.DataFrame(
            {
                "SMA_20": [100.0, 100.0, 100.0],
                "EMA_20": [99.0, 100.0, 101.0],
                "RSI_14": [40.0, 55.0, 45.0],
            },
            index=pd.Index(["2024-01-02", "2024-01-03", "2024-01-04"]),
        )

        matching_rows = scan_entry_setups(
            feature_data,
            [
                {"field": "RSI14", "operator": "<", "value": 50.0},
                {"field": "SMA20", "operator": ">", "other_field": "EMA20"},
            ],
        )

        self.assertEqual(["2024-01-02"], list(matching_rows.index))

    def test_scan_entry_setups_raises_clear_error_for_malformed_condition(self):
        feature_data = pd.DataFrame({"Close": [100.0]})

        with self.assertRaisesRegex(ValueError, "condition.operator is required"):
            scan_entry_setups(feature_data, [{"field": "Close", "value": 100.0}])

    def test_scan_entry_setups_raises_clear_error_for_missing_field(self):
        feature_data = pd.DataFrame({"Close": [100.0]}, index=["2024-01-02"])

        with self.assertRaisesRegex(ValueError, "unknown field: EMA_20"):
            scan_entry_setups(
                feature_data,
                [{"field": "EMA_20", "operator": ">", "value": 99.0}],
            )

    def test_scan_entry_setups_keeps_unknown_alias_errors_clear(self):
        feature_data = pd.DataFrame({"Close": [100.0]}, index=["2024-01-02"])

        with self.assertRaisesRegex(ValueError, "unknown field: NotAFeature"):
            scan_entry_setups(
                feature_data,
                [{"field": "NotAFeature", "operator": ">", "value": 99.0}],
            )

    def test_scan_entry_setups_raises_clear_error_for_missing_row_values(self):
        feature_data = pd.DataFrame(
            {"Close": [100.0, None], "EMA_20": [99.0, 98.0]},
            index=["2024-01-02", "2024-01-03"],
        )

        with self.assertRaisesRegex(
            ValueError,
            "missing value for field 'Close' at row index '2024-01-03'",
        ):
            scan_entry_setups(
                feature_data,
                [{"field": "Close", "operator": ">", "other_field": "EMA_20"}],
            )

    def test_scan_entry_setups_rejects_invalid_inputs(self):
        with self.assertRaisesRegex(ValueError, "feature_data must be a pandas DataFrame"):
            scan_entry_setups([], [{"field": "Close", "operator": ">", "value": 100.0}])

        with self.assertRaisesRegex(ValueError, "entry_conditions must not be empty"):
            scan_entry_setups(pd.DataFrame({"Close": [100.0]}), [])


if __name__ == "__main__":
    unittest.main()