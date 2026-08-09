import unittest
from unittest.mock import Mock

import pandas as pd

from market.historical_data_loader import HistoricalDataLoader


class HistoricalDataLoaderTests(unittest.TestCase):
    def _build_raw_history(self, periods: int = 25) -> pd.DataFrame:
        dates = pd.date_range("2024-01-02", periods=periods, freq="D")
        closes = [100.0 + float(index) for index in range(periods)]

        return pd.DataFrame(
            {
                "Date": dates.strftime("%Y-%m-%d"),
                "Open": [close - 0.5 for close in closes],
                "High": [close + 1.0 for close in closes],
                "Low": [close - 1.0 for close in closes],
                "Close": closes,
                "Volume": [1000 + index for index in range(periods)],
            }
        )

    def test_load_prepares_required_features_and_drops_unusable_rows(self):
        history_manager = Mock()
        feature_store = Mock()

        history_manager.load_history.return_value = self._build_raw_history()
        feature_store.features_exist.return_value = False

        data = HistoricalDataLoader(
            history_manager=history_manager,
            feature_store=feature_store,
        ).load("NVDA")

        self.assertEqual(
            [
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
                "SMA_20",
                "EMA_20",
                "RSI_14",
                "ATR_14",
                "BB_MIDDLE",
                "BB_UPPER",
                "BB_LOWER",
            ],
            list(data.columns),
        )
        self.assertEqual("Date", data.index.name)
        self.assertEqual(pd.Timestamp("2024-01-21"), data.index[0])
        self.assertEqual(6, len(data.index))
        self.assertEqual(25, data.attrs["rows_loaded"])
        self.assertEqual(6, data.attrs["rows_after_cleaning"])
        self.assertFalse(
            data[["SMA_20", "EMA_20", "RSI_14", "ATR_14", "BB_MIDDLE", "BB_UPPER", "BB_LOWER"]]
            .isna()
            .any()
            .any()
        )
        feature_store.load_features.assert_not_called()

    def test_load_joins_available_feature_columns_and_computes_missing_ones(self):
        history_manager = Mock()
        feature_store = Mock()

        history_manager.load_history.return_value = self._build_raw_history()
        feature_store.features_exist.return_value = True
        feature_store.load_features.return_value = pd.DataFrame(
            {
                "Date": pd.date_range("2024-01-02", periods=25, freq="D").strftime("%Y-%m-%d"),
                "EMA_20": [999.0 for _ in range(25)],
            }
        )

        data = HistoricalDataLoader(
            history_manager=history_manager,
            feature_store=feature_store,
        ).load("NVDA")

        self.assertIn("SMA_20", data.columns)
        self.assertIn("EMA_20", data.columns)
        self.assertIn("RSI_14", data.columns)
        self.assertIn("BB_UPPER", data.columns)
        self.assertEqual(999.0, data.loc[pd.Timestamp("2024-01-21"), "EMA_20"])

    def test_load_drops_rows_with_unavailable_existing_feature_values(self):
        history_manager = Mock()
        feature_store = Mock()

        history_manager.load_history.return_value = self._build_raw_history()
        feature_store.features_exist.return_value = True

        dates = pd.date_range("2024-01-02", periods=25, freq="D")
        rsi_values = [55.0 for _ in range(25)]
        rsi_values[23] = None

        feature_store.load_features.return_value = pd.DataFrame(
            {
                "Date": dates.strftime("%Y-%m-%d"),
                "RSI_14": rsi_values,
            }
        )

        data = HistoricalDataLoader(
            history_manager=history_manager,
            feature_store=feature_store,
        ).load("NVDA")

        self.assertNotIn(pd.Timestamp("2024-01-25"), data.index)
        self.assertFalse(data["RSI_14"].isna().any())

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

    def test_load_forwards_interval_to_history_manager(self):
        history_manager = Mock()
        feature_store = Mock()

        history_manager.load_history.return_value = self._build_raw_history()
        feature_store.features_exist.return_value = False

        HistoricalDataLoader(
            history_manager=history_manager,
            feature_store=feature_store,
        ).load("NVDA", interval="1wk")

        history_manager.load_history.assert_called_once_with("NVDA", "1wk")

    def test_load_applies_period_lookback_window(self):
        history_manager = Mock()
        feature_store = Mock()

        history_manager.load_history.return_value = self._build_raw_history(periods=90)
        feature_store.features_exist.return_value = False

        data = HistoricalDataLoader(
            history_manager=history_manager,
            feature_store=feature_store,
        ).load("NVDA", period="30d")

        self.assertFalse(data.empty)
        lookback_days = (data.index.max() - data.index.min()).days
        self.assertLessEqual(lookback_days, 30)

    def test_load_refreshes_history_when_cached_rows_do_not_cover_requested_period(self):
        history_manager = Mock()
        market_data_manager = Mock()
        feature_store = Mock()

        history_manager.load_history.return_value = self._build_raw_history(periods=30)
        market_data_manager.download_history.return_value = self._build_raw_history(periods=800)
        feature_store.features_exist.return_value = False

        data = HistoricalDataLoader(
            history_manager=history_manager,
            market_data_manager=market_data_manager,
            feature_store=feature_store,
        ).load("NVDA", period="2y", interval="1d")

        market_data_manager.download_history.assert_called_once_with(
            "NVDA",
            period="2y",
            interval="1d",
        )
        history_manager.save_history.assert_called_once()
        self.assertGreater(data.attrs["rows_loaded"], 30)

    def test_load_ignores_short_feature_cache_for_longer_requested_period(self):
        history_manager = Mock()
        market_data_manager = Mock()
        feature_store = Mock()

        history_manager.load_history.return_value = self._build_raw_history(periods=30)
        market_data_manager.download_history.return_value = self._build_raw_history(periods=800)
        feature_store.features_exist.return_value = True
        feature_store.load_features.return_value = self._build_raw_history(periods=30)[
            ["Date", "Close"]
        ]

        data = HistoricalDataLoader(
            history_manager=history_manager,
            market_data_manager=market_data_manager,
            feature_store=feature_store,
        ).load("NVDA", period="2y", interval="1d")

        self.assertGreater(data.attrs["rows_loaded"], 30)


if __name__ == "__main__":
    unittest.main()