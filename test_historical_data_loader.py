import unittest
from unittest.mock import Mock

import pandas as pd

from market.historical_data_loader import HistoricalDataLoader


class HistoricalDataLoaderTests(unittest.TestCase):
    def test_load_returns_raw_history_with_date_index(self):
        history_manager = Mock()
        feature_store = Mock()

        history_manager.load_history.return_value = pd.DataFrame(
            {
                "Date": ["2024-01-02", "2024-01-03"],
                "Open": [100.0, 101.0],
                "High": [102.0, 103.0],
                "Low": [99.0, 100.0],
                "Close": [101.0, 102.0],
                "Volume": [1000, 1100],
            }
        )
        feature_store.features_exist.return_value = False

        data = HistoricalDataLoader(
            history_manager=history_manager,
            feature_store=feature_store,
        ).load("NVDA")

        self.assertEqual(["Open", "High", "Low", "Close", "Volume"], list(data.columns))
        self.assertEqual("Date", data.index.name)
        self.assertEqual(pd.Timestamp("2024-01-02"), data.index[0])
        self.assertEqual(101.0, data.loc[pd.Timestamp("2024-01-02"), "Close"])
        feature_store.load_features.assert_not_called()

    def test_load_joins_available_feature_columns(self):
        history_manager = Mock()
        feature_store = Mock()

        history_manager.load_history.return_value = pd.DataFrame(
            {
                "Date": ["2024-01-02", "2024-01-03"],
                "Open": [100.0, 101.0],
                "High": [102.0, 103.0],
                "Low": [99.0, 100.0],
                "Close": [101.0, 102.0],
                "Volume": [1000, 1100],
            }
        )
        feature_store.features_exist.return_value = True
        feature_store.load_features.return_value = pd.DataFrame(
            {
                "Date": ["2024-01-02", "2024-01-03"],
                "Close": [101.0, 102.0],
                "RSI_14": [45.0, 52.0],
                "EMA_20": [100.5, 101.25],
            }
        )

        data = HistoricalDataLoader(
            history_manager=history_manager,
            feature_store=feature_store,
        ).load("NVDA")

        self.assertIn("RSI_14", data.columns)
        self.assertIn("EMA_20", data.columns)
        self.assertEqual(45.0, data.loc[pd.Timestamp("2024-01-02"), "RSI_14"])
        self.assertEqual(101.25, data.loc[pd.Timestamp("2024-01-03"), "EMA_20"])

    def test_load_raises_clear_error_when_raw_history_missing_required_columns(self):
        history_manager = Mock()
        feature_store = Mock()

        history_manager.load_history.return_value = pd.DataFrame(
            {
                "Date": ["2024-01-02"],
                "Open": [100.0],
                "High": [102.0],
                "Low": [99.0],
                "Close": [101.0],
            }
        )
        feature_store.features_exist.return_value = False

        loader = HistoricalDataLoader(
            history_manager=history_manager,
            feature_store=feature_store,
        )

        with self.assertRaisesRegex(
            ValueError,
            "historical market data is missing required columns: Volume",
        ):
            loader.load("NVDA")

    def test_load_raises_clear_error_when_feature_data_missing_date(self):
        history_manager = Mock()
        feature_store = Mock()

        history_manager.load_history.return_value = pd.DataFrame(
            {
                "Date": ["2024-01-02"],
                "Open": [100.0],
                "High": [102.0],
                "Low": [99.0],
                "Close": [101.0],
                "Volume": [1000],
            }
        )
        feature_store.features_exist.return_value = True
        feature_store.load_features.return_value = pd.DataFrame(
            {
                "RSI_14": [45.0],
            }
        )

        loader = HistoricalDataLoader(
            history_manager=history_manager,
            feature_store=feature_store,
        )

        with self.assertRaisesRegex(
            ValueError,
            "historical feature data is missing required columns: Date",
        ):
            loader.load("NVDA")


if __name__ == "__main__":
    unittest.main()