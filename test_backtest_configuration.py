import unittest

from config import settings

try:
    from market.data_manager import MarketDataManager
except Exception:  # pragma: no cover - optional dependency guard for local test envs
    MarketDataManager = None


class BacktestConfigurationTests(unittest.TestCase):
    def test_settings_expose_backtest_period_and_interval(self):
        self.assertEqual("2y", settings.BACKTEST_PERIOD)
        self.assertEqual("1d", settings.BACKTEST_INTERVAL)

    def test_market_snapshot_defaults_remain_observation_defaults(self):
        if MarketDataManager is None:
            self.skipTest("MarketDataManager dependencies unavailable")

        defaults = MarketDataManager.download_history.__defaults__
        self.assertEqual((settings.DEFAULT_PERIOD, settings.DEFAULT_INTERVAL), defaults)


if __name__ == "__main__":
    unittest.main()
